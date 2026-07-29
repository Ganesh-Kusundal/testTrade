"""Unified Dhan instrument resolution.

Single module for the full resolution pipeline (D-011 / REF-004 merge of
segments.py + instrument_mapper.py + resolver.py):

1. Wire-segment mappings — Exchange/Segment enums <-> Dhan wire strings
   ("NSE_EQ", "IDX_I", ...) used by HTTP and WebSocket protocols.
2. CSV row mapping — pure translation from the Dhan instrument master
   vocabulary to SCALPR's domain model (no I/O).
3. Symbol resolution — thread-safe O(1) symbol -> Instrument lookups with
   alternate key formats and index fallback.
"""

from __future__ import annotations

import contextlib
import logging
import re
import threading
from collections.abc import Iterable
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, NamedTuple

from scalpr.domain.errors import InstrumentNotFound

class DhanInstrumentNotFoundError(InstrumentNotFound, Exception):
    """Instrument not found in the Dhan instrument master."""

InstrumentNotFoundError = DhanInstrumentNotFoundError
from scalpr.domain.instrument import (
    Exchange,
    Instrument,
    OptionType,
    ResolvedInstrument,
    Segment,
    SimpleInstrumentId,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Wire-segment mappings (formerly segments.py)
# ---------------------------------------------------------------------------

# Default segment for unknown exchanges
DEFAULT_SEGMENT = "NSE_EQ"

# Short exchange codes
_EXCHANGE_SHORT: dict[Exchange, str] = {
    Exchange.NSE: "NSE",
    Exchange.BSE: "BSE",
    Exchange.MCX: "MCX",
}

# Exchange string to Dhan wire segment (default segment per exchange).
# Used by ws_client.py for binary protocol segment lookup.
EXCHANGE_TO_SEGMENT: dict[str, str] = {
    "NSE": "NSE_EQ",
    "BSE": "BSE_EQ",
    "MCX": "MCX_COMM",
    "INDEX": "IDX_I",  # For indices like NIFTY, BANKNIFTY
    "NFO": "NSE_FNO",  # NSE F&O
    "BFO": "BSE_FNO",  # BSE F&O
    "NSE_FNO": "NSE_FNO",
    "BSE_FNO": "BSE_FNO",
    "CURRENCY": "NSE_CURRENCY",
}

# Dhan wire segment to exchange string
SEGMENT_TO_EXCHANGE: dict[str, str] = {
    "NSE_EQ": "NSE",
    "BSE_EQ": "BSE",
    "MCX_COMM": "MCX",
    "IDX_I": "INDEX",
    "NSE_FNO": "NSE",
    "BSE_FNO": "BSE",
    "NSE_CURRENCY": "NSE",
    "BSE_CURRENCY": "BSE",
}

# CSV segment mapping (exchange_id, segment_code) -> wire_segment
_COMPACT_SEGMENT_MAP: dict[tuple[str, str], str] = {
    ("NSE", "E"): "NSE_EQ",
    ("NSE", "D"): "NSE_FNO",
    ("NSE", "I"): "IDX_I",
    ("BSE", "E"): "BSE_EQ",
    ("BSE", "D"): "BSE_FNO",
    ("BSE", "I"): "IDX_I",
    ("MCX", "M"): "MCX_COMM",
    ("CDS", "D"): "NSE_CURRENCY",
    ("NSE", "C"): "NSE_CURRENCY",
    ("BSE", "C"): "BSE_CURRENCY",
}

# Binary protocol numeric codes (Dhan v2 websocket)
NUMERIC_TO_SEGMENT: dict[int, str] = {
    0: "IDX_I",
    1: "NSE_EQ",
    2: "NSE_FNO",
    3: "NSE_CURRENCY",
    4: "BSE_EQ",
    5: "MCX_COMM",
    7: "BSE_CURRENCY",
    8: "BSE_FNO",
}

SEGMENT_TO_NUMERIC: dict[str, int] = {v: k for k, v in NUMERIC_TO_SEGMENT.items()}


def exchange_to_wire(exchange: Exchange | str) -> str:
    """Convert Exchange enum or string to Dhan wire segment string (legacy 1-arg).

    Delegates to the canonical pair-based _WIRE_BY_EXCHANGE_SEGMENT using
    a default segment per exchange.

    Args:
        exchange: Exchange enum value or string (e.g., "NSE", "MCX")

    Returns:
        Dhan wire segment string (e.g., "NSE_EQ", "MCX_COMM")

    Raises:
        ValueError: If exchange is not recognized
    """
    if isinstance(exchange, Exchange):
        # Derive from canonical pair map using a default segment
        _default_seg = {
            Exchange.NSE: Segment.EQUITY,
            Exchange.BSE: Segment.EQUITY,
            Exchange.MCX: Segment.COMMODITY,
        }
        seg = _default_seg.get(exchange)
        if seg is None:
            raise ValueError(f"No wire segment for exchange: {exchange}")
        return _WIRE_BY_EXCHANGE_SEGMENT[(exchange, seg)]

    # String lookup
    wire = EXCHANGE_TO_SEGMENT.get(exchange.upper())
    if wire is None:
        raise ValueError(f"Unknown exchange: {exchange!r}")
    return wire


# Exchange normalisation: raw broker/user strings -> Exchange enum
_EXCHANGE_NORMALISE: dict[str, Exchange] = {
    "NSE": Exchange.NSE,
    "BSE": Exchange.BSE,
    "MCX": Exchange.MCX,
    "NSE_EQ": Exchange.NSE,
    "BSE_EQ": Exchange.BSE,
    "MCX_COMM": Exchange.MCX,
    "NSE_FNO": Exchange.NSE,
    "BSE_FNO": Exchange.BSE,
    # Indices and currency use Exchange.NSE (not separate exchange enums).
    "IDX_I": Exchange.NSE,
    "NSE_CURRENCY": Exchange.NSE,
    "BSE_CURRENCY": Exchange.NSE,
    "INDEX": Exchange.NSE,
    "CURRENCY": Exchange.NSE,
    "NFO": Exchange.NSE,
    "BFO": Exchange.BSE,
}


def normalise_exchange(exchange: str | Exchange, *, strict: bool = False) -> Exchange:
    """Normalise a raw exchange/segment string to an Exchange enum.

    Args:
        exchange: Raw exchange string (e.g., "NSE", "NSE_EQ", "IDX_I")
        strict: If True, raise ValueError for unknown strings instead of
            silently defaulting to NSE (typo protection at API boundaries).

    Returns:
        Exchange enum value (defaults to NSE for unknown strings unless strict)
    """
    if isinstance(exchange, Exchange):
        return exchange
    key = str(exchange).strip().upper()
    exch = _EXCHANGE_NORMALISE.get(key)
    if exch is None:
        if strict:
            raise ValueError(f"Unknown exchange: {exchange!r}")
        return Exchange.NSE
    return exch


# (Exchange, Segment) -> Dhan wire segment string
_WIRE_BY_EXCHANGE_SEGMENT: dict[tuple[Exchange, Segment], str] = {
    (Exchange.NSE, Segment.EQUITY): "NSE_EQ",
    (Exchange.BSE, Segment.EQUITY): "BSE_EQ",
    (Exchange.NSE, Segment.FUTURES): "NSE_FNO",
    (Exchange.NSE, Segment.OPTIONS): "NSE_FNO",
    (Exchange.BSE, Segment.FUTURES): "BSE_FNO",
    (Exchange.BSE, Segment.OPTIONS): "BSE_FNO",
    (Exchange.MCX, Segment.COMMODITY): "MCX_COMM",
    (Exchange.MCX, Segment.FUTURES): "MCX_COMM",
    (Exchange.MCX, Segment.OPTIONS): "MCX_COMM",
    (Exchange.NSE, Segment.INDEX): "IDX_I",
    (Exchange.BSE, Segment.INDEX): "IDX_I",
    (Exchange.NSE, Segment.CURRENCY): "NSE_CURRENCY",
}


def to_dhan_wire(exchange: Exchange, segment: Segment) -> str:
    """Convert (Exchange, Segment) pair to Dhan wire segment string.

    Args:
        exchange: Exchange enum value
        segment: Segment enum value

    Returns:
        Dhan wire segment string (e.g., "NSE_EQ", "NSE_FNO", "IDX_I")

    Raises:
        ValueError: If no wire mapping exists for the pair
    """
    wire = _WIRE_BY_EXCHANGE_SEGMENT.get((exchange, segment))
    if wire is None:
        raise ValueError(
            f"No Dhan wire mapping for exchange={exchange!r}, segment={segment!r}"
        )
    return wire


def segment_to_exchange(segment: str, default: str = "NSE") -> Exchange:
    """Convert Dhan wire segment to Exchange enum.

    Args:
        segment: Dhan wire segment (e.g., "NSE_EQ", "MCX_COMM")
        default: Default exchange if segment not recognized

    Returns:
        Exchange enum value
    """
    exch_str = SEGMENT_TO_EXCHANGE.get(segment, default)
    try:
        return Exchange(exch_str)
    except ValueError:
        # Fallback to NSE if exchange not in enum
        return Exchange.NSE


def parse_segment(value: str) -> str | None:
    """Parse user/broker input to canonical segment string.

    Args:
        value: Segment string or exchange name

    Returns:
        Canonical segment string or None if not recognized
    """
    if not value:
        return None

    value_upper = value.strip().upper()

    # Direct mapping
    if value_upper in EXCHANGE_TO_SEGMENT:
        return EXCHANGE_TO_SEGMENT[value_upper]

    # Already a wire segment
    if value_upper in SEGMENT_TO_EXCHANGE:
        return value_upper

    return None


# ---------------------------------------------------------------------------
# Instrument master row mapping (formerly instrument_mapper.py)
#
# Single translation point between the Dhan instrument master vocabulary and
# SCALPR's domain model. No I/O — takes row dicts, returns MappedInstrument.
# Patterns ported from Trade_XV2 v2 instrument adapter.
# ---------------------------------------------------------------------------


class MappedInstrument(NamedTuple):
    instrument: Instrument
    wire_segment: str  # Dhan HTTP/WS segment, e.g. "NSE_EQ", "IDX_I"
    underlying: str | None  # derived for F&O rows, None otherwise


# Full SEM_INSTRUMENT_NAME vocabulary observed in the live CSV
_NAME_TO_SEGMENT: dict[str, Segment] = {
    "EQUITY": Segment.EQUITY,
    "INDEX": Segment.EQUITY,  # index-ness carried by wire segment IDX_I
    "BE": Segment.EQUITY,
    "BOND": Segment.EQUITY,
    "FUTIDX": Segment.FUTURES,
    "FUTSTK": Segment.FUTURES,
    "FUTCOM": Segment.FUTURES,
    "FUTCUR": Segment.FUTURES,
    "OPTIDX": Segment.OPTIONS,
    "OPTSTK": Segment.OPTIONS,
    "OPTCUR": Segment.OPTIONS,
    "OPTFUT": Segment.OPTIONS,
    "OPTCOM": Segment.OPTIONS,
}

# Dhan option codes: BSE uses CA/PA for CALL/PUT; "XX" means not an option
_OPTION_TYPE: dict[str, OptionType] = {
    "CE": OptionType.CE, "CA": OptionType.CE, "CALL": OptionType.CE,
    "PE": OptionType.PE, "PA": OptionType.PE, "PUT": OptionType.PE,
}

# Trailing futures symbol, e.g. "USDINR24AUGFUT" → "USDINR"
_FUT_TRAILING_RE = re.compile(r"^([A-Z]+)\d+[A-Z]{3}FUT$")


def map_row(row: dict[str, Any]) -> MappedInstrument | None:
    """Map a loader row dict[str, Any] to a MappedInstrument, or None to skip the row."""
    symbol = str(row.get("SEM_TRADING_SYMBOL") or "").strip()
    security_id = str(row.get("SEM_SMST_SECURITY_ID") or "").strip()
    if not symbol or not security_id:
        return None

    exch_id = str(row.get("SEM_EXM_EXCH_ID") or "").strip().upper()
    seg_code = str(row.get("SEM_SEGMENT") or "").strip().upper()
    wire_segment = str(row.get("WIRE_SEGMENT") or "").strip().upper() or \
        _COMPACT_SEGMENT_MAP.get((exch_id, seg_code), "")
    if not wire_segment:
        return None

    # IDX_I rows keep their raw exchange (NSE or BSE)
    if wire_segment == "IDX_I" and exch_id in ("NSE", "BSE"):
        exchange_str = exch_id
    else:
        exchange_str = SEGMENT_TO_EXCHANGE.get(wire_segment, "NSE")
    try:
        exchange = Exchange(exchange_str)
    except ValueError:
        exchange = Exchange.NSE

    name = str(row.get("SEM_INSTRUMENT_NAME") or "").strip().upper()
    segment = _NAME_TO_SEGMENT.get(name)
    if segment is None:
        return None  # unknown vocabulary — skip, never mis-map

    lot_size = _safe_int(row.get("SEM_LOT_UNITS"), default=1)
    tick_size = _safe_decimal(row.get("SEM_TICK_SIZE"), default="0.05")

    option_type: OptionType | None = None
    strike: Decimal | None = None
    expiry: date | None = None
    underlying: str | None = None

    if segment in (Segment.OPTIONS, Segment.FUTURES):
        expiry_str = row.get("SEM_EXPIRY_DATE")
        if expiry_str:
            with contextlib.suppress(ValueError):
                expiry = date.fromisoformat(str(expiry_str)[:10])
        underlying = _derive_underlying(row, symbol)

        if segment == Segment.OPTIONS:
            opt_raw = str(row.get("SEM_OPTION_TYPE") or "").strip().upper()
            option_type = _OPTION_TYPE.get(opt_raw)  # "XX"/unknown → None
            strike = _safe_opt_decimal(row.get("SEM_STRIKE_PRICE"))
            if strike is not None and strike <= 0:
                strike = None  # Dhan uses -0.01 as "no strike" sentinel

    # Equity display symbols drop the -EQ series suffix
    if segment == Segment.EQUITY and symbol.upper().endswith("-EQ"):
        symbol = symbol[:-3]

    instrument = Instrument(
        symbol=symbol,
        exchange=exchange,
        segment=segment,
        security_id=security_id,
        lot_size=lot_size,
        tick_size=tick_size,
        option_type=option_type,
        strike=strike,
        expiry=expiry,
    )
    return MappedInstrument(instrument, wire_segment, underlying)


def wire_segment_for(exchange: Exchange, segment: Segment) -> str:
    """Fallback wire segment for instruments not sourced from the CSV.

    Delegates to the canonical pair mapping in to_dhan_wire;
    the legacy heuristics remain only for pairs outside that table.
    """
    try:
        return to_dhan_wire(exchange, segment)
    except ValueError:
        pass
    if exchange is Exchange.MCX:
        return "MCX_COMM"
    if segment in (Segment.FUTURES, Segment.OPTIONS):
        return "BSE_FNO" if exchange is Exchange.BSE else "NSE_FNO"
    return "BSE_EQ" if exchange is Exchange.BSE else "NSE_EQ"


def _derive_underlying(row: dict[str, Any], trading_symbol: str) -> str | None:
    """Underlying for F&O: SM_SYMBOL_NAME → custom symbol → hyphen split → regex."""
    name = str(row.get("SM_SYMBOL_NAME") or "").strip()
    if name and name.lower() != "nan":
        return name.upper()

    custom = str(row.get("SEM_CUSTOM_SYMBOL") or "").strip()
    if custom and custom.lower() != "nan":
        return custom.split()[0].upper()

    sym = trading_symbol.strip().upper()
    if "-" in sym:
        return sym.split("-")[0]

    m = _FUT_TRAILING_RE.match(sym)
    if m:
        return m.group(1)
    return None


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _safe_decimal(value: Any, default: str = "0") -> Decimal:
    if value is None:
        return Decimal(default)
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal(default)


def _safe_opt_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Step size constants
# ---------------------------------------------------------------------------

INDEX_STEP_SIZES: dict[str, float] = {
    "NIFTY": 50.0, "NIFTY 50": 50.0,
    "BANKNIFTY": 100.0, "NIFTY BANK": 100.0,
    "FINNIFTY": 50.0, "NIFTY FIN SERVICE": 50.0,
    "MIDCPNIFTY": 25.0, "NIFTY MID SELECT": 25.0,
    "SENSEX": 100.0, "BANKEX": 100.0,
}

COMMODITY_STEP_SIZES: dict[str, float] = {
    "ALUMINIUM": 5.0, "CARDAMOM": 5.0, "COPPER": 5.0,
    "COTTON": 10.0, "CRUDEOIL": 50.0, "DHANIYA": 5.0,
    "GOLD": 100.0, "GUARGUM": 5.0, "GUARSEED": 5.0,
    "JEERA": 5.0, "LEAD": 5.0, "MENTHAOIL": 5.0,
    "NATURALGAS": 5.0, "NICKEL": 10.0, "SILVER": 250.0,
    "ZINC": 5.0,
}

# ---------------------------------------------------------------------------
# Symbol resolver (formerly resolver.py)
# ---------------------------------------------------------------------------


class SymbolResolver:
    """Thread-safe O(1) symbol → Instrument resolver.

    Provides fast instrument lookup by symbol, security_id, or alternate formats.
    Supports loading from CSV rows with automatic alternate key generation.
    """

    def __init__(self) -> None:
        self._by_symbol: dict[tuple[str, Exchange], Instrument] = {}
        self._by_security_id: dict[str, Instrument] = {}
        self._by_underlying: dict[tuple[str, Exchange], list[Instrument]] = {}
        self._wire_by_sid: dict[str, str] = {}
        self._kind_by_sid: dict[str, str] = {}
        self._stock_step_sizes: dict[str, float] = {}
        self._loaded = False
        self._step_sizes_loaded = False
        self._lock = threading.RLock()

    def resolve(self, symbol: str, exchange: str) -> Instrument:
        """Resolve symbol to Instrument.

        Args:
            symbol: Trading symbol (e.g., "RELIANCE", "NIFTY")
            exchange: Exchange code (e.g., "NSE", "MCX", "INDEX")

        Returns:
            Instrument object

        Raises:
            InstrumentNotFoundError: If symbol cannot be resolved
        """
        exch = self._normalise_exchange(exchange)
        inst = self._find(symbol, exch)
        if inst is None:
            raise InstrumentNotFoundError(
                f"Instrument not found: symbol={symbol!r}, exchange={exchange!r}"
            )
        return inst

    def resolve_full(self, symbol: str, exchange: str) -> ResolvedInstrument:
        """Resolve symbol to ResolvedInstrument with wire-format mappings.

        Returns a fully-resolved instrument containing everything needed
        to make API calls without further lookups.
        """
        exch = self._normalise_exchange(exchange)
        inst = self._find(symbol, exch)
        if inst is None:
            raise InstrumentNotFoundError(
                f"Instrument not found: symbol={symbol!r}, exchange={exchange!r}"
            )
        wire_seg = self._wire_by_sid.get(inst.security_id) or to_dhan_wire(exch, inst.segment)
        return ResolvedInstrument(
            instrument_id=SimpleInstrumentId(symbol=symbol, exchange=exch),
            security_id=inst.security_id,
            exchange=exch,
            segment=inst.segment,
            trading_symbol=inst.symbol,
            wire_segment=wire_seg,
            lot_size=inst.lot_size,
            tick_size=inst.tick_size,
            freeze_quantity=None,
            expiry=inst.expiry,
            strike=inst.strike,
            option_type=inst.option_type,
        )

    def get_by_symbol(self, symbol: str, exchange: str) -> Instrument | None:
        """Get instrument by symbol, returns None if not found."""
        try:
            return self._find(symbol, self._normalise_exchange(exchange))
        except Exception:
            return None

    def get_by_security_id(self, security_id: str) -> Instrument | None:
        """Get instrument by security_id, returns None if not found."""
        return self._by_security_id.get(str(security_id))

    def get_lot_size(self, symbol: str, exchange: str) -> int:
        """Get lot size for an instrument."""
        return self.resolve(symbol, exchange).lot_size

    def wire_segment_of(self, symbol: str, exchange: str) -> str:
        """Dhan wire segment for a symbol (e.g. "NSE_EQ", "IDX_I", "NSE_FNO")."""
        inst = self.resolve(symbol, exchange)
        return self._wire_by_sid.get(inst.security_id) or wire_segment_for(inst.exchange, inst.segment)

    def instrument_kind_of(self, symbol: str, exchange: str) -> str:
        """Dhan instrument name (e.g. "EQUITY", "INDEX", "FUTSTK") required by charts APIs."""
        inst = self.resolve(symbol, exchange)
        return self._kind_by_sid.get(inst.security_id) or "EQUITY"

    def get_futures_for_underlying(
        self, underlying: str, exchange: str
    ) -> list[Instrument]:
        """Get all future instruments for an underlying, sorted by expiry.

        Pure in-memory lookup — no API calls. Uses the ``_by_underlying``
        index populated during instrument CSV load.

        Args:
            underlying: Underlying symbol (e.g., "NIFTY", "RELIANCE").
            exchange: Exchange code (e.g., "NSE").

        Returns:
            List of Instrument objects with segment=FUTURES, sorted by
            expiry date (nearest first). Empty list if no futures exist.
        """
        exch = self._normalise_exchange(exchange)
        key = (underlying.upper(), exch)
        instruments = self._by_underlying.get(key, [])
        futures = [
            inst
            for inst in instruments
            if inst.segment == Segment.FUTURES and inst.expiry is not None
        ]
        return sorted(futures, key=lambda inst: inst.expiry)  # type: ignore[arg-type,return-value]

    def resolve_underlying_for_options(
        self, symbol: str, exchange: str
    ) -> tuple[int, str]:
        """Resolve an option-chain underlying to (security_id, wire_segment).

        Encapsulates the lookup strategy so callers (e.g. the option-chain
        adapter) don't reach into resolver internals. Tries a direct symbol
        lookup first; commodity underlyings (e.g. MCX ``SILVER``) aren't
        indexed as direct symbols, so it falls back to deriving the
        underlying's ``security_id``/``wire_segment`` from the nearest
        futures contract — which is what Dhan's ``/optionchain`` expects.

        Raises:
            InstrumentNotFoundError: if the symbol can't be resolved and no
                futures contract exists for it.
        """
        try:
            resolved = self.resolve_full(symbol, exchange)
            return int(resolved.security_id), resolved.wire_segment
        except InstrumentNotFoundError:
            futures = self.get_futures_for_underlying(symbol, exchange)
            if not futures:
                raise
            fut = futures[0]
            wire_seg = self.wire_segment_of(fut.symbol, exchange)
            return int(fut.security_id), wire_seg

    def stats(self) -> dict[str, Any]:
        """Get resolver statistics."""
        return {"loaded": self._loaded, "total": len(self._by_security_id)}

    def all_instruments(self) -> list[Instrument]:
        """Get all loaded instruments."""
        return list(self._by_security_id.values())

    def load_from_rows(self, rows: Iterable[dict[str, Any]]) -> dict[str, int | float]:
        """Load instruments from CSV rows with atomic swap.

        Args:
            rows: Iterable of CSV row dicts

        Returns:
            Dict with keys: total, skipped, skip_rate
        """
        new_by_symbol: dict[tuple[str, Exchange], Instrument] = {}
        new_by_sid: dict[str, Instrument] = {}
        new_by_underlying: dict[tuple[str, Exchange], list[Instrument]] = {}
        new_wire_by_sid: dict[str, str] = {}
        new_kind_by_sid: dict[str, str] = {}
        skipped = 0

        for row in rows:
            try:
                mapped = map_row(row)
            except Exception:
                skipped += 1
                continue

            if mapped is None:
                skipped += 1
                continue

            inst = mapped.instrument

            # Generate alternate keys for flexible lookup
            alt_keys = _generate_alternate_keys(
                symbol=inst.symbol,
                segment=inst.segment,
                expiry=inst.expiry,
                strike=inst.strike,
                option_type=inst.option_type,
            )

            # Register all alternate keys
            for k in alt_keys:
                existing = new_by_symbol.get((k, inst.exchange))
                if existing is None or (existing.segment == Segment.OPTIONS and inst.segment != Segment.OPTIONS):
                    new_by_symbol[(k, inst.exchange)] = inst

            new_by_sid[inst.security_id] = inst  # Index by numeric security_id
            new_wire_by_sid[inst.security_id] = mapped.wire_segment
            new_kind_by_sid[inst.security_id] = str(row.get("SEM_INSTRUMENT_NAME") or "").strip().upper()

            # Populate underlying index for OPTIONS/FUTURES
            if inst.segment in (Segment.OPTIONS, Segment.FUTURES):
                underlying = mapped.underlying or (inst.symbol.split()[0].upper() if inst.symbol else "")
                if underlying:
                    key = (underlying, inst.exchange)
                    new_by_underlying.setdefault(key, []).append(inst)

        with self._lock:
            self._by_symbol = new_by_symbol
            self._by_security_id = new_by_sid
            self._by_underlying = new_by_underlying
            self._wire_by_sid = new_wire_by_sid
            self._kind_by_sid = new_kind_by_sid
            self._loaded = True

        total_loaded = len(new_by_sid)
        total_processed = total_loaded + skipped
        skip_rate = skipped / total_processed if total_processed > 0 else 0.0

        result = {
            "total": total_loaded,
            "skipped": skipped,
            "skip_rate": skip_rate,
        }

        logger.info(
            "Instrument cache loaded: total=%d skipped=%d skip_rate=%.2f%%",
            total_loaded,
            skipped,
            skip_rate * 100,
        )

        return result

    def _find(self, symbol: str, exch: Exchange) -> Instrument | None:
        """Find instrument with progressive lookup."""
        clean = symbol.strip().upper()

        # 1. Try direct lookup
        inst = self._by_symbol.get((clean, exch))
        if inst is not None:
            return inst

        # 2. Try stripped lookup (no spaces, dashes)
        stripped = clean.replace(" ", "").replace("-", "").replace("_", "")
        inst = self._by_symbol.get((stripped, exch))
        if inst is not None:
            return inst

        # 3. Standardize口语 option wording (CALL -> CE, PUT -> PE)
        clean = _normalise_option_wording(clean)

        inst = self._by_symbol.get((clean, exch))
        if inst is not None:
            return inst

        # 4. Try INDEX fallback for known indices
        if clean in ("NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX"):
            index_exch = Exchange.NSE  # SCALPR doesn't have INDEX, use NSE
            inst = self._by_symbol.get((clean, index_exch))
            if inst is not None:
                return inst

        return None

    @staticmethod
    def _normalise_exchange(exchange: str) -> Exchange:
        """Normalize exchange string to Exchange enum (strict: typos raise)."""
        return normalise_exchange(exchange, strict=True)

    # ── Step size detection ──────────────────────────────────────────────────

    def auto_detect_step_sizes(self, csv_path: str | Path) -> dict[str, float]:
        """Read instrument CSV and auto-detect option strike step sizes.

        For each underlying symbol, groups option contracts at the nearest
        expiry and finds the most common difference between consecutive sorted
        strike prices.

        Args:
            csv_path: Path to the Dhan instrument master CSV file.

        Returns:
            Dict mapping underlying symbol -> detected step size (float).
        """
        import csv
        from collections import Counter, defaultdict

        options: list[tuple[str, str, float]] = []

        with open(csv_path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                instr_name = str(row.get("SEM_INSTRUMENT_NAME", "")).strip().upper()
                if instr_name not in ("OPTIDX", "OPTSTK", "OPTCOM"):
                    continue

                custom = str(row.get("SEM_CUSTOM_SYMBOL", "")).strip()
                if not custom or custom.lower() == "nan":
                    continue
                underlying = custom.split()[0].upper()

                expiry = str(row.get("SEM_EXPIRY_DATE", "")).strip()[:10]
                if not expiry:
                    continue

                strike_str = str(row.get("SEM_STRIKE_PRICE", "")).strip()
                if not strike_str or strike_str.lower() == "nan":
                    continue
                try:
                    strike = float(strike_str)
                except (ValueError, TypeError):
                    continue
                if strike <= 0:
                    continue

                options.append((underlying, expiry, strike))

        # Find nearest (earliest) expiry per underlying
        expiry_set: dict[str, set[str]] = defaultdict(set)
        for underlying, expiry, _ in options:
            expiry_set[underlying].add(expiry)

        nearest_expiry: dict[str, str] = {}
        for underlying, expiries in expiry_set.items():
            nearest_expiry[underlying] = sorted(expiries)[0]

        # Group strikes at nearest expiry only
        strikes_by_underlying: dict[str, list[float]] = defaultdict(list)
        for underlying, expiry, strike in options:
            if expiry == nearest_expiry.get(underlying):
                strikes_by_underlying[underlying].append(strike)

        # For each group: sort strikes, find most common difference
        result: dict[str, float] = {}
        for underlying, strikes in strikes_by_underlying.items():
            if len(strikes) < 2:
                continue
            strikes = sorted(set(strikes))
            if len(strikes) < 2:
                continue
            diffs = [round(strikes[i + 1] - strikes[i], 2) for i in range(len(strikes) - 1)]
            if not diffs:
                continue
            counter = Counter(diffs)
            step = counter.most_common(1)[0][0]
            if step > 0:
                result[underlying] = step

        return result

    def get_step_size(self, symbol: str) -> float:
        """Get the strike interval step size for a symbol.

        Resolution order:
        1. Known index step sizes (``INDEX_STEP_SIZES``).
        2. Auto-detected stock step sizes (from ``load_step_sizes``).
        3. Known commodity step sizes (``COMMODITY_STEP_SIZES``).
        4. Fallback to 1.0.

        Args:
            symbol: Underlying symbol (e.g. ``"NIFTY"``, ``"RELIANCE"``).

        Returns:
            Step size as float.
        """
        sym_upper = symbol.upper().strip()

        if sym_upper in INDEX_STEP_SIZES:
            return INDEX_STEP_SIZES[sym_upper]

        if sym_upper in self._stock_step_sizes:
            return self._stock_step_sizes[sym_upper]

        if sym_upper in COMMODITY_STEP_SIZES:
            return COMMODITY_STEP_SIZES[sym_upper]

        return 1.0

    def load_step_sizes(self, csv_path: str | Path | None = None) -> None:
        """Load step sizes from an instrument CSV file or use empty defaults.

        Args:
            csv_path: Path to the Dhan instrument master CSV. If ``None``,
                      only hardcoded index and commodity steps are available.
        """
        if csv_path is not None:
            self._stock_step_sizes = self.auto_detect_step_sizes(csv_path)
        else:
            self._stock_step_sizes = {}
        self._step_sizes_loaded = True


def _normalise_option_wording(symbol: str) -> str:
    """Map口语 option wording to Dhan's CE/PE contract suffix.

    Single source of truth for CALL -> CE / PUT -> PE conversion, used by
    both the runtime lookup (``_find``) and the alternate-key generator so
    the wording mapping isn't duplicated (and drift-prone) in two places.
    """
    if symbol.endswith("CALL"):
        return symbol[:-4] + "CE"
    if symbol.endswith("PUT"):
        return symbol[:-3] + "PE"
    return symbol


def _generate_alternate_keys(
    symbol: str,
    segment: Segment,
    expiry: Any,
    strike: Decimal | None,
    option_type: OptionType | None,
) -> list[str]:
    """Generate alternate symbol formats for flexible lookup."""
    keys = []

    # 1. Primary symbol
    sym_up = symbol.strip().upper()
    keys.append(sym_up)

    # 2. Stripped symbol (no spaces, dashes)
    stripped = sym_up.replace(" ", "").replace("-", "").replace("_", "")
    keys.append(stripped)

    # 3. Standardize口语 option wording (CALL -> CE, PUT -> PE)
    norm = _normalise_option_wording(sym_up)
    if norm != sym_up:
        keys.append(norm)

    # 4. For options/futures, generate common formats
    if segment in (Segment.OPTIONS, Segment.FUTURES) and expiry:
        try:
            from datetime import datetime
            if isinstance(expiry, str):
                dt = datetime.strptime(expiry[:10], "%Y-%m-%d")
            else:
                dt = datetime.combine(expiry, datetime.min.time())

            dd = dt.strftime("%d")
            dd_strip = str(int(dd))
            MMM = dt.strftime("%b").upper()
            yy = dt.strftime("%y")
            dt.strftime("%Y")

            # Extract underlying: leading alphabetic run. Handles both
            # spaced symbols ("SILVER 30 JUL 2026 FUT") and dash symbols
            # ("SILVER-28Jul2026-217000-CE") where split()[0] would grab
            # the entire symbol.
            underlying_match = re.match(r"^[A-Za-z]+", sym_up)
            underlying = underlying_match.group(0) if underlying_match else sym_up.split()[0]

            if segment == Segment.OPTIONS and option_type and strike:
                ce_pe = option_type.value
                strike_str = str(int(strike)) if strike % 1 == 0 else str(strike)
                yyyy = dt.strftime("%Y")

                # Generate common option formats
                keys.append(f"{underlying} {dd} {MMM} {yy} {strike_str} {ce_pe}")
                keys.append(f"{underlying} {dd_strip} {MMM} {yy} {strike_str} {ce_pe}")
                keys.append(f"{underlying}{dd}{MMM}{yy}{strike_str}{ce_pe}")
                keys.append(f"{underlying}{dd_strip}{MMM}{yy}{strike_str}{ce_pe}")

                # Year-less variants (e.g. "SILVER 28 JUL 217000 CE")
                keys.append(f"{underlying} {dd} {MMM} {strike_str} {ce_pe}")
                keys.append(f"{underlying} {dd_strip} {MMM} {strike_str} {ce_pe}")
                keys.append(f"{underlying}{dd}{MMM}{strike_str}{ce_pe}")
                keys.append(f"{underlying}{dd_strip}{MMM}{strike_str}{ce_pe}")

                # Full-year variants (e.g. "SILVER 28 JUL 2026 217000 CE")
                keys.append(f"{underlying} {dd} {MMM} {yyyy} {strike_str} {ce_pe}")
                keys.append(f"{underlying}{dd}{MMM}{yyyy}{strike_str}{ce_pe}")

            elif segment == Segment.FUTURES:
                keys.append(f"{underlying} {MMM} FUT")
                keys.append(f"{underlying}{MMM}FUT")
                keys.append(f"{underlying} {yy} {MMM} FUT")

        except Exception as exc:
            logger.debug("alternate_key_generation_failed: %s", exc)

    # Deduplicate
    res = []
    seen = set()
    for k in keys:
        k_clean = k.strip().upper()
        if k_clean and k_clean not in seen:
            seen.add(k_clean)
            res.append(k_clean)

    return res

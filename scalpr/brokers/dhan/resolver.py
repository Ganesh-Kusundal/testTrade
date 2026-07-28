"""O(1) symbol → Instrument resolver backed by dictionaries.

Provides fast instrument lookup with support for alternate symbol formats
and index fallback.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Iterable
from decimal import Decimal

from scalpr.brokers.dhan.exceptions import InstrumentNotFoundError
from scalpr.brokers.dhan.instrument_mapper import map_row, wire_segment_for
from scalpr.brokers.dhan.segments import normalise_exchange, to_dhan_wire
from scalpr.domain.instrument import (
    Exchange,
    Instrument,
    OptionType,
    ResolvedInstrument,
    Segment,
    SimpleInstrumentId,
)

logger = logging.getLogger(__name__)


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
        self._loaded = False
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
        return sorted(futures, key=lambda inst: inst.expiry)

    def stats(self) -> dict:
        """Get resolver statistics."""
        return {"loaded": self._loaded, "total": len(self._by_security_id)}

    def all_instruments(self) -> list[Instrument]:
        """Get all loaded instruments."""
        return list(self._by_security_id.values())

    def load_from_rows(self, rows: Iterable[dict]) -> dict[str, int | float]:
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
            f"Instrument cache loaded: total={total_loaded} skipped={skipped} skip_rate={skip_rate*100:.2f}%"
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

        # 3. Try standardizing option format (CALL -> CE, PUT -> PE)
        if clean.endswith("CALL"):
            clean = clean[:-4] + "CE"
        elif clean.endswith("PUT"):
            clean = clean[:-3] + "PE"

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


def _generate_alternate_keys(
    symbol: str,
    segment: Segment,
    expiry,
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

    # 3. Standardize option format
    if sym_up.endswith("CALL"):
        keys.append(sym_up[:-4] + "CE")
    elif sym_up.endswith("PUT"):
        keys.append(sym_up[:-3] + "PE")

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

            # Extract underlying (first word of symbol)
            underlying = sym_up.split()[0]

            if segment == Segment.OPTIONS and option_type and strike:
                ce_pe = option_type.value
                strike_str = str(int(strike)) if strike % 1 == 0 else str(strike)

                # Generate common option formats
                keys.append(f"{underlying} {dd} {MMM} {yy} {strike_str} {ce_pe}")
                keys.append(f"{underlying} {dd_strip} {MMM} {yy} {strike_str} {ce_pe}")
                keys.append(f"{underlying}{dd}{MMM}{yy}{strike_str}{ce_pe}")
                keys.append(f"{underlying}{dd_strip}{MMM}{yy}{strike_str}{ce_pe}")

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

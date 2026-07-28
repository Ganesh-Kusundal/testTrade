"""Pure-function mapper: Dhan instrument CSV row → domain Instrument.

Single translation point between the Dhan instrument master vocabulary and
SCALPR's domain model. No I/O — takes row dicts, returns MappedInstrument.
Patterns ported from Trade_XV2 v2 instrument adapter.
"""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal
from typing import NamedTuple

from scalpr.brokers.dhan.segments import (
    _COMPACT_SEGMENT_MAP,
    SEGMENT_TO_EXCHANGE,
    to_dhan_wire,
)
from scalpr.domain.instrument import Exchange, Instrument, OptionType, Segment


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


def map_row(row: dict) -> MappedInstrument | None:
    """Map a loader row dict to a MappedInstrument, or None to skip the row."""
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
            try:
                expiry = date.fromisoformat(str(expiry_str)[:10])
            except ValueError:
                pass
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

    Delegates to the canonical pair mapping in segments.to_dhan_wire;
    the legacy heuristics remain only for pairs outside that table.
    """
    try:
        return to_dhan_wire(exchange, segment)
    except ValueError:
        pass
    if exchange is Exchange.MCX:
        return "MCX_COMM"
    if exchange is Exchange.NSE_FNO or segment in (Segment.FUTURES, Segment.OPTIONS):
        return "BSE_FNO" if exchange is Exchange.BSE else "NSE_FNO"
    return "BSE_EQ" if exchange is Exchange.BSE else "NSE_EQ"


def _derive_underlying(row: dict, trading_symbol: str) -> str | None:
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


def _safe_int(value, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _safe_decimal(value, default: str = "0") -> Decimal:
    if value is None:
        return Decimal(default)
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal(default)


def _safe_opt_decimal(value) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None

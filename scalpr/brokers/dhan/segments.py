"""Dhan segment adapter — exchange and segment mappings.

Provides mappings between SCALPR's Exchange enum and Dhan's wire format
segment strings used in HTTP API requests.
"""

from __future__ import annotations

from scalpr.domain.instrument import Exchange, Segment

# Default segment for unknown exchanges
DEFAULT_SEGMENT = "NSE_EQ"

# Short exchange codes
_EXCHANGE_SHORT: dict[Exchange, str] = {
    Exchange.NSE: "NSE",
    Exchange.BSE: "BSE",
    Exchange.MCX: "MCX",
}

# Dhan HTTP/wire segment strings
_DHAN_WIRE: dict[Exchange, str] = {
    Exchange.NSE: "NSE_EQ",
    Exchange.BSE: "BSE_EQ",
    Exchange.MCX: "MCX_COMM",
    Exchange.NSE_FNO: "NSE_FNO",
    Exchange.INDEX: "IDX_I",
    Exchange.CURRENCY: "NSE_CURRENCY",
}

# Exchange string to Dhan wire segment
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
    
    Args:
        exchange: Exchange enum value or string (e.g., "NSE", "MCX")
    
    Returns:
        Dhan wire segment string (e.g., "NSE_EQ", "MCX_COMM")
    
    Raises:
        ValueError: If exchange is not recognized
    """
    if isinstance(exchange, Exchange):
        wire = _DHAN_WIRE.get(exchange)
        if wire is None:
            raise ValueError(f"No wire segment for exchange: {exchange}")
        return wire
    
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
    # Wire strings deliberately map to the enum they name (IDX_I → INDEX,
    # *_CURRENCY → CURRENCY): the resolver's _find has its own INDEX→NSE
    # fallback for well-known indices, and callers passing wire strings get
    # the semantically-true exchange back. Only the SCALPR storage-key
    # aliases below normalise to the row-storage exchange.
    "IDX_I": Exchange.INDEX,
    "NSE_CURRENCY": Exchange.CURRENCY,
    "BSE_CURRENCY": Exchange.CURRENCY,
    # Storage-key aliases: index/currency rows are stored under their raw
    # exchange (NSE/BSE per instrument_mapper), so these identifiers must
    # normalise to the storage key rather than Exchange.INDEX/CURRENCY.
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
    (Exchange.INDEX, Segment.INDEX): "IDX_I",
    (Exchange.NSE_FNO, Segment.FUTURES): "NSE_FNO",
    (Exchange.NSE_FNO, Segment.OPTIONS): "NSE_FNO",
    (Exchange.NSE, Segment.CURRENCY): "NSE_CURRENCY",
    (Exchange.CURRENCY, Segment.CURRENCY): "NSE_CURRENCY",
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

"""Dhan segment adapter — exchange and segment mappings.

Provides mappings between SCALPR's Exchange enum and Dhan's wire format
segment strings used in HTTP API requests.
"""

from __future__ import annotations

from scalpr.domain.instrument import Exchange

# Default segment for unknown exchanges
DEFAULT_SEGMENT = "NSE_EQ"

# Short exchange codes
_EXCHANGE_SHORT: dict[Exchange, str] = {
    Exchange.NSE: "NSE",
    Exchange.MCX: "MCX",
}

# Dhan HTTP/wire segment strings
_DHAN_WIRE: dict[Exchange, str] = {
    Exchange.NSE: "NSE_EQ",
    Exchange.MCX: "MCX_COMM",
}

# Exchange string to Dhan wire segment
EXCHANGE_TO_SEGMENT: dict[str, str] = {
    "NSE": "NSE_EQ",
    "MCX": "MCX_COMM",
    "INDEX": "IDX_I",  # For indices like NIFTY, BANKNIFTY
    "NFO": "NSE_FNO",  # NSE F&O
    "BFO": "BSE_FNO",  # BSE F&O
}

# Dhan wire segment to exchange string
SEGMENT_TO_EXCHANGE: dict[str, str] = {
    "NSE_EQ": "NSE",
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


def to_dhan_wire(exchange: Exchange | str) -> str:
    """Convert Exchange enum or string to Dhan wire segment string.
    
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

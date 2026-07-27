from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum


class Exchange(str, Enum):
    NSE = "NSE"
    MCX = "MCX"
    NSE_FNO = "NSE_FNO"  # F&O segment


class Segment(str, Enum):
    EQUITY = "EQUITY"
    FUTURES = "FUTURES"
    OPTIONS = "OPTIONS"
    COMMODITY = "COMMODITY"


class OptionType(str, Enum):
    CE = "CE"
    PE = "PE"


@dataclass(slots=True, frozen=True)
class Instrument:
    """Instrument definition for trading contracts."""
    symbol: str
    exchange: Exchange
    segment: Segment
    security_id: str  # Dhan numeric security ID (e.g., "2885" for RELIANCE)
    lot_size: int
    tick_size: Decimal
    option_type: OptionType | None = None
    strike: Decimal | None = None
    expiry: date | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.tick_size, Decimal):
            raise TypeError("tick_size must be a Decimal")
        if self.strike is not None and not isinstance(self.strike, Decimal):
            raise TypeError("strike must be a Decimal")
        if not isinstance(self.lot_size, int):
            raise TypeError("lot_size must be an integer")

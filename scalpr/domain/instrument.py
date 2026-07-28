from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Union


class Exchange(str, Enum):
    NSE = "NSE"
    BSE = "BSE"
    MCX = "MCX"
    NSE_FNO = "NSE_FNO"  # F&O segment
    INDEX = "INDEX"
    CURRENCY = "CURRENCY"


class Segment(str, Enum):
    EQUITY = "EQUITY"
    FUTURES = "FUTURES"
    OPTIONS = "OPTIONS"
    COMMODITY = "COMMODITY"
    INDEX = "INDEX"
    CURRENCY = "CURRENCY"


class OptionType(str, Enum):
    CE = "CE"
    PE = "PE"


class MarketFeed(str, Enum):
    LTP = "ltp"
    QUOTE = "quote"
    FULL = "full"


@dataclass(slots=True, frozen=True)
class Instrument:
    """Instrument definition for trading contracts."""
    symbol: str
    exchange: Exchange
    segment: Segment
    security_id: str  # broker-assigned instrument id; populated only by broker resolvers, opaque outside brokers
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


@dataclass(frozen=True)
class SimpleInstrumentId:
    """Equity/index identifier: 'TCS:NSE'"""
    symbol: str
    exchange: Exchange

    @classmethod
    def parse(cls, qualified: str) -> SimpleInstrumentId:
        """Parse 'SYMBOL:EXCHANGE' format."""
        parts = qualified.split(":")
        if len(parts) != 2:
            raise ValueError(f"Invalid instrument identifier: {qualified!r}. Expected 'SYMBOL:EXCHANGE'")
        symbol, exchange_str = parts[0].strip().upper(), parts[1].strip().upper()
        if not symbol:
            raise ValueError(f"Empty symbol in: {qualified!r}")
        try:
            exchange = Exchange(exchange_str)
        except ValueError:
            raise ValueError(f"Unknown exchange: {exchange_str!r}") from None
        return cls(symbol=symbol, exchange=exchange)

    def __str__(self) -> str:
        return f"{self.symbol}:{self.exchange.value}"


@dataclass(frozen=True)
class DerivativeInstrumentId:
    """Structured derivative contract."""
    underlying: str
    exchange: Exchange
    segment: Segment  # FUTURES, OPTIONS, or COMMODITY
    expiry: date
    strike: Decimal | None = None
    option_type: OptionType | None = None

    def __post_init__(self) -> None:
        if self.segment == Segment.OPTIONS:
            if self.strike is None:
                raise ValueError("OPTIONS segment requires strike")
            if self.option_type is None:
                raise ValueError("OPTIONS segment requires option_type")
        if self.segment not in (Segment.FUTURES, Segment.OPTIONS, Segment.COMMODITY):
            raise ValueError(
                f"DerivativeInstrumentId requires FUTURES, OPTIONS, or COMMODITY segment, got {self.segment!r}"
            )


InstrumentId = Union[SimpleInstrumentId, DerivativeInstrumentId]


@dataclass(frozen=True)
class ResolvedInstrument:
    """Provider-resolved instrument with wire-format mappings."""
    instrument_id: InstrumentId
    security_id: str
    exchange: Exchange
    segment: Segment
    trading_symbol: str
    dhan_exchange_segment: str
    lot_size: int | None
    tick_size: Decimal | None
    freeze_quantity: int | None
    expiry: date | None
    strike: Decimal | None
    option_type: OptionType | None

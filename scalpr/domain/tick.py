from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal


@dataclass(slots=True, frozen=True)
class Tick:
    """Real-time market tick containing price and volume information."""
    symbol: str
    ltp: Decimal
    bid: Decimal
    ask: Decimal
    delta_volume: int
    cumulative_volume: int
    exchange_timestamp: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.ltp, Decimal):
            raise TypeError("ltp must be a Decimal")
        if not isinstance(self.bid, Decimal):
            raise TypeError("bid must be a Decimal")
        if not isinstance(self.ask, Decimal):
            raise TypeError("ask must be a Decimal")
        if not isinstance(self.delta_volume, int):
            raise TypeError("delta_volume must be an integer")
        if not isinstance(self.cumulative_volume, int):
            raise TypeError("cumulative_volume must be an integer")
        if self.exchange_timestamp.tzinfo is None or self.exchange_timestamp.tzinfo.utcoffset(self.exchange_timestamp) is None:
            raise ValueError("exchange_timestamp must be timezone-aware")


@dataclass(slots=True, frozen=True)
class OHLCV:
    """Historical or aggregated OHLCV candle bar."""
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    bar_open_time: datetime
    is_closed: bool

    def __post_init__(self) -> None:
        if not isinstance(self.open, Decimal):
            raise TypeError("open must be a Decimal")
        if not isinstance(self.high, Decimal):
            raise TypeError("high must be a Decimal")
        if not isinstance(self.low, Decimal):
            raise TypeError("low must be a Decimal")
        if not isinstance(self.close, Decimal):
            raise TypeError("close must be a Decimal")
        if not isinstance(self.volume, int):
            raise TypeError("volume must be an integer")
        if self.bar_open_time.tzinfo is None or self.bar_open_time.tzinfo.utcoffset(self.bar_open_time) is None:
            raise ValueError("bar_open_time must be timezone-aware")
        if self.bar_open_time.tzinfo != timezone.utc:
            raise ValueError("bar_open_time must be timezone-aware UTC")


@dataclass(frozen=True)
class Candle:
    """Normalized OHLCV candle for historical data.

    Provider-independent: timestamps are always UTC-aware datetimes,
    prices are Decimals, volume/OI are optional ints.
    """
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int | None = None
    open_interest: int | None = None

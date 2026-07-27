from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from scalpr.domain.tick import OHLCV, Tick

IST = timezone(timedelta(hours=5, minutes=30))


class TickAggregator:
    """Thread-safe Tick-to-OHLCV candle aggregator."""

    def __init__(self, timeframe_minutes: int):
        self.timeframe_minutes = timeframe_minutes
        self.current_bars: dict[str, OHLCV] = {}
        self.lock = asyncio.Lock()

    def _get_bar_start_time(self, dt: datetime) -> datetime:
        """Calculate the bar start time in IST, returning as a UTC tz-aware datetime."""
        dt_ist = dt.astimezone(IST)
        minutes_since_midnight = dt_ist.hour * 60 + dt_ist.minute
        aligned_minutes = (minutes_since_midnight // self.timeframe_minutes) * self.timeframe_minutes
        aligned_dt_ist = dt_ist.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(minutes=aligned_minutes)
        return aligned_dt_ist.astimezone(timezone.utc)

    async def process_tick(self, tick: Tick) -> OHLCV | None:
        """Process a tick. Returns a closed OHLCV bar if rollover occurred, otherwise None."""
        async with self.lock:
            symbol = tick.symbol
            bar_start = self._get_bar_start_time(tick.exchange_timestamp)
            current_bar = self.current_bars.get(symbol)

            if current_bar is None:
                # Initial bar creation
                self.current_bars[symbol] = OHLCV(
                    open=tick.ltp,
                    high=tick.ltp,
                    low=tick.ltp,
                    close=tick.ltp,
                    volume=tick.delta_volume,
                    bar_open_time=bar_start,
                    is_closed=False,
                )
                return None

            if bar_start > current_bar.bar_open_time:
                # Rollover! Close the current bar and open a new one
                closed_bar = OHLCV(
                    open=current_bar.open,
                    high=current_bar.high,
                    low=current_bar.low,
                    close=current_bar.close,
                    volume=current_bar.volume,
                    bar_open_time=current_bar.bar_open_time,
                    is_closed=True,
                )

                # Start new bar
                self.current_bars[symbol] = OHLCV(
                    open=tick.ltp,
                    high=tick.ltp,
                    low=tick.ltp,
                    close=tick.ltp,
                    volume=tick.delta_volume,
                    bar_open_time=bar_start,
                    is_closed=False,
                )
                return closed_bar

            elif bar_start == current_bar.bar_open_time:
                # Mutate/update the current bar
                self.current_bars[symbol] = OHLCV(
                    open=current_bar.open,
                    high=max(current_bar.high, tick.ltp),
                    low=min(current_bar.low, tick.ltp),
                    close=tick.ltp,
                    volume=current_bar.volume + tick.delta_volume,
                    bar_open_time=current_bar.bar_open_time,
                    is_closed=False,
                )
                return None

            else:
                # Older tick, ignore to prevent out-of-order corruption
                return None

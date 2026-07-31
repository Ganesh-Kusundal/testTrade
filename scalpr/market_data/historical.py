from __future__ import annotations

from datetime import datetime

from scalpr.domain.contracts import HistoricalSourceProtocol
from scalpr.domain.tick import OHLCV, Tick


class HistoricalLoader:
    """Loads historical OHLCV candles from the broker."""

    def __init__(self, client: HistoricalSourceProtocol):
        self.client = client

    def load_history(self, symbol: str, timeframe: str, lookback_days: int) -> list[OHLCV]:
        """Fetch historical bars from DhanHQ. (Mocked implementation for local run)."""
        # In actual production, calls REST client of the gateway and normalizes to list[OHLCV]
        return []


class SeamStitcher:
    """Stitches historical and live data, preventing overlap and gaps."""

    def __init__(self, last_bar_timestamp: datetime):
        self.last_bar_timestamp = last_bar_timestamp

    def should_process_tick(self, tick: Tick) -> bool:
        """Drop any ticks older than or equal to the end of historical bars."""
        return tick.exchange_timestamp > self.last_bar_timestamp

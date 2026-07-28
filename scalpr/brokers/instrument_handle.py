"""Instrument handle — scoped operations on a resolved instrument.

Returned by Gateway.instrument(). Bundles a ResolvedInstrument with
references to the adapter stack for data operations.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from scalpr.domain.instrument import ResolvedInstrument


class InstrumentHandle:
    """Scoped operations on a single resolved instrument.

    Usage::

        tcs = gw.instrument("TCS:NSE")
        candles = tcs.historical(interval="1D", start="2025-01-01")
        quote = tcs.quote()
        price = tcs.ltp()
    """

    def __init__(
        self,
        resolved: ResolvedInstrument,
        market_data_adapter: Any,
        historical_adapter: Any,
    ) -> None:
        self._resolved = resolved
        self._market_data = market_data_adapter
        self._historical = historical_adapter

    @property
    def resolved(self) -> ResolvedInstrument:
        return self._resolved

    @property
    def symbol(self) -> str:
        return self._resolved.trading_symbol

    @property
    def exchange(self) -> str:
        return self._resolved.exchange.value

    @property
    def security_id(self) -> str:
        return self._resolved.security_id

    def ltp(self) -> Decimal:
        """Get current last traded price (uses pre-resolved security_id)."""
        return self._market_data.get_ltp_by_id(
            self._resolved.security_id,
            self._resolved.wire_segment,
            symbol=self.symbol,
        )

    def quote(self) -> dict[str, Any]:
        """Get full quote with all fields (uses pre-resolved security_id)."""
        return self._market_data.get_quote_by_id(
            self._resolved.security_id,
            self._resolved.wire_segment,
            symbol=self.symbol,
        )

    def depth(self, levels: int = 5) -> dict[str, Any]:
        """Get market depth (REST supports exactly 5 levels; use the
        WebSocket full mode for 20-level depth)."""
        if levels != 5:
            raise ValueError(
                f"REST depth supports exactly 5 levels, got {levels}. "
                "Use subscribe_feed(MarketFeed.FULL, ...) for 20-level depth."
            )
        return self._market_data.get_depth_by_id(
            self._resolved.security_id,
            self._resolved.wire_segment,
            symbol=self.symbol,
        )

    def historical(
        self,
        interval: str = "1D",
        start: date | datetime | str | None = None,
        end: date | datetime | str | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch historical OHLCV candles.

        Args:
            interval: Candle interval (e.g. "1D", "5m", "1h")
            start: Start date (defaults to 90 days ago)
            end: End date (defaults to today)

        Returns:
            List of candle dicts with timestamp, open, high, low, close, volume
        """
        # Parse string dates FIRST so defaults derive from the real end date
        if isinstance(start, str):
            start = date.fromisoformat(start)
        if isinstance(end, str):
            end = date.fromisoformat(end)

        if end is None:
            end = date.today()
        if start is None:
            end_d = end.date() if isinstance(end, datetime) else end
            start = end_d - timedelta(days=90)

        return self._historical.get_ohlcv(
            self.symbol,
            self.exchange,
            interval,
            start,
            end,
        )

"""Instrument handle — scoped operations on a resolved instrument.

Returned by Gateway.instrument(). Bundles a ResolvedInstrument with
references to the adapter stack for data operations.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from scalpr.brokers.errors import OptionChainNotSupported
from scalpr.domain.instrument import ResolvedInstrument

# Wire segments that support option chain queries
_OPTIONABLE_SEGMENTS = frozenset({"NSE_FNO", "BSE_FNO", "IDX_I", "MCX_COMM"})


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
        option_chain_adapter: Any = None,
        ws_manager: Any = None,
        ws_loop: Any = None,
    ) -> None:
        self._resolved = resolved
        self._market_data = market_data_adapter
        self._historical = historical_adapter
        self._option_chain = option_chain_adapter
        self._ws_manager = ws_manager
        self._ws_loop = ws_loop

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

    @property
    def id(self):
        """Instrument identity (SimpleInstrumentId or DerivativeInstrumentId)."""
        return self._resolved.instrument_id

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

    def ohlc(self) -> dict[str, Any]:
        """Get today's OHLC from the live quote.

        Returns:
            Dict with keys: open, high, low, close, ltp, volume, change, change_percent
        """
        q = self.quote()
        return {
            "open": q.get("open"),
            "high": q.get("high"),
            "low": q.get("low"),
            "close": q.get("close"),
            "ltp": q.get("ltp"),
            "volume": q.get("volume"),
            "change": q.get("change"),
            "change_percent": q.get("change_percent"),
        }

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

    def option_chain(self, expiry: date | None = None) -> list[dict[str, Any]]:
        """Fetch the option chain for this instrument's underlying.

        Only available for indices and F&O instruments. Raises
        OptionChainNotSupported for plain equities (NSE_EQ / BSE_EQ).

        Args:
            expiry: Specific expiry date. If None, next expiry is used.

        Returns:
            Flat list of dicts with keys:
            symbol, security_id, strike, bid, ask, oi, volume, delta
        """
        wire_seg = self._resolved.wire_segment
        if wire_seg not in _OPTIONABLE_SEGMENTS:
            raise OptionChainNotSupported(
                f"Option chain not supported for {self.symbol} ({self.exchange}) "
                f"— only available for indices and F&O instruments"
            )
        if self._option_chain is None:
            raise OptionChainNotSupported(
                f"Option chain adapter not available for {self.symbol}"
            )
        return self._option_chain.get_option_chain(
            self.symbol,
            self.exchange,
            expiry=expiry,
        )

    def subscribe(
        self,
        mode: Any,
        on_event: Any,
    ) -> None:
        """Subscribe to live market data for this instrument.

        Args:
            mode: MarketFeed enum (LTP, QUOTE, or FULL)
            on_event: Callback for market events
        """
        if self._ws_manager is None or self._ws_loop is None:
            raise RuntimeError(
                "WebSocket manager not available. "
                "Ensure the Gateway was initialised with streaming support."
            )
        import asyncio
        pair = (self.symbol, self.exchange)
        asyncio.run_coroutine_threadsafe(
            self._ws_manager.subscribe_pairs(
                [pair],
                mode=mode.value if hasattr(mode, "value") else str(mode),
            ),
            self._ws_loop,
        ).result(timeout=15)
        if on_event:
            self._ws_manager.add_subscriber(on_event)

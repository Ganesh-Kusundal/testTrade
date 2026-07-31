from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime
from decimal import Decimal
from typing import Any

from scalpr.domain.contracts import BrokerClientProtocol, MarketDepth, Quote
from scalpr.domain.instrument import (
    MarketFeed,
    ResolvedInstrument,
)
from scalpr.domain.tick import OHLC, Candle, FullEvent, QuoteEvent, TickerEvent
from scalpr.gateway.subscription import Subscription

logger = logging.getLogger(__name__)


class MarketDataService:
    """Broker-agnostic market data service that converts raw adapter responses
    into canonical domain objects (Quote, OHLC, MarketDepth, Candle, events).
    """

    def __init__(self, client: BrokerClientProtocol) -> None:
        self._client = client

    def quote(self, resolved: ResolvedInstrument) -> Quote:
        """Return canonical Quote domain object."""
        return self._client.get_quote(resolved)

    def ohlc(self, resolved: ResolvedInstrument) -> OHLC:
        """Return OHLC snapshot from quote data."""
        quote = self.quote(resolved)
        return OHLC(
            open=quote.open,
            high=quote.high,
            low=quote.low,
            close=quote.close,
            timestamp=quote.timestamp,
        )

    def depth(self, resolved: ResolvedInstrument, levels: int = 5) -> MarketDepth:
        """Return market depth with up to `levels` bid/ask levels."""
        full = self._client.get_market_depth(resolved)
        return MarketDepth(
            symbol=full.symbol,
            exchange=full.exchange,
            bid_levels=full.bid_levels[:levels],
            ask_levels=full.ask_levels[:levels],
            timestamp=full.timestamp,
        )

    def historical(
        self,
        resolved: ResolvedInstrument,
        interval: str = "1D",
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[Candle]:
        """Return normalized candle list.

        Dhan returns column-array dicts; we convert to Candle domain objects
        with Decimal prices and UTC-aware timestamps.
        """
        symbol = resolved.trading_symbol
        exchange = resolved.exchange.value
        timeframe = "DAY" if interval.upper() in ("1D", "DAY") else "INTRADAY"
        interval_minutes = int(interval.rstrip("Dm").rstrip("h")) if interval[-1] in ("m", "h") else 5

        raw = self._client.get_historical(
            symbol, exchange, timeframe=timeframe, interval=interval_minutes,
            from_date=start.strftime("%Y-%m-%d") if start else None,
            to_date=end.strftime("%Y-%m-%d") if end else None,
        )

        if isinstance(raw, list):
            return [_dict_to_candle(c) for c in raw]
        return []

    def subscribe_feed(
        self,
        mode: MarketFeed,
        instruments: list[ResolvedInstrument] | list[str],
        on_event: Callable[[TickerEvent | QuoteEvent | FullEvent], None],
    ) -> Subscription:
        """Subscribe to live market feed.

        Batches instruments into groups of 100 per Dhan's limit.
        Returns a Subscription handle.
        """
        resolved_list = self._resolve_all(instruments)
        sub_id = f"sub-{id(on_event)}"

        for i in range(0, len(resolved_list), 100):
            batch = resolved_list[i : i + 100]
            if mode == MarketFeed.TICKER or mode == MarketFeed.QUOTE:
                for r in batch:
                    self._client.subscribe_quotes(r)
            elif mode == MarketFeed.FULL:
                for r in batch:
                    self._client.subscribe_market_depth(r, level=5)

        return Subscription(
            id=sub_id,
            instruments=[str(r.instrument_id) for r in resolved_list],
            mode=mode,
        )

    def unsubscribe(self, subscription: Subscription) -> None:
        """Unsubscribe from a live feed subscription."""
        if not subscription.is_active:
            return
        subscription.deactivate()

    def _resolve_all(self, instruments: list[ResolvedInstrument] | list[str]) -> list[ResolvedInstrument]:
        result: list[ResolvedInstrument] = []
        for inst in instruments:
            if isinstance(inst, ResolvedInstrument):
                result.append(inst)
            else:
                result.append(self._client.resolve_instrument(inst))
        return result


def _dict_to_candle(d: dict[str, Any]) -> Candle:
    """Convert a raw dict candle to a Candle domain object."""
    ts = d.get("timestamp")
    if isinstance(ts, datetime):
        timestamp = ts
    elif isinstance(ts, (int, float)):
        timestamp = datetime.fromtimestamp(float(ts))
    else:
        timestamp = datetime.now()

    return Candle(
        timestamp=timestamp,
        open=Decimal(str(d.get("open", 0))),
        high=Decimal(str(d.get("high", 0))),
        low=Decimal(str(d.get("low", 0))),
        close=Decimal(str(d.get("close", 0))),
        volume=int(d.get("volume", 0)) if d.get("volume") is not None else None,
        open_interest=int(d.get("oi", 0)) if d.get("oi") is not None else None,
    )

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import date, datetime
from typing import Any

from scalpr.domain.contracts import MarketDepth, Quote
from scalpr.domain.instrument import ResolvedInstrument
from scalpr.domain.tick import OHLC, Candle
from scalpr.gateway.market_data_service import MarketDataService
from scalpr.gateway.subscription import Subscription

logger = logging.getLogger(__name__)


class Instrument:
    """Domain object representing a resolved tradable instrument.

    Wraps a ResolvedInstrument and delegates market-data operations to
    MarketDataService. Only operations valid for the instrument type
    should be allowed (e.g., option_chain requires an index/underlying).
    """

    def __init__(
        self,
        resolved: ResolvedInstrument,
        market_data: MarketDataService,
        option_chain_service: Any = None,
    ) -> None:
        self.id = resolved.instrument_id
        self.resolved = resolved
        self._md = market_data
        self._oc = option_chain_service

    def historical(
        self,
        interval: str = "1D",
        start: datetime | date | None = None,
        end: datetime | date | None = None,
    ) -> list[Candle]:
        """Return normalized candle list for the given interval."""
        return self._md.historical(self.resolved, interval=interval, start=start, end=end)

    def quote(self) -> Quote:
        """Return canonical Quote domain object."""
        return self._md.quote(self.resolved)

    def ohlc(self) -> OHLC:
        """Return OHLC snapshot."""
        return self._md.ohlc(self.resolved)

    def depth(self, levels: int = 5) -> MarketDepth:
        """Return market depth with up to `levels` bid/ask levels."""
        return self._md.depth(self.resolved, levels=levels)

    def subscribe(
        self,
        mode: Any,
        on_event: Callable[[Any], None],
    ) -> Subscription:
        """Subscribe to live market feed for this instrument."""
        return self._md.subscribe_feed(mode, [self.resolved], on_event)

    def option_chain(self, expiry: date | None = None) -> Any:
        """Return option chain for this instrument.

        Requires an index or underlying instrument.
        """
        if self._oc is None:
            raise OptionChainNotSupported("Option chain service not available")
        return self._oc.chain(self.resolved, expiry)

    def expired_options(
        self,
        expiry: date,
        start: date,
        end: date,
    ) -> list[Any]:
        """Return expired option candles for the given expiry window."""
        if self._oc is None:
            raise OptionChainNotSupported("Option chain service not available")
        return self._oc.expired_options(self.resolved, expiry, start, end)


class OptionChainNotSupported(Exception):
    """Raised when option chain is requested for an instrument that doesn't support it."""

from __future__ import annotations

import logging
from typing import Any, Callable

from scalpr.adapters.dhan.client import DhanClient
from scalpr.domain.instrument import (
    Exchange,
    ResolvedInstrument,
    Segment,
    SimpleInstrumentId,
    MarketFeed,
)
from scalpr.domain.tick import TickerEvent, QuoteEvent, FullEvent
from scalpr.engine.clock import Clock, LiveClock
from scalpr.engine.message_bus import MessageBus, RecordingBus
from scalpr.gateway.account_service import AccountService
from scalpr.gateway.instrument import Instrument
from scalpr.gateway.market_data_service import MarketDataService
from scalpr.gateway.order_service import OrderService
from scalpr.gateway.order_update_service import OrderUpdateService
from scalpr.gateway.portfolio_service import PortfolioService
from scalpr.gateway.risk_service import RiskService
from scalpr.gateway.subscription import Subscription
from scalpr.gateway.trader_control_service import TraderControlService

logger = logging.getLogger(__name__)


class Gateway:
    """Application facade — single entry point for the application.

    The gateway never constructs Dhan payloads directly. It delegates to
    domain services which in turn use the adapter.
    """

    def __init__(
        self,
        client: DhanClient | None = None,
        bus: MessageBus | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._client = client or DhanClient()
        self._bus = bus or RecordingBus()
        self._clock = clock or LiveClock()

        self._market_data = MarketDataService(self._client)
        self._risk = RiskService(self._client)
        self._orders = OrderService(
            client=self._client,
            bus=self._bus,
            clock=self._clock,
            risk=self._risk,
        )
        self._portfolio = PortfolioService(self._client)
        self._account = AccountService(self._client)
        self._trader_control = TraderControlService(self._client)
        self._order_updates = OrderUpdateService(self._client, bus=self._bus)

        self._started = False

    @property
    def orders(self) -> OrderService:
        return self._orders

    @property
    def portfolio(self) -> PortfolioService:
        return self._portfolio

    @property
    def account(self) -> AccountService:
        return self._account

    @property
    def trader_control(self) -> TraderControlService:
        return self._trader_control

    @property
    def order_updates(self) -> OrderUpdateService:
        return self._order_updates

    def start(self) -> None:
        """Start the gateway — connect WebSocket and start message bus."""
        if self._started:
            return
        self._client.start()
        self._started = True

    def stop(self) -> None:
        """Stop the gateway — disconnect WebSocket."""
        if not self._started:
            return
        self._client.stop()
        self._started = False

    def instrument(
        self,
        identifier: str | SimpleInstrumentId | ResolvedInstrument | Instrument,
        exchange: Exchange | None = None,
        segment: Segment | None = None,
    ) -> Instrument:
        """Resolve an instrument identifier into a domain Instrument object."""
        if isinstance(identifier, Instrument):
            return identifier
        if isinstance(identifier, ResolvedInstrument):
            return Instrument(resolved=identifier, market_data=self._market_data)
        if isinstance(identifier, SimpleInstrumentId):
            resolved = self._client.resolve_instrument(identifier)
            return Instrument(resolved=resolved, market_data=self._market_data)

        if isinstance(identifier, str):
            resolved = self._client.resolve_instrument(identifier)
            return Instrument(resolved=resolved, market_data=self._market_data)

        raise ValueError(f"Cannot resolve instrument from {type(identifier)}")

    def subscribe_feed(
        self,
        mode: MarketFeed,
        instruments: Instrument | list[Instrument] | str | list[str],
        on_event: Callable[[TickerEvent | QuoteEvent | FullEvent], None] | None = None,
    ) -> Subscription:
        """Subscribe to live market feed."""
        if isinstance(instruments, (str, Instrument)):
            instruments = [instruments]

        resolved_list: list[ResolvedInstrument] = []
        for inst in instruments:
            if isinstance(inst, Instrument):
                resolved_list.append(inst.resolved)
            elif isinstance(inst, ResolvedInstrument):
                resolved_list.append(inst)
            elif isinstance(inst, str):
                resolved_list.append(self._client.resolve_instrument(inst))
            else:
                raise ValueError(f"Cannot resolve instrument from {type(inst)}")

        return self._market_data.subscribe_feed(mode, resolved_list, on_event or (lambda e: None))

    def unsubscribe(self, subscription: Subscription) -> None:
        """Unsubscribe from a live feed subscription."""
        self._market_data.unsubscribe(subscription)

    def profile(self) -> dict[str, Any]:
        """Return account profile."""
        return self._client.get_profile()

    def renew_token(self) -> str:
        """Renew the access token."""
        return self._client.renew_access_token()

    def capabilities(self) -> dict[str, Any]:
        """Return account capabilities."""
        return self._client.get_capabilities()

    def close(self) -> None:
        """Close the gateway and release all resources."""
        self.stop()

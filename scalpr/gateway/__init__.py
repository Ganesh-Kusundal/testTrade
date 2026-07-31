from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from scalpr.domain.contracts import BrokerClientProtocol
from scalpr.domain.instrument import (
    Exchange,
    MarketFeed,
    ResolvedInstrument,
    Segment,
    SimpleInstrumentId,
)
from scalpr.domain.tick import FullEvent, QuoteEvent, TickerEvent
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

# ── Broker factory registry ─────────────────────────────────────────────
# Maps broker names to factory functions.  Each factory receives a `config`
# dict and returns a BrokerClientProtocol.  New brokers register here —
# Gateway never imports a concrete adapter directly.

_broker_factories: dict[str, Callable[[dict], BrokerClientProtocol]] = {}


def register_broker(name: str, factory: Callable[[dict], BrokerClientProtocol]) -> None:
    """Register a broker factory by name (e.g. 'dhan', 'upstox')."""
    _broker_factories[name] = factory


def create_broker_client(name: str, config: dict | None = None) -> BrokerClientProtocol:
    """Create a broker client by registered name."""
    if name not in _broker_factories:
        raise ValueError(
            f"Unknown broker {name!r}.  Registered: {list(_broker_factories)}"
        )
    return _broker_factories[name](config or {})


def _create_dhan_client(config: dict) -> BrokerClientProtocol:
    """Lazy factory for DhanClient — only imported when called.

    ``config`` may contain: bus (MessageBus), clock (Clock),
    and any DhanClient-specific keys (client_id, access_token, etc.).
    bus/clock are extracted and the rest is passed to DhanClient.
    """
    from scalpr.adapters.dhan.client import DhanClient
    bus = config.get("bus", RecordingBus())
    clock = config.get("clock", LiveClock())
    dhan_config = {k: v for k, v in config.items() if k not in ("bus", "clock")}
    return DhanClient(bus=bus, clock=clock, config=dhan_config)


# Register the default broker at import time (lazy import inside factory).
register_broker("dhan", _create_dhan_client)


class Gateway:
    """Application facade — single entry point for the application.

    The gateway never constructs Dhan payloads directly. It delegates to
    domain services which in turn use the adapter.
    """

    def __init__(
        self,
        client: BrokerClientProtocol | None = None,
        bus: MessageBus | None = None,
        clock: Clock | None = None,
        broker: str | None = None,
        broker_config: dict | None = None,
    ) -> None:
        if client is not None:
            self._client = client
        else:
            _broker = broker or "dhan"
            cfg = dict(broker_config or {})
            cfg.setdefault("bus", bus or RecordingBus())
            cfg.setdefault("clock", clock or LiveClock())
            self._client = create_broker_client(_broker, cfg)
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

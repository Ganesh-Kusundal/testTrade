"""Canonical contract models for broker-agnostic data exchange.

These models define the standard return types for all gateway operations,
ensuring no broker-specific fields leak into application code.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Protocol, runtime_checkable

from scalpr.domain.order import OrderSide
from scalpr.domain.position import Position
from scalpr.domain.tick import DepthLevel
from scalpr.domain.values import ZERO

# ── Protocols for broker-specific adapters ─────────────────────────────
# These define the structural typing contracts that Dhan (or future broker)
# adapters must satisfy. Using Protocol allows duck-typing without requiring
# explicit inheritance, enabling clean separation between the broker-agnostic
# facade and broker-specific implementations.


@runtime_checkable
class HttpClientProtocol(Protocol):
    """Protocol for broker HTTP clients.

    Defines the contract that any broker-specific HTTP client must satisfy.
    The broker-agnostic facade and adapters depend on this protocol, not on
    concrete implementations like DhanHttpClient.
    """

    def post(self, endpoint: str, json: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute HTTP POST request."""
        ...

    def get(self, endpoint: str) -> dict[str, Any]:
        """Execute HTTP GET request."""
        ...

    def put(self, endpoint: str, json: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute HTTP PUT request."""
        ...

    def delete(self, endpoint: str) -> dict[str, Any]:
        """Execute HTTP DELETE request."""
        ...

    def update_token(self, access_token: str) -> None:
        """Update the access token for authenticated requests."""
        ...

    def close(self) -> None:
        """Close the HTTP session and release resources."""
        ...


@runtime_checkable
class ResolverProtocol(Protocol):
    """Protocol for instrument resolution.

    Defines the contract that any broker-specific symbol resolver must satisfy.
    The broker-agnostic facade and adapters depend on this protocol, not on
    concrete implementations like SymbolResolver.
    """

    def resolve(self, symbol: str, exchange: str) -> Any:
        """Resolve symbol+exchange to an Instrument."""
        ...

    def resolve_full(self, symbol: str, exchange: str) -> Any:
        """Resolve symbol+exchange to a full ResolvedInstrument."""
        ...

    def get_by_symbol(self, symbol: str, exchange: str) -> Any | None:
        """Look up instrument by symbol and exchange."""
        ...

    def get_by_security_id(self, security_id: str) -> Any | None:
        """Look up instrument by security ID."""
        ...

    def get_lot_size(self, symbol: str, exchange: str) -> int:
        """Get the lot size for a given instrument."""
        ...

    def wire_segment_of(self, symbol: str, exchange: str) -> str:
        """Get the wire-format segment string for an instrument."""
        ...

    def instrument_kind_of(self, symbol: str, exchange: str) -> str:
        """Get the instrument kind (EQ, FUT, OPT, etc.) for an instrument."""
        ...


@runtime_checkable
class ExecutionGatewayProtocol(Protocol):
    """Outward port for order placement and position enquiry.

    Consumers in risk/, oms/ and strategy/ depend on this, never on a
    concrete broker adapter — the broker is a replaceable detail.
    """

    def get_positions(self) -> list[Any]:
        """Return current broker positions."""
        ...

    def place_order(self, order: Any) -> str:
        """Submit an order; return the broker's order id."""
        ...


@runtime_checkable
class HistoricalSourceProtocol(Protocol):
    """Outward port for historical candle retrieval."""

    def get_historical(
        self,
        symbol: str,
        exchange: str,
        timeframe: str,
        lookback_days: int,
    ) -> list[dict[str, Any]]:
        """Return raw historical candles for the given instrument."""
        ...


@runtime_checkable
class BrokerClientProtocol(Protocol):
    """Outward port covering every method the gateway layer uses on a broker client.

    Every gateway service (orders, portfolio, market-data, risk, account,
    trader-control, order-updates) depends on this protocol, never on a
    concrete adapter class like DhanClient.  Adding a second broker means
    implementing this protocol — zero changes to the gateway layer.

    ``Any`` return types are intentional: the gateway services are the ones
    that map raw dicts into domain objects, so the protocol only guarantees
    that the method exists, not its shape.
    """

    broker: str

    # ── lifecycle ─────────────────────────────────────────────────────
    def start(self) -> None: ...
    def stop(self) -> None: ...

    # ── instrument resolution ─────────────────────────────────────────
    def resolve_instrument(self, identifier: Any) -> Any: ...

    # ── orders (bus-driven path lives in the adapter; these are the
    #    query/CRUD helpers that gateway services call directly) ────────
    def get_order_detail(self, order_id: str, **kw: Any) -> Any: ...
    def get_trade_book(self, **kw: Any) -> Any: ...
    def cancel_all_orders(self, symbol: str | None = None) -> int: ...

    # ── portfolio ─────────────────────────────────────────────────────
    def get_positions(self, **kw: Any) -> list[Position]: ...
    def get_holdings(self, **kw: Any) -> Any: ...
    def get_funds(self, **kw: Any) -> Any: ...
    def margin_calculator(
        self,
        security_id: str,
        exchange_segment: str,
        transaction_type: str,
        quantity: int,
        product_type: str,
        price: float,
        trigger_price: float = 0,
    ) -> Any: ...

    # ── market data ───────────────────────────────────────────────────
    def get_quote(self, resolved: Any) -> Any: ...
    def get_market_depth(self, resolved: Any) -> Any: ...
    def get_historical(
        self,
        symbol: str,
        exchange: str,
        timeframe: str = "DAY",
        interval: int = 5,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> Any: ...
    def subscribe_quotes(self, resolved: Any) -> None: ...
    def subscribe_market_depth(self, resolved: Any, level: int = 20) -> None: ...
    def unsubscribe_quotes(self, resolved: Any) -> None: ...
    def unsubscribe_market_depth(self, resolved: Any) -> None: ...

    # ── trader control ────────────────────────────────────────────────
    def kill_switch(self, action: str) -> str: ...
    def status_kill_switch(self) -> str: ...

    # ── order-update WebSocket (may be a no-op in adapters that use
    #    polling instead) ──────────────────────────────────────────────
    def connect_order_updates(self) -> None: ...
    def disconnect_order_updates(self) -> None: ...

    # ── auth / profile (used by Gateway facade only) ──────────────────
    def get_profile(self) -> Any: ...
    def renew_access_token(self) -> str: ...
    def get_capabilities(self) -> Any: ...


@dataclass(frozen=True)
class Quote:
    """Canonical market quote model with all Dhan quote fields.

    Returned by Gateway.quote() and InstrumentHandle.quote().
    """

    symbol: str
    exchange: str
    ltp: Decimal
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    change: Decimal = ZERO
    change_percent: Decimal = ZERO
    timestamp: datetime | None = None
    average_price: Decimal = ZERO
    buy_quantity: int = 0
    sell_quantity: int = 0
    last_quantity: int = 0
    last_trade_time: datetime | None = None
    lower_circuit_limit: Decimal = ZERO
    upper_circuit_limit: Decimal = ZERO
    oi: int = 0
    oi_day_high: Decimal = ZERO
    oi_day_low: Decimal = ZERO


@dataclass(frozen=True)
class MarketDepth:
    """Canonical market depth model with bid/ask levels.

    Returned by Gateway.depth().
    """

    symbol: str
    exchange: str
    bid_levels: list[DepthLevel]
    ask_levels: list[DepthLevel]
    timestamp: datetime | None = None


@dataclass(frozen=True)
class Holding:
    """Canonical holdings model for long-term delivery positions.

    Returned by Gateway.holdings().
    """

    symbol: str
    exchange: str
    quantity: int
    average_price: Decimal
    current_price: Decimal
    pnl: Decimal = ZERO
    pnl_percent: Decimal = ZERO


@dataclass(frozen=True)
class Funds:
    """Canonical funds and margin model.

    Returned by Gateway.funds().
    """

    available_margin: Decimal
    used_margin: Decimal
    total_balance: Decimal
    collateral: Decimal = ZERO
    realtime: bool = True


@dataclass(frozen=True)
class Trade:
    """Canonical trade/execution fill model.

    Returned by Gateway.trades().
    """

    trade_id: str
    order_id: str
    symbol: str
    exchange: str
    side: OrderSide
    quantity: int
    price: Decimal
    timestamp: datetime | None = None

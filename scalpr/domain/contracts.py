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
from scalpr.domain.tick import DepthLevel, OHLC
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

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum

from scalpr.domain.instrument import Exchange
from scalpr.domain.values import ZERO


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


# Alias for spec compatibility — Side and OrderSide are the same concept
Side = OrderSide


class OrderType(str, Enum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"
    STOP_LOSS = "STOP_LOSS"
    STOP_LOSS_MARKET = "STOP_LOSS_MARKET"


class ProductType(str, Enum):
    INTRADAY = "INTRADAY"
    DELIVERY = "DELIVERY"
    MARGIN = "MARGIN"
    COVER_ORDER = "COVER_ORDER"


class Validity(str, Enum):
    DAY = "DAY"
    IOC = "IOC"
    GTD = "GTD"
    GTC = "GTC"


class OrderState(str, Enum):
    PENDING = "PENDING"
    OPEN = "OPEN"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"

    @property
    def is_terminal(self) -> bool:
        return self in (
            OrderState.FILLED,
            OrderState.CANCELLED,
            OrderState.REJECTED,
            OrderState.EXPIRED,
        )


ORDER_STATE_TRANSITIONS: dict[OrderState, frozenset[OrderState]] = {
    OrderState.PENDING: frozenset({
        OrderState.OPEN,
        OrderState.PARTIALLY_FILLED,
        OrderState.FILLED,
        OrderState.CANCELLED,
        OrderState.REJECTED,
    }),
    OrderState.OPEN: frozenset({
        OrderState.PARTIALLY_FILLED,
        OrderState.FILLED,
        OrderState.CANCELLED,
        OrderState.REJECTED,
        OrderState.EXPIRED,
    }),
    OrderState.PARTIALLY_FILLED: frozenset({
        OrderState.FILLED,
        OrderState.CANCELLED,
        OrderState.REJECTED,
        OrderState.EXPIRED,
    }),
    OrderState.FILLED: frozenset(),
    OrderState.CANCELLED: frozenset(),
    OrderState.REJECTED: frozenset(),
    OrderState.EXPIRED: frozenset(),
}


@dataclass(slots=True, frozen=True)
class Order:
    """Order represents an order execution request and status."""
    order_id: str
    symbol: str
    exchange: Exchange
    side: OrderSide
    order_type: OrderType
    quantity: int
    price: Decimal = ZERO
    trigger_price: Decimal = ZERO
    state: OrderState = OrderState.PENDING
    filled_quantity: int = 0
    avg_price: Decimal = ZERO
    timestamp: datetime | None = None
    product_type: str = "INTRADAY"
    validity: str = "DAY"
    reject_reason: str = ""
    correlation_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.price, Decimal):
            raise TypeError("price must be a Decimal")
        if not isinstance(self.trigger_price, Decimal):
            raise TypeError("trigger_price must be a Decimal")
        if not isinstance(self.avg_price, Decimal):
            raise TypeError("avg_price must be a Decimal")
        if not isinstance(self.quantity, int):
            raise TypeError("quantity must be an integer")
        if not isinstance(self.filled_quantity, int):
            raise TypeError("filled_quantity must be an integer")
        if self.quantity <= 0:
            raise ValueError("quantity must be positive")
        if self.filled_quantity < 0:
            raise ValueError("filled_quantity must be non-negative")
        if self.filled_quantity > self.quantity:
            raise ValueError("filled_quantity cannot exceed quantity")
        if not self.symbol:
            raise ValueError("symbol must be non-empty")
        if self.price < 0:
            raise ValueError("price must be non-negative")
        if self.trigger_price < 0:
            raise ValueError("trigger_price must be non-negative")
        if self.order_type == OrderType.LIMIT and self.price <= 0:
            raise ValueError("LIMIT orders must have price > 0")
        if self.timestamp is not None and self.timestamp > datetime.now(timezone.utc):
            raise ValueError("timestamp cannot be in the future")

    def transition_to(self, new_state: OrderState) -> Order:
        """Validate FSM transitions and return a new Order copy."""
        allowed = ORDER_STATE_TRANSITIONS.get(self.state, frozenset())
        if new_state not in allowed:
            raise ValueError(f"Invalid transition from {self.state} to {new_state}")
        return replace(self, state=new_state)

    def is_active(self) -> bool:
        """Return True if order is in a non-terminal state."""
        return not self.state.is_terminal

    def notional_value(self) -> Decimal:
        """Return price * quantity as Decimal."""
        return self.price * Decimal(self.quantity)

    def remaining_quantity(self) -> int:
        """Return unfilled quantity."""
        return self.quantity - self.filled_quantity

    def fill_ratio(self) -> Decimal:
        """Return ratio of filled to total quantity."""
        if self.quantity == 0:
            return ZERO
        return Decimal(self.filled_quantity) / Decimal(self.quantity)


@dataclass(frozen=True)
class OrderRequest:
    """Immutable order placement request."""
    instrument: str  # symbol or InstrumentId
    side: Side
    quantity: int
    order_type: OrderType = OrderType.LIMIT
    product: ProductType = ProductType.INTRADAY
    validity: Validity = Validity.DAY
    price: Decimal | None = None
    trigger_price: Decimal | None = None
    correlation_id: str | None = None


@dataclass(frozen=True)
class ModifyOrderRequest:
    """Immutable order modification request."""
    quantity: int | None = None
    price: Decimal | None = None
    trigger_price: Decimal | None = None
    validity: Validity | None = None


# ── Broker-agnostic status mapping ──────────────────────────────────────
# Canonical mapping from broker status strings to OrderState.  Both the
# gateway layer (order_service._safe_order_state) and the adapter layer
# (mapper_orders.order_status_from_dhan) import this single source of
# truth so status translations never drift.
#
# Broker-specific adapters translate their own status strings (e.g.
# "PART_TRADED", "TRANSIT", "TRADED") into these generic keys before
# they reach the gateway.

BROKER_STATUS_TO_ORDER_STATE: dict[str, OrderState] = {
    "PENDING": OrderState.PENDING,
    "OPEN": OrderState.OPEN,
    "TRIGGER PENDING": OrderState.PENDING,
    "TRANSIT": OrderState.PENDING,
    "PARTIALLY FILLED": OrderState.PARTIALLY_FILLED,
    "PART_TRADED": OrderState.PARTIALLY_FILLED,
    "FILLED": OrderState.FILLED,
    "TRADED": OrderState.FILLED,
    "CANCELLED": OrderState.CANCELLED,
    "REJECTED": OrderState.REJECTED,
    "EXPIRED": OrderState.EXPIRED,
}


def broker_status_to_order_state(raw: str) -> OrderState:
    """Map a broker status string to an OrderState.

    Returns OrderState.PENDING for unknown strings rather than raising,
    so the Order constructor never blows up on an exotic status.
    """
    return BROKER_STATUS_TO_ORDER_STATE.get(raw.strip().upper(), OrderState.PENDING)

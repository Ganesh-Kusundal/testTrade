"""Domain events for the SCALPR trading system.

All events are frozen dataclasses (immutable) with UTC timestamps.
Events represent significant state changes in the domain that other
components may need to react to.

Event Types:
    Order Events: OrderPlaced, OrderModified, OrderUpdated, OrderCancelled,
                  OrderRejected, OrderExpired
    Fill Events: FillReceived
    Position Events: PositionOpened, PositionClosed, PositionReversed, PositionUpdated
    Market Data Events: TickReceived, BarClosed, HistoricalDataLoaded
    Signal Events: SignalGenerated, GateFailed
    Risk Events: RiskCheckPassed, RiskCheckFailed, CircuitBreakerTripped, SessionHalted
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone

from scalpr.domain.fill import Fill
from scalpr.domain.order import Order
from scalpr.domain.position import Position
from scalpr.domain.signal import Signal
from scalpr.domain.tick import OHLCV, Tick

logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class DomainEvent:
    """Base class for all domain events. Immutable with UTC timestamp."""
    timestamp: datetime

    def __post_init__(self) -> None:
        if self.timestamp.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware UTC")
        if self.timestamp.tzinfo != timezone.utc:
            raise ValueError("timestamp must be timezone-aware UTC")


@dataclass(slots=True, frozen=True)
class OrderPlaced(DomainEvent):
    """Event published when a new order is submitted."""
    order: Order


@dataclass(slots=True, frozen=True)
class OrderModified(DomainEvent):
    """Event published when an order is modified."""
    order: Order
    old_price: float
    old_quantity: int


@dataclass(slots=True, frozen=True)
class OrderCancelled(DomainEvent):
    """Event published when an order is cancelled."""
    order: Order
    reason: str = ""


@dataclass(slots=True, frozen=True)
class OrderRejected(DomainEvent):
    """Event published when an order is rejected by broker."""
    order: Order
    error_code: str = ""
    error_message: str = ""


@dataclass(slots=True, frozen=True)
class OrderExpired(DomainEvent):
    """Event published when an order expires."""
    order: Order


@dataclass(slots=True, frozen=True)
class OrderUpdated(DomainEvent):
    """Event published when an order is updated (e.g., state change)."""
    order: Order
    previous_state: str


@dataclass(slots=True, frozen=True)
class FillReceived(DomainEvent):
    """Event published when an execution fill is received."""
    fill: Fill


@dataclass(slots=True, frozen=True)
class PositionOpened(DomainEvent):
    """Event published when a new position is opened."""
    position: Position


@dataclass(slots=True, frozen=True)
class PositionClosed(DomainEvent):
    """Event published when a position is fully closed."""
    position: Position
    realized_pnl: float


@dataclass(slots=True, frozen=True)
class PositionReversed(DomainEvent):
    """Event published when a position is reversed (long→short or vice versa)."""
    position: Position
    old_side: str
    new_side: str


@dataclass(slots=True, frozen=True)
class PositionUpdated(DomainEvent):
    """Event published when a position is updated (e.g., quantity change)."""
    position: Position
    previous_quantity: int


@dataclass(slots=True, frozen=True)
class TickReceived(DomainEvent):
    """Event published when a market tick is received."""
    tick: Tick


@dataclass(slots=True, frozen=True)
class BarClosed(DomainEvent):
    """Event published when a new OHLCV bar is closed."""
    bar: OHLCV
    symbol: str


@dataclass(slots=True, frozen=True)
class HistoricalDataLoaded(DomainEvent):
    """Event published when historical data is loaded."""
    symbol: str
    bar_count: int
    start_time: datetime
    end_time: datetime


@dataclass(slots=True, frozen=True)
class SignalGenerated(DomainEvent):
    """Event published when a trading signal is generated."""
    signal: Signal
    gate_results: dict[str, bool]


@dataclass(slots=True, frozen=True)
class GateFailed(DomainEvent):
    """Event published when a signal gate fails."""
    gate_id: str
    gate_name: str
    reason: str


@dataclass(slots=True, frozen=True)
class CircuitBreakerTripped(DomainEvent):
    """Event published when a circuit breaker is tripped."""
    component: str
    reason: str
    threshold: float
    current_value: float


@dataclass(slots=True, frozen=True)
class RiskCheckPassed(DomainEvent):
    """Event published when a risk check passes."""
    check_name: str
    order: Order


@dataclass(slots=True, frozen=True)
class RiskCheckFailed(DomainEvent):
    """Event published when a risk check fails."""
    check_name: str
    order: Order
    reason: str


@dataclass(slots=True, frozen=True)
class SessionHalted(DomainEvent):
    """Event published when trading session is halted."""
    reason: str
    halted_by: str = "system"


class IEventBus(ABC):
    """Abstract interface for event bus publish/subscribe."""

    @abstractmethod
    def publish(self, event: DomainEvent) -> None:
        """Publish an event to all subscribers."""
        pass

    @abstractmethod
    def subscribe(self, event_type: type[DomainEvent], handler: callable) -> None:
        """Subscribe to events of a specific type."""
        pass

    @abstractmethod
    def unsubscribe(self, event_type: type[DomainEvent], handler: callable) -> None:
        """Unsubscribe from events of a specific type."""
        pass


class InMemoryEventBus(IEventBus):
    """Simple in-process event bus for single-machine deployment."""

    def __init__(self) -> None:
        self._subscribers: dict[type[DomainEvent], list[callable]] = {}

    def publish(self, event: DomainEvent) -> None:
        handlers = self._subscribers.get(type(event), [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as exc:
                logger.error("Event handler failed for %s: %s", type(event).__name__, exc)

    def subscribe(self, event_type: type[DomainEvent], handler: callable) -> None:
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: type[DomainEvent], handler: callable) -> None:
        if event_type in self._subscribers:
            self._subscribers[event_type] = [
                h for h in self._subscribers[event_type] if h != handler
            ]

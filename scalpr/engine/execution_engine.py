from __future__ import annotations

import dataclasses
from datetime import datetime, timezone
from typing import Any

from scalpr.domain.events import FillReceived, OrderPlaced, OrderUpdated
from scalpr.domain.fill import Fill
from scalpr.domain.order import Order, OrderState
from scalpr.engine.clock import Clock
from scalpr.engine.message_bus import MessageBus


class EventStore:
    def __init__(self) -> None:
        self._events: list[Any] = []

    def append(self, event: Any) -> None:
        self._events.append(event)

    def events(self, order_id: str) -> list[Any]:
        return [e for e in self._events if getattr(e, "order_id", None) == order_id]

    def all(self) -> list[Any]:
        return list(self._events)

    def clear(self) -> None:
        self._events.clear()


class Cache:
    def __init__(self) -> None:
        self._orders: dict[str, Order] = {}

    def order(self, order_id: str) -> Order | None:
        return self._orders.get(order_id)

    def open_orders(self) -> list[Order]:
        return [o for o in self._orders.values() if o.is_active()]

    def update(self, order: Order) -> None:
        self._orders[order.order_id] = order

    def all(self) -> list[Order]:
        return list(self._orders.values())

    def clear(self) -> None:
        self._orders.clear()


@dataclasses.dataclass(frozen=True)
class SubmitOrder:
    order: Order
    broker: str = "dhan"


@dataclasses.dataclass(frozen=True)
class CancelOrder:
    order_id: str
    broker: str = "dhan"


@dataclasses.dataclass(frozen=True)
class ModifyOrder:
    order_id: str
    updates: dict
    broker: str = "dhan"


@dataclasses.dataclass(frozen=True)
class OrderAccepted:
    order_id: str
    timestamp: datetime


@dataclasses.dataclass(frozen=True)
class OrderRejected:
    order_id: str
    reason: str
    timestamp: datetime


@dataclasses.dataclass(frozen=True)
class OrderCancelled:
    order_id: str
    timestamp: datetime


@dataclasses.dataclass(frozen=True)
class OrderFilled:
    order_id: str
    fill: Fill
    timestamp: datetime


class ExecutionEngine:
    def __init__(self, bus: MessageBus, clock: Clock) -> None:
        self._bus = bus
        self._clock = clock
        self._event_store = EventStore()
        self._cache = Cache()
        self._running = False

    @property
    def event_store(self) -> EventStore:
        return self._event_store

    @property
    def cache(self) -> Cache:
        return self._cache

    def start(self) -> None:
        self._bus.subscribe("exec.command.submit", self._on_submit)
        self._bus.subscribe("exec.command.cancel", self._on_cancel)
        self._bus.subscribe("exec.command.modify", self._on_modify)
        self._bus.subscribe("exec.event.accepted", self._on_accepted)
        self._bus.subscribe("exec.event.fill", self._on_fill)
        self._bus.subscribe("exec.event.rejected", self._on_rejected)
        self._bus.subscribe("exec.event.cancelled", self._on_cancelled)
        self._running = True

    def stop(self) -> None:
        self._running = False

    def _route(self, base_topic: str, broker: str, payload: Any) -> None:
        topic = f"{base_topic}.{broker}"
        self._bus.publish(topic, payload)

    def _on_submit(self, cmd: SubmitOrder) -> None:
        self._event_store.append(cmd)
        order = cmd.order

        existing = self._cache.order(order.order_id)
        if existing is not None:
            return

        self._cache.update(order)
        self._bus.publish(
            "domain.order.placed",
            OrderPlaced(order=order, timestamp=datetime.now(timezone.utc)),
        )

        self._route("exec.command.submit", cmd.broker, cmd)

    def _on_cancel(self, cmd: CancelOrder) -> None:
        self._event_store.append(cmd)
        order = self._cache.order(cmd.order_id)
        if order is None:
            return
        if order.state.is_terminal:
            return
        try:
            cancelled = order.transition_to(OrderState.CANCELLED)
            self._cache.update(cancelled)
            self._event_store.append(cmd)
            self._route("exec.command.cancel", cmd.broker, cmd)
        except ValueError:
            pass

    def _on_modify(self, cmd: ModifyOrder) -> None:
        self._event_store.append(cmd)
        order = self._cache.order(cmd.order_id)
        if order is None or order.state.is_terminal:
            return
        new_order = dataclasses.replace(order, **cmd.updates)
        self._cache.update(new_order)
        self._route("exec.command.modify", cmd.broker, cmd)

    def _on_accepted(self, order_id: str) -> None:
        order = self._cache.order(order_id)
        if order is None:
            return
        try:
            accepted = order.transition_to(OrderState.OPEN)
            self._cache.update(accepted)
            self._event_store.append(
                OrderAccepted(order_id=order_id, timestamp=self._clock.utc_now())
            )
        except ValueError:
            pass

    def _on_fill(self, fill: Fill) -> None:
        self._event_store.append(fill)
        order = self._cache.order(fill.order_id)
        if order is None:
            return

        order.remaining_quantity()
        new_filled = order.filled_quantity + fill.quantity
        is_complete = new_filled >= order.quantity

        target_state = OrderState.FILLED if is_complete else OrderState.PARTIALLY_FILLED
        new_qty = min(new_filled, order.quantity)

        try:
            new_order = order.transition_to(target_state)
        except ValueError:
            new_order = order

        new_order = dataclasses.replace(
            new_order,
            filled_quantity=new_qty,
            avg_price=fill.price,
        )
        self._cache.update(new_order)
        self._event_store.append(OrderFilled(order_id=fill.order_id, fill=fill, timestamp=self._clock.utc_now()))
        self._bus.publish(
            "domain.fill.received",
            FillReceived(fill=fill, timestamp=datetime.now(timezone.utc)),
        )
        if is_complete:
            self._bus.publish(
                "domain.order.updated",
                OrderUpdated(
                    order=new_order,
                    previous_state=order.state.value,
                    timestamp=datetime.now(timezone.utc),
                ),
            )

    def _on_rejected(self, payload: Any) -> None:
        order_id = payload.order_id if hasattr(payload, "order_id") else str(payload)
        reason = payload.reason if hasattr(payload, "reason") else ""
        order = self._cache.order(order_id)
        if order is None:
            return
        try:
            rejected = order.transition_to(OrderState.REJECTED)
            rejected = dataclasses.replace(rejected, reject_reason=reason)
            self._cache.update(rejected)
            self._event_store.append(
                OrderRejected(order_id=order_id, reason=reason, timestamp=self._clock.utc_now())
            )
        except ValueError:
            pass

    def _on_cancelled(self, payload: Any) -> None:
        order_id = payload.order_id if hasattr(payload, "order_id") else str(payload)
        order = self._cache.order(order_id)
        if order is None:
            return
        try:
            cancelled = order.transition_to(OrderState.CANCELLED)
            self._cache.update(cancelled)
        except ValueError:
            pass

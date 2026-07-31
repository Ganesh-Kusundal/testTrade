from __future__ import annotations

import dataclasses
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from scalpr.domain.events import FillReceived, OrderPlaced, OrderUpdated
from scalpr.domain.fill import Fill
from scalpr.domain.order import Order, OrderState
from scalpr.engine.clock import Clock
from scalpr.engine.message_bus import MessageBus

logger = logging.getLogger(__name__)


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
    broker_order_id: str = ""


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
class OrderCancelRejected:
    order_id: str
    reason: str
    timestamp: datetime


@dataclasses.dataclass(frozen=True)
class OrderModified:
    order_id: str
    updates: dict
    timestamp: datetime


@dataclasses.dataclass(frozen=True)
class OrderModifyRejected:
    order_id: str
    reason: str
    timestamp: datetime


@dataclasses.dataclass(frozen=True)
class OrderFilled:
    order_id: str
    fill: Fill
    timestamp: datetime


# Fields a broker modify may legitimately change. Anything else arriving in a
# ModifyOrder.updates dict is a bug or an attack — never let it reach the
# frozen domain object.
MODIFIABLE_FIELDS: frozenset[str] = frozenset(
    {"price", "quantity", "trigger_price", "validity"}
)


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
        # Broker-specific event topics
        self._bus.subscribe("exec.event.accepted.dhan", self._on_accepted)
        self._bus.subscribe("exec.event.filled.dhan", self._on_fill)
        self._bus.subscribe("exec.event.rejected.dhan", self._on_rejected)
        self._bus.subscribe("exec.event.cancelled.dhan", self._on_cancelled)
        self._bus.subscribe("exec.event.cancel_rejected.dhan", self._on_cancel_rejected)
        self._bus.subscribe("exec.event.modified.dhan", self._on_modified)
        self._bus.subscribe("exec.event.modify_rejected.dhan", self._on_modify_rejected)
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
        # Route the intent only. The order stays in its current state until the
        # broker confirms on exec.event.cancelled.<broker> — a local book that
        # claims CANCELLED while the broker holds a live order is a real-money
        # divergence.
        self._route("exec.command.cancel", cmd.broker, cmd)

    def _on_modify(self, cmd: ModifyOrder) -> None:
        self._event_store.append(cmd)
        order = self._cache.order(cmd.order_id)
        if order is None or order.state.is_terminal:
            return
        # Route the intent only; apply on exec.event.modified.<broker>.
        self._route("exec.command.modify", cmd.broker, cmd)

    def _on_accepted(self, payload: OrderAccepted) -> None:
        order_id = payload.order_id
        order = self._cache.order(order_id)
        if order is None:
            return
        try:
            accepted = order.transition_to(OrderState.OPEN)
            self._cache.update(accepted)
            self._event_store.append(payload)
        except ValueError:
            pass

    def _on_fill(self, payload: OrderFilled) -> None:
        fill = payload.fill
        self._event_store.append(payload)
        order = self._cache.order(fill.order_id)
        if order is None:
            return

        new_filled = order.filled_quantity + fill.quantity
        is_complete = new_filled >= order.quantity

        target_state = OrderState.FILLED if is_complete else OrderState.PARTIALLY_FILLED
        new_qty = min(new_filled, order.quantity)

        try:
            new_order = order.transition_to(target_state)
        except ValueError:
            new_order = order

        # Weighted average, not marginal last-fill price: avg_price drives
        # position cost basis and PnL, so replacing it with each new fill's
        # price corrupts the book of record on multi-fill orders. Divide by
        # the quantity actually stored (new_qty) so an over-fill is clamped
        # consistently with filled_quantity.
        if new_qty > 0 and new_filled > 0:
            total_cost = (order.avg_price * Decimal(order.filled_quantity)) + (
                fill.price * Decimal(fill.quantity)
            )
            avg_price = total_cost / Decimal(new_qty)
        else:
            avg_price = fill.price

        new_order = dataclasses.replace(
            new_order,
            filled_quantity=new_qty,
            avg_price=avg_price,
        )
        self._cache.update(new_order)
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

    def _on_rejected(self, payload: OrderRejected) -> None:
        order_id = payload.order_id
        reason = payload.reason
        order = self._cache.order(order_id)
        if order is None:
            return
        try:
            rejected = order.transition_to(OrderState.REJECTED)
            rejected = dataclasses.replace(rejected, reject_reason=reason)
            self._cache.update(rejected)
            self._event_store.append(payload)
        except ValueError:
            pass

    def _on_cancelled(self, payload: OrderCancelled) -> None:
        order_id = payload.order_id
        order = self._cache.order(order_id)
        if order is None:
            return
        try:
            cancelled = order.transition_to(OrderState.CANCELLED)
            self._cache.update(cancelled)
            self._event_store.append(payload)
        except ValueError:
            pass

    def _on_cancel_rejected(self, payload: OrderCancelRejected) -> None:
        # The order remains in whatever state it was; record the refusal so the
        # risk layer and any operator can see the cancel did not land.
        self._event_store.append(payload)
        logger.warning(
            "cancel_rejected: order_id=%s reason=%s", payload.order_id, payload.reason
        )

    def _on_modified(self, payload: OrderModified) -> None:
        order = self._cache.order(payload.order_id)
        if order is None:
            return
        applied = {
            key: value
            for key, value in payload.updates.items()
            if key in MODIFIABLE_FIELDS
        }
        rejected_keys = set(payload.updates) - MODIFIABLE_FIELDS
        if rejected_keys:
            logger.warning(
                "modify_fields_refused: order_id=%s fields=%s",
                payload.order_id,
                sorted(rejected_keys),
            )
        if not applied:
            self._event_store.append(payload)
            return
        try:
            updated = dataclasses.replace(order, **applied)
        except (TypeError, ValueError) as exc:
            logger.warning(
                "modify_apply_rejected: order_id=%s reason=%s",
                payload.order_id,
                exc,
            )
            self._event_store.append(payload)
            return
        self._cache.update(updated)
        self._event_store.append(payload)

    def _on_modify_rejected(self, payload: OrderModifyRejected) -> None:
        self._event_store.append(payload)
        logger.warning(
            "modify_rejected: order_id=%s reason=%s", payload.order_id, payload.reason
        )

from __future__ import annotations

import threading
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from scalpr.domain.fill import Fill
from scalpr.domain.order import Order, OrderSide, OrderState
from scalpr.domain.position import Position
from scalpr.domain.values import ZERO
from scalpr.engine.message_bus import MessageBus


class FakeExchange:
    def __init__(self, bus: MessageBus) -> None:
        self._bus = bus
        self._lock = threading.Lock()
        self._orders: dict[str, Order] = {}
        self._fills: dict[str, list[Fill]] = {}
        self._positions: dict[str, Position] = {}
        self._fill_counter = 0

        bus.subscribe("exec.command.submit.fake", self._on_submit)
        bus.subscribe("exec.command.cancel.fake", self._on_cancel)

    def _next_fill_id(self) -> str:
        self._fill_counter += 1
        return f"fake_fill_{self._fill_counter}"

    def _on_submit(self, cmd: Any) -> None:
        if hasattr(cmd, "order"):
            self.submit_order(cmd.order)

    def _on_cancel(self, cmd: Any) -> None:
        order_id = cmd.order_id if hasattr(cmd, "order_id") else str(cmd)
        self.cancel_order(order_id)

    def submit_order(self, order: Order) -> Fill:
        with self._lock:
            ts = datetime.now(timezone.utc)
            side = order.side
            price = order.price

            if order.order_type.value in ("MARKET", "STOP_LOSS_MARKET") and price == ZERO:
                price = Decimal("100.0")

            fill = Fill(
                fill_id=self._next_fill_id(),
                order_id=order.order_id,
                symbol=order.symbol,
                side=side,
                quantity=order.quantity,
                price=price,
                timestamp=ts,
            )

            try:
                filled_order = order.transition_to(OrderState.FILLED)
            except ValueError:
                filled_order = order
            filled_qty = order.filled_quantity + order.remaining_quantity()
            import dataclasses
            filled_order = dataclasses.replace(
                filled_order,
                state=OrderState.FILLED,
                filled_quantity=filled_qty,
                avg_price=price,
            )

            self._orders[order.order_id] = filled_order
            self._fills[order.order_id] = [*self._fills.get(order.order_id, []), fill]

            delta = order.quantity if side == OrderSide.BUY else -order.quantity
            pos = self._positions.get(order.symbol)
            if pos is None:
                pos = Position(
                    symbol=order.symbol,
                    exchange=order.exchange,
                )
            pos = pos.with_fill(delta, price, side)
            self._positions[order.symbol] = pos

        self._bus.publish("exec.event.accepted", order.order_id)
        self._bus.publish("exec.event.fill", fill)

        return fill

    def get_position(self, symbol: str) -> Position | None:
        with self._lock:
            return self._positions.get(symbol)

    def get_open_orders(self) -> list[Order]:
        with self._lock:
            return [o for o in self._orders.values() if o.is_active()]

    def cancel_order(self, order_id: str) -> bool:
        with self._lock:
            order = self._orders.get(order_id)
            if order is None or order.state.is_terminal:
                return False
            try:
                cancelled = order.transition_to(OrderState.CANCELLED)
                self._orders[order_id] = cancelled
                self._bus.publish("exec.event.cancelled", cancelled)
                return True
            except ValueError:
                return False

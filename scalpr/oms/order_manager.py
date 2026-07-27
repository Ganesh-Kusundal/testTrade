from __future__ import annotations

import logging
import threading
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal

from scalpr.domain.fill import Fill
from scalpr.domain.order import Order, OrderState
from scalpr.oms.persistence import OmsRepository

logger = logging.getLogger(__name__)


class OrderManager:
    """Manages order lifecycles, FSM state changes, fill accumulation, and audit trails."""

    def __init__(self, repository: OmsRepository | None = None) -> None:
        self.orders: dict[str, Order] = {}
        self.fills: dict[str, list[Fill]] = {}
        self.event_log: list[str] = []
        self._lock = threading.RLock()
        self._repository = repository

    def add_order(self, order: Order) -> None:
        """Register a new order. Deduplicates by order_id."""
        with self._lock:
            if order.order_id in self.orders:
                raise ValueError(f"Duplicate order ID: {order.order_id}")
            self.orders[order.order_id] = order
            self._log_event(order.order_id, f"Created order as {order.state.value}")
            
            # Persist to database if repository available
            if self._repository:
                try:
                    self._repository.save_order(order)
                except Exception as e:
                    logger.error(f"Failed to persist order {order.order_id}: {e}")

    def update_order_state(self, order_id: str, new_state: OrderState) -> Order:
        """Atomically transition order state and record event."""
        with self._lock:
            order = self.orders.get(order_id)
            if not order:
                raise ValueError(f"Order not found: {order_id}")
            updated = order.transition_to(new_state)
            self.orders[order_id] = updated
            self._log_event(order_id, f"State changed from {order.state.value} to {new_state.value}")
            
            # Persist updated order state
            if self._repository:
                try:
                    self._repository.save_order(updated)
                except Exception as e:
                    logger.error(f"Failed to persist order state update {order_id}: {e}")
            
            return updated

    def process_fill(self, fill: Fill) -> Order:
        """Process execution fill, update average price, and accumulate filled quantity."""
        with self._lock:
            order_id = fill.order_id
            order = self.orders.get(order_id)
            if not order:
                raise ValueError(f"Order not found for fill: {order_id}")

            if order_id not in self.fills:
                self.fills[order_id] = []
            self.fills[order_id].append(fill)

            total_filled = sum(f.quantity for f in self.fills[order_id])
            if total_filled <= 0:
                raise ValueError("Accumulated fill quantity must be positive")

            total_cost = sum(f.price * Decimal(f.quantity) for f in self.fills[order_id])
            avg_price = total_cost / Decimal(total_filled)

            if total_filled >= order.quantity:
                new_state = OrderState.FILLED
            else:
                new_state = OrderState.PARTIALLY_FILLED

            # Transition and update order representation
            updated = replace(
                order,
                filled_quantity=total_filled,
                avg_price=avg_price,
            )

            # Avoid self-transition issues if state doesn't actually change
            if updated.state != new_state:
                updated = updated.transition_to(new_state)

            self.orders[order_id] = updated
            self._log_event(
                order_id,
                f"Fill processed: {fill.quantity} @ {fill.price}. Total filled: {total_filled}/{order.quantity}. State: {new_state.value}",
            )
            
            # Persist fill and updated order to database
            if self._repository:
                try:
                    self._repository.save_fill(fill)
                    self._repository.save_order(updated)
                except Exception as e:
                    logger.error(f"Failed to persist fill {fill.fill_id}: {e}")
            
            return updated

    def get_order(self, order_id: str) -> Order | None:
        with self._lock:
            return self.orders.get(order_id)

    def _log_event(self, order_id: str, message: str) -> None:
        ts = datetime.now(timezone.utc).isoformat()
        self.event_log.append(f"[{ts}] Order {order_id}: {message}")
    
    def restore_state(self) -> None:
        """Restore orders and fills from persistence (crash recovery)."""
        if not self._repository:
            return
        
        try:
            restored_orders = self._repository.restore_orders()
            
            with self._lock:
                self.orders.clear()
                self.orders.update(restored_orders)
                
            logger.info(f"OMS state restored: {len(restored_orders)} orders recovered")
        except Exception as e:
            logger.warning(f"Failed to restore OMS state: {e}")
    
    def get_orders(self) -> list[Order]:
        """Get all orders as a list."""
        with self._lock:
            return list(self.orders.values())

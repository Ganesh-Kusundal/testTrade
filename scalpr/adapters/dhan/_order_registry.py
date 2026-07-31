"""Local order id <-> Dhan orderId identity map.

The strategy layer knows an order by its local `Order.order_id`. Dhan knows
it by the `orderId` it returns from POST /orders. Every subsequent broker
call — cancel, modify, status — must address the broker's id, and every
inbound broker event must be translated back. Without this map the adapter
sends local UUIDs to the broker and cancels silently no-op.

In-memory only. On restart the map is rebuilt by OrderWatcher from the order
book, matching on `correlationId` (the local order id is sent as
correlationId — see _mapper_orders.order_to_dhan_request_v2).
"""

from __future__ import annotations

import threading


class OrderRegistry:
    """Thread-safe bidirectional map between local order ids and broker ids."""

    def __init__(self) -> None:
        self._to_broker: dict[str, str] = {}
        self._to_local: dict[str, str] = {}
        self._lock = threading.Lock()

    def register(self, local_id: str, broker_id: str) -> None:
        """Map a local order id to a broker order id, replacing any prior pair."""
        if not broker_id:
            raise ValueError("broker_id must be non-empty")
        if not local_id:
            raise ValueError("local_id must be non-empty")
        with self._lock:
            previous = self._to_broker.get(local_id)
            if previous is not None:
                self._to_local.pop(previous, None)
            self._to_broker[local_id] = broker_id
            self._to_local[broker_id] = local_id

    def broker_id(self, local_id: str) -> str | None:
        with self._lock:
            return self._to_broker.get(local_id)

    def local_id(self, broker_id: str) -> str | None:
        with self._lock:
            return self._to_local.get(broker_id)

    def forget(self, local_id: str) -> None:
        with self._lock:
            broker_id = self._to_broker.pop(local_id, None)
            if broker_id is not None:
                self._to_local.pop(broker_id, None)

    def all_broker_ids(self) -> list[str]:
        with self._lock:
            return list(self._to_local.keys())

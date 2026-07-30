from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Callable

from scalpr.adapters.dhan.client import DhanClient
from scalpr.domain.tick import TickerEvent, QuoteEvent, FullEvent
from scalpr.gateway.subscription import Subscription
from scalpr.domain.instrument import MarketFeed

logger = logging.getLogger(__name__)


class OrderUpdate:
    """Normalized order update event from the broker's order-update WebSocket."""

    def __init__(
        self,
        order_id: str,
        status: str,
        instrument: Any = None,
        filled_quantity: int = 0,
        remaining_quantity: int = 0,
        average_price: Decimal | None = None,
        timestamp: datetime | None = None,
        rejection_reason: str | None = None,
    ) -> None:
        self.order_id = order_id
        self.status = status
        self.instrument = instrument
        self.filled_quantity = filled_quantity
        self.remaining_quantity = remaining_quantity
        self.average_price = average_price
        self.timestamp = timestamp
        self.rejection_reason = rejection_reason


class OrderUpdateService:
    """Manages the order-update WebSocket connection and normalizes events.

    The adapter must normalize Dhan order updates into OrderUpdate domain events.
    """

    def __init__(self, client: DhanClient, bus: Any = None) -> None:
        self._client = client
        self._bus = bus
        self._subscribers: list[Callable[[OrderUpdate], None]] = []
        self._connected = False

    def connect(self) -> None:
        """Connect to the order-update WebSocket."""
        if hasattr(self._client, "connect_order_updates"):
            self._client.connect_order_updates()
        self._connected = True

    def disconnect(self) -> None:
        """Disconnect the order-update WebSocket."""
        if hasattr(self._client, "disconnect_order_updates"):
            self._client.disconnect_order_updates()
        self._connected = False

    def subscribe(self, on_update: Callable[[OrderUpdate], None]) -> Subscription:
        """Subscribe to order update events."""
        self._subscribers.append(on_update)
        return Subscription(
            id=f"ou-{id(on_update)}",
            instruments=["*"],
            mode=MarketFeed.FULL,
        )

    def unsubscribe(self, subscription: Subscription) -> None:
        """Unsubscribe from order update events."""
        subscription.deactivate()

    def _on_order_update(self, raw: dict[str, Any]) -> None:
        """Normalize a raw Dhan order update dict into an OrderUpdate event."""
        from decimal import Decimal
        update = OrderUpdate(
            order_id=raw.get("orderId", ""),
            status=raw.get("status", ""),
            filled_quantity=int(raw.get("filledQty", 0)),
            remaining_quantity=int(raw.get("remainingQty", 0)),
            average_price=Decimal(str(raw.get("avgPrice", 0))),
            timestamp=raw.get("timestamp"),
            rejection_reason=raw.get("reason") or raw.get("rejectReason"),
        )
        for callback in self._subscribers:
            callback(update)
        if self._bus is not None:
            self._bus.publish("exec.event.order_update.dhan", update)

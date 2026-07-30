from __future__ import annotations

from unittest.mock import MagicMock

from scalpr.adapters.dhan.client import DhanClient
from scalpr.gateway.order_update_service import OrderUpdateService, OrderUpdate
from scalpr.gateway.subscription import Subscription


class TestOrderUpdateService:
    def test_connect_calls_client(self):
        client = MagicMock(spec=DhanClient)
        svc = OrderUpdateService(client)
        svc.connect()
        client.connect_order_updates.assert_called_once()
        assert svc._connected is True

    def test_disconnect_calls_client(self):
        client = MagicMock(spec=DhanClient)
        svc = OrderUpdateService(client)
        svc.connect()
        svc.disconnect()
        client.disconnect_order_updates.assert_called_once()
        assert svc._connected is False

    def test_subscribe_returns_subscription(self):
        client = MagicMock(spec=DhanClient)
        svc = OrderUpdateService(client)
        sub = svc.subscribe(on_update=lambda e: None)
        assert isinstance(sub, Subscription)
        assert sub.is_active is True

    def test_on_order_update_normalizes(self):
        client = MagicMock(spec=DhanClient)
        received = []
        svc = OrderUpdateService(client)
        svc.subscribe(on_update=lambda e: received.append(e))

        svc._on_order_update({
            "orderId": "ord-1",
            "status": "FILLED",
            "filledQty": 10,
            "remainingQty": 0,
            "avgPrice": "2500.5",
            "timestamp": None,
            "reason": None,
        })

        assert len(received) == 1
        update = received[0]
        assert isinstance(update, OrderUpdate)
        assert update.order_id == "ord-1"
        assert update.status == "FILLED"
        assert update.filled_quantity == 10
        assert update.remaining_quantity == 0
        assert update.average_price is not None

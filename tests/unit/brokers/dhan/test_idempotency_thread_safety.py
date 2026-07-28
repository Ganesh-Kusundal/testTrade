"""Thread safety tests for OrdersAdapter idempotency cache."""
import contextlib
import threading
from decimal import Decimal
from unittest.mock import MagicMock

from scalpr.brokers.dhan.orders import OrdersAdapter
from scalpr.domain.instrument import Exchange
from scalpr.domain.order import Order, OrderSide, OrderState, OrderType


def _make_order(order_id: str) -> Order:
    return Order(
        order_id=order_id, symbol="RELIANCE", exchange=Exchange.NSE,
        side=OrderSide.BUY, order_type=OrderType.LIMIT,
        quantity=10, price=Decimal("2500"), state=OrderState.PENDING,
    )


def test_concurrent_place_order_should_not_duplicate_idempotency_check():
    """Concurrent threads placing same correlation_id must not create duplicates.

    Exactly one thread should succeed (place the order). All others should
    receive an OrderError with 'Duplicate' in the message.
    """
    mock_client = MagicMock()
    mock_client.client_id = "test"
    mock_client.post.return_value = {
        "orderId": "ord_1", "orderStatus": "FILLED",
        "tradedQuantity": 10, "tradedPrice": 2500.0,
    }
    mock_resolver = MagicMock()
    mock_inst = MagicMock()
    mock_inst.security_id = "12345"
    mock_resolver.resolve.return_value = mock_inst

    adapter = OrdersAdapter(mock_client, mock_resolver)
    order = _make_order("ord_1")

    results = {"success": 0, "duplicate": 0, "error": 0}
    lock = threading.Lock()
    barrier = threading.Barrier(10)  # synchronise thread starts

    def place():
        # All threads start at the same instant to maximise race window
        with contextlib.suppress(threading.BrokenBarrierError):
            barrier.wait(timeout=5)
        try:
            adapter.place_order(order)
            with lock:
                results["success"] += 1
        except Exception as e:
            with lock:
                if "Duplicate" in str(e):
                    results["duplicate"] += 1
                else:
                    results["error"] += 1

    threads = [threading.Thread(target=place) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Exactly one should succeed, rest should be duplicates
    assert results["success"] == 1, f"Expected exactly 1 success: {results}"
    assert results["duplicate"] == 9, f"Expected 9 duplicates: {results}"
    assert results["error"] == 0, f"Unexpected errors: {results}"

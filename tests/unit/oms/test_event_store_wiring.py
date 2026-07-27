"""EventStore wiring: OrderManager must persist domain events for audit/replay.

Closes the last deferred item — EventStore round-trips correctly but was
dead code in production: no events were appended during live trading.
"""
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock

from scalpr.domain.fill import Fill
from scalpr.domain.instrument import Exchange
from scalpr.domain.order import Order, OrderSide, OrderState, OrderType
from scalpr.observability.event_store import EventStore
from scalpr.oms.order_manager import OrderManager


def _order(order_id: str = "O1") -> Order:
    return Order(
        order_id=order_id,
        symbol="RELIANCE",
        exchange=Exchange.NSE,
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=10,
        price=Decimal("2500.50"),
        state=OrderState.PENDING,
    )


def _fill(order_id: str = "O1") -> Fill:
    return Fill(
        fill_id="F1",
        order_id=order_id,
        symbol="RELIANCE",
        side=OrderSide.BUY,
        quantity=10,
        price=Decimal("2500.50"),
        timestamp=datetime(2026, 7, 27, 10, 0, 0, tzinfo=timezone.utc),
    )


class TestOrderManagerEmitsEvents:
    def _manager(self, tmp_path):
        store = EventStore(db_path=str(tmp_path / "events.db"))
        return OrderManager(event_store=store, session_id="test-session"), store

    def test_add_order_appends_order_placed(self, tmp_path):
        manager, store = self._manager(tmp_path)
        manager.add_order(_order())

        events = store.get_session_events("test-session")
        assert len(events) == 1
        _, event = events[0]
        assert event.__class__.__name__ == "OrderPlaced"
        assert event.order.order_id == "O1"

    def test_state_change_appends_order_updated_with_previous_state(self, tmp_path):
        manager, store = self._manager(tmp_path)
        manager.add_order(_order())
        manager.update_order_state("O1", OrderState.OPEN)

        events = store.get_session_events("test-session", event_type="OrderUpdated")
        assert len(events) == 1
        _, event = events[0]
        assert event.previous_state == "PENDING"
        assert event.order.state == OrderState.OPEN

    def test_process_fill_appends_fill_received(self, tmp_path):
        manager, store = self._manager(tmp_path)
        manager.add_order(_order())
        manager.process_fill(_fill())

        events = store.get_session_events("test-session", event_type="FillReceived")
        assert len(events) == 1
        _, event = events[0]
        assert isinstance(event.fill, Fill)
        assert event.fill.fill_id == "F1"

    def test_event_store_failure_never_breaks_order_flow(self):
        """Observability must not take down trading — same policy as repository."""
        broken = MagicMock(spec=EventStore)
        broken.append.side_effect = RuntimeError("disk full")
        manager = OrderManager(event_store=broken, session_id="s")

        manager.add_order(_order())
        updated = manager.process_fill(_fill())

        assert updated.state == OrderState.FILLED  # flow unharmed
        assert broken.append.call_count == 2  # it did try

    def test_no_event_store_is_still_fine(self):
        manager = OrderManager()
        manager.add_order(_order())
        assert manager.get_order("O1") is not None


class TestBootstrapWiresEventStore:
    def test_wire_injects_event_store_into_order_manager(self, tmp_path):
        from unittest.mock import create_autospec

        from scalpr.api.bootstrap import wire
        from scalpr.brokers.gateway import IBrokerGateway

        gw = create_autospec(IBrokerGateway, instance=True)
        ctx = wire(
            gw,
            ["RELIANCE"],
            db_path=str(tmp_path / "oms.db"),
            events_db_path=str(tmp_path / "events.db"),
        )

        manager = ctx.order_router.order_manager
        assert manager._event_store is not None, "EventStore not wired — dead code again"

        # And it actually records: a session id was assigned
        assert manager._session_id

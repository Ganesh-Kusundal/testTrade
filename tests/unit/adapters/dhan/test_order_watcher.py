"""OrderWatcher — turns the Dhan order book into lifecycle events.

Without this, nothing in production ever publishes exec.event.filled.dhan.
"""

from decimal import Decimal
from unittest.mock import MagicMock

from scalpr.adapters.dhan._order_registry import OrderRegistry
from scalpr.adapters.dhan._order_watcher import OrderWatcher
from scalpr.engine.clock import StaticClock
from scalpr.engine.message_bus import RecordingBus


def _watcher(book):
    http = MagicMock()
    http.get.return_value = book
    bus = RecordingBus()
    registry = OrderRegistry()
    registry.register("local-1", "ORD1")
    return OrderWatcher(http, bus, StaticClock(), registry), bus, http


def _entry(status, filled_qty, traded_price, order_id="ORD1", correlation=None):
    entry = {
        "orderId": order_id,
        "orderStatus": status,
        "filledQty": filled_qty,
        "averageTradedPrice": traded_price,
        "quantity": 10,
    }
    if correlation is not None:
        entry["correlationId"] = correlation
    return entry


class TestOrderWatcherFills:
    def test_partial_fill_publishes_the_new_quantity_only(self):
        """A book showing 4 filled after 0 is a 4-lot fill, not a 4-lot total."""
        watcher, bus, _ = _watcher([_entry("PART_TRADED", 4, 2500.50)])

        watcher.poll_once()

        fills = bus.filter("exec.event.filled.dhan")
        assert len(fills) == 1
        fill = fills[0].payload.fill
        assert fill.order_id == "local-1"
        assert fill.quantity == 4
        assert fill.price == Decimal("2500.50")
        assert isinstance(fill.price, Decimal)

    def test_second_poll_publishes_only_the_delta(self):
        """Polling is idempotent on unchanged rows and emits deltas on changed
        rows — re-emitting the cumulative total would double-count the position."""
        watcher, bus, http = _watcher([_entry("PART_TRADED", 4, 2500.50)])
        watcher.poll_once()
        http.get.return_value = [_entry("TRADED", 10, 2501.00)]

        watcher.poll_once()

        fills = bus.filter("exec.event.filled.dhan")
        assert len(fills) == 2
        assert fills[1].payload.fill.quantity == 6

    def test_unchanged_book_publishes_nothing_further(self):
        watcher, bus, _ = _watcher([_entry("PART_TRADED", 4, 2500.50)])
        watcher.poll_once()

        watcher.poll_once()

        assert len(bus.filter("exec.event.filled.dhan")) == 1

    def test_zero_filled_quantity_publishes_no_fill(self):
        """An accepted-but-unfilled order is not a fill. Publishing a
        zero-quantity fill would corrupt avg_price to zero."""
        watcher, bus, _ = _watcher([_entry("TRANSIT", 0, None)])

        watcher.poll_once()

        assert len(bus.filter("exec.event.filled.dhan")) == 0


class TestOrderWatcherTerminalStates:
    def test_broker_rejection_publishes_rejected(self):
        watcher, bus, _ = _watcher([_entry("REJECTED", 0, None)])

        watcher.poll_once()

        rejected = bus.filter("exec.event.rejected.dhan")
        assert len(rejected) == 1
        assert rejected[0].payload.order_id == "local-1"

    def test_broker_cancellation_publishes_cancelled(self):
        watcher, bus, _ = _watcher([_entry("CANCELLED", 0, None)])

        watcher.poll_once()

        cancelled = bus.filter("exec.event.cancelled.dhan")
        assert len(cancelled) == 1
        assert cancelled[0].payload.order_id == "local-1"

    def test_terminal_state_is_published_once(self):
        watcher, bus, _ = _watcher([_entry("CANCELLED", 0, None)])
        watcher.poll_once()

        watcher.poll_once()

        assert len(bus.filter("exec.event.cancelled.dhan")) == 1

    def test_terminal_order_is_pruned_from_tracking(self):
        """Terminal orders must stop accumulating state, or a long-running
        session leaks memory and re-scans the same rows forever."""
        watcher, bus, _ = _watcher([_entry("TRADED", 10, 2500.00)])
        watcher.poll_once()

        watcher.poll_once()

        assert len(bus.filter("exec.event.filled.dhan")) == 1
        assert watcher._seen_filled == {}
        assert watcher._terminal == {"ORD1"}


class TestOrderWatcherRobustness:
    def test_unmapped_broker_order_is_ignored(self):
        """Orders placed outside this process (manual, or a previous run)
        must not be invented into the local book."""
        watcher, bus, _ = _watcher([_entry("TRADED", 10, 2500.00, order_id="FOREIGN")])

        watcher.poll_once()

        assert len(bus.filter("exec.event.filled.dhan")) == 0

    def test_correlation_id_adopts_lost_submit_or_restart(self):
        """When the local order id was sent as correlationId but the submit
        response was lost (or the process restarted), the watcher must
        re-attribute the broker order to the local id and report fills."""
        watcher, bus, _ = _watcher(
            [_entry("PART_TRADED", 4, 2500.50, order_id="ORD9", correlation="local-9")]
        )

        watcher.poll_once()

        fills = bus.filter("exec.event.filled.dhan")
        assert len(fills) == 1
        assert fills[0].payload.order_id == "local-9"
        assert watcher._registry.local_id("ORD9") == "local-9"

    def test_http_failure_does_not_raise(self):
        """The watcher runs on a heartbeat; one failed poll must not kill it."""
        watcher, bus, http = _watcher([])
        http.get.side_effect = RuntimeError("rate limited")

        watcher.poll_once()

        assert bus.recorded_events == []

    def test_unknown_status_is_skipped_not_fatal(self):
        watcher, bus, _ = _watcher([_entry("SOMETHING_NEW", 0, None)])

        watcher.poll_once()

        assert bus.recorded_events == []

    def test_dict_wrapped_book_is_unwrapped(self):
        """Defensive: some gateways wrap the order-book list under a key."""
        watcher, bus, _ = _watcher({"data": [_entry("TRADED", 10, 2500.00)]})

        watcher.poll_once()

        fills = bus.filter("exec.event.filled.dhan")
        assert len(fills) == 1

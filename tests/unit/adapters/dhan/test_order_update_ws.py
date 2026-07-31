"""Tests for OrderUpdateFeed wrapper and DhanClient._on_order_update_push."""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch

import pytest

from scalpr.adapters.dhan._order_update_ws import OrderUpdateFeed


class TestOrderUpdateFeedNormalise:
    """Unit tests for the normalise static method."""

    def test_normalise_maps_sdk_fields_to_wire_shape(self):
        data = {
            "orderNo": "ORD123",
            "status": "TRADED",
            "filledQty": 10,
            "remainingQty": 0,
            "avgPrice": 2500.5,
            "orderTimestamp": "2026-07-31T10:00:00",
            "rejectReason": None,
            "tradingSymbol": "RELIANCE",
            "transactionType": "BUY",
            "orderType": "LIMIT",
            "productType": "INTRADAY",
            "quantity": 10,
            "price": 2500.0,
            "triggerPrice": 0,
            "correlationId": "local-1",
        }
        wire = OrderUpdateFeed._normalise(data)
        assert wire["orderId"] == "ORD123"
        assert wire["orderStatus"] == "TRADED"
        assert wire["filledQty"] == 10
        assert wire["remainingQty"] == 0
        assert wire["avgPrice"] == 2500.5
        assert wire["tradingSymbol"] == "RELIANCE"
        assert wire["transactionType"] == "BUY"
        assert wire["correlationId"] == "local-1"

    def test_normalise_handles_empty_data(self):
        wire = OrderUpdateFeed._normalise({})
        assert wire["orderId"] == ""
        assert wire["orderStatus"] == ""
        assert wire["filledQty"] == 0

    def test_normalise_handles_none_fields(self):
        data = {"orderNo": "ORD1", "status": None}
        wire = OrderUpdateFeed._normalise(data)
        assert wire["orderId"] == "ORD1"
        assert wire["orderStatus"] == "None"


class TestOrderUpdateFeedLifecycle:
    """Tests for connect/disconnect lifecycle."""

    def test_connect_starts_daemon_thread(self):
        feed = OrderUpdateFeed(client_id="c1", access_token="t1")
        stop_event = threading.Event()

        def fake_run():
            stop_event.wait(timeout=2)

        with patch.object(feed, "_run", side_effect=fake_run):
            feed.connect()
            assert feed.connected
            stop_event.set()
            feed.disconnect()
            assert not feed.connected

    def test_disconnect_stops_thread(self):
        feed = OrderUpdateFeed(client_id="c1", access_token="t1")
        stop_event = threading.Event()

        def fake_run():
            stop_event.wait(timeout=2)

        with patch.object(feed, "_run", side_effect=fake_run):
            feed.connect()
            assert feed.connected
            stop_event.set()
            feed.disconnect()
            assert not feed.connected

    def test_connect_is_idempotent(self):
        feed = OrderUpdateFeed(client_id="c1", access_token="t1")
        stop_event = threading.Event()

        def fake_run():
            stop_event.wait(timeout=2)

        with patch.object(feed, "_run", side_effect=fake_run):
            feed.connect()
            t1 = feed._thread
            feed.connect()  # second call should not create a new thread
            assert feed._thread is t1
            stop_event.set()
            feed.disconnect()

    def test_connected_property_false_when_not_started(self):
        feed = OrderUpdateFeed(client_id="c1", access_token="t1")
        assert not feed.connected


class TestOrderUpdateFeedHandleUpdate:
    """Tests for the async handle_update callback."""

    @pytest.mark.asyncio
    async def test_handle_update_dispatches_order_alert(self):
        calls = []
        feed = OrderUpdateFeed(
            client_id="c1", access_token="t1", on_update=lambda w: calls.append(w)
        )
        raw = {
            "Type": "order_alert",
            "Data": {
                "orderNo": "ORD1",
                "status": "TRADED",
                "filledQty": 5,
            },
        }
        await feed._handle_update(raw)
        assert len(calls) == 1
        assert calls[0]["orderId"] == "ORD1"
        assert calls[0]["orderStatus"] == "TRADED"

    @pytest.mark.asyncio
    async def test_handle_update_ignores_non_alert_types(self):
        calls = []
        feed = OrderUpdateFeed(
            client_id="c1", access_token="t1", on_update=lambda w: calls.append(w)
        )
        await feed._handle_update({"Type": "something_else", "Data": {}})
        assert len(calls) == 0

    @pytest.mark.asyncio
    async def test_handle_update_ignores_empty_data(self):
        calls = []
        feed = OrderUpdateFeed(
            client_id="c1", access_token="t1", on_update=lambda w: calls.append(w)
        )
        await feed._handle_update({"Type": "order_alert", "Data": {}})
        assert len(calls) == 0

    @pytest.mark.asyncio
    async def test_handle_update_no_callback_is_safe(self):
        feed = OrderUpdateFeed(client_id="c1", access_token="t1", on_update=None)
        raw = {"Type": "order_alert", "Data": {"orderNo": "X", "status": "TRADED"}}
        await feed._handle_update(raw)  # should not raise


class TestDhanClientOnOrderUpdatePush:
    """Tests for DhanClient._on_order_update_push handler."""

    def _make_client(self):
        """Build a DhanClient with mocked collaborators."""
        from scalpr.engine.clock import StaticClock
        from scalpr.engine.message_bus import RecordingBus

        bus = RecordingBus()
        clock = StaticClock(datetime(2026, 7, 31, 10, 0, tzinfo=timezone.utc))
        config = {
            "client_id": "test_client",
            "access_token": "test_token",
            "totp_secret": "test_secret",  # pragma: allowlist secret
        }
        with patch("scalpr.adapters.dhan.client.TokenManager"), \
             patch("scalpr.adapters.dhan.client.DhanHttpClient") as MockHTTP, \
             patch("scalpr.adapters.dhan.client.DhanWebSocket"), \
             patch("scalpr.adapters.dhan.client.InstrumentLoader"), \
             patch("scalpr.adapters.dhan.client.HistoricalDataAdapter"), \
             patch("scalpr.adapters.dhan.client.OptionChainAdapter"), \
             patch("scalpr.adapters.dhan.client.GreeksCalculator"), \
             patch("scalpr.adapters.dhan.client.PortfolioAdapter"):
            mock_http = MockHTTP.return_value
            mock_http.access_token = "test_token"
            from scalpr.adapters.dhan.client import DhanClient
            client = DhanClient(bus, clock, config)
        return client, bus, clock

    def test_filled_publishes_order_filled_event(self):
        client, bus, _clock = self._make_client()
        client._registry.register("local-1", "ORD123")
        wire = {
            "orderId": "ORD123",
            "orderStatus": "TRADED",
            "filledQty": 10,
            "avgPrice": 2500.0,
            "tradingSymbol": "RELIANCE",
            "transactionType": "BUY",
        }
        client._on_order_update_push(wire)
        fills = bus.filter("exec.event.filled.dhan")
        assert len(fills) == 1
        ev = fills[0].payload
        assert ev.order_id == "local-1"
        assert ev.fill.quantity == 10
        assert ev.fill.price == Decimal("2500.0")
        assert ev.fill.symbol == "RELIANCE"

    def test_rejected_publishes_order_rejected_event(self):
        client, bus, _clock = self._make_client()
        client._registry.register("local-1", "ORD456")
        wire = {
            "orderId": "ORD456",
            "orderStatus": "REJECTED",
            "rejectReason": "Insufficient funds",
        }
        client._on_order_update_push(wire)
        rejections = bus.filter("exec.event.rejected.dhan")
        assert len(rejections) == 1
        assert rejections[0].payload.order_id == "local-1"
        assert rejections[0].payload.reason == "Insufficient funds"

    def test_cancelled_publishes_order_cancelled_event(self):
        client, bus, _clock = self._make_client()
        client._registry.register("local-1", "ORD789")
        wire = {"orderId": "ORD789", "orderStatus": "CANCELLED"}
        client._on_order_update_push(wire)
        cancelled = bus.filter("exec.event.cancelled.dhan")
        assert len(cancelled) == 1
        assert cancelled[0].payload.order_id == "local-1"

    def test_empty_order_id_is_ignored(self):
        client, bus, _clock = self._make_client()
        client._on_order_update_push({"orderId": "", "orderStatus": "TRADED"})
        assert len(bus.filter("exec.event.filled.dhan")) == 0

    def test_unmapped_broker_id_uses_broker_id_as_order_id(self):
        client, bus, _clock = self._make_client()
        wire = {
            "orderId": "UNKNOWN_BROKER_ID",
            "orderStatus": "TRADED",
            "filledQty": 5,
            "avgPrice": 100.0,
            "tradingSymbol": "TEST",
            "transactionType": "BUY",
        }
        client._on_order_update_push(wire)
        fills = bus.filter("exec.event.filled.dhan")
        assert len(fills) == 1
        assert fills[0].payload.order_id == "UNKNOWN_BROKER_ID"

    def test_open_status_produces_no_bus_event(self):
        """PENDING/OPEN statuses are informational — OrderWatcher handles them."""
        client, bus, _clock = self._make_client()
        client._registry.register("local-1", "ORD999")
        wire = {"orderId": "ORD999", "orderStatus": "PENDING"}
        client._on_order_update_push(wire)
        assert len(bus.filter("exec.event.filled.dhan")) == 0
        assert len(bus.filter("exec.event.rejected.dhan")) == 0
        assert len(bus.filter("exec.event.cancelled.dhan")) == 0

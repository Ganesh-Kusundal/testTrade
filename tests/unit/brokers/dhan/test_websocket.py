"""Unit tests for Dhan WebSocket components (SDK-based).

Tests cover:
- DhanWebSocketManager: subscriber management, tick distribution, lifecycle,
  health monitoring, error isolation (20+ tests)
- DhanWebSocketClient: SDK-based connection, subscription, security_id resolution
  (10+ tests)

Total: 30+ test methods.
"""

import logging
import time
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from scalpr.brokers.dhan.ws_client import DhanWebSocketClient
from scalpr.brokers.dhan.ws_manager import (
    ConnectionStatus,
    DhanWebSocketManager,
)
from scalpr.domain.tick import Tick

# ═══════════════════════════════════════════════════════════════════════════════
# DhanWebSocketManager Tests
# ═══════════════════════════════════════════════════════════════════════════════

def _make_manager(**kwargs):
    """Helper to create a manager with mocked dependencies."""
    mgr = DhanWebSocketManager(access_token="t", client_id="c", **kwargs)
    mock_client = MagicMock()
    mock_client.connect = AsyncMock(return_value=True)
    mock_client.disconnect = AsyncMock(return_value=True)
    mock_client.subscribe = AsyncMock(return_value=True)
    mock_client.unsubscribe = AsyncMock(return_value=True)
    mock_client.on_tick = MagicMock()
    mgr._ws_client = mock_client
    mgr._ws_parser = MagicMock()
    return mgr


def _make_tick(**kw):
    base = {"symbol": "X", "ltp": Decimal("100"), "bid": Decimal("0"), "ask": Decimal("0"),
            "delta_volume": 0, "cumulative_volume": 0, "exchange_timestamp": datetime.now(timezone.utc)}
    base.update(kw)
    return Tick(**base)


class TestManagerSubscriberManagement:
    """Tests for add/remove subscriber and tick distribution."""

    def test_add_subscriber_sync(self):
        mgr = _make_manager()
        def cb(t):
            return None
        mgr.add_subscriber(cb)
        assert cb in mgr._subscribers or len(mgr._subscribers) >= 1

    def test_remove_subscriber_sync(self):
        mgr = _make_manager()
        def cb(t):
            return None
        mgr._subscribers.append(cb)
        mgr.remove_subscriber(cb)
        assert cb not in mgr._subscribers

    def test_distribute_to_multiple(self):
        mgr = _make_manager()
        received = [[], []]
        mgr._subscribers = [lambda t: received[0].append(t), lambda t: received[1].append(t)]
        tick = _make_tick()
        mgr._distribute_tick_sync(tick)
        assert received[0] == [tick] and received[1] == [tick]

    def test_distribute_no_subscribers(self):
        mgr = _make_manager()
        mgr._subscribers = []
        mgr._distribute_tick_sync(_make_tick())  # should not raise

    def test_subscriber_error_isolated(self, caplog):
        mgr = _make_manager()
        caplog.set_level(logging.ERROR)
        received = []
        mgr._subscribers = [lambda t: 1/0, lambda t: received.append(t)]
        mgr._distribute_tick_sync(_make_tick())
        assert len(received) == 1
        assert any("ZeroDivisionError" in r.message or "subscriber callback error" in r.message.lower() for r in caplog.records)

    def test_on_tick_is_alias(self):
        mgr = _make_manager()
        def cb(t):
            return None
        mgr.on_tick(cb)
        assert cb in mgr._subscribers or len(mgr._subscribers) >= 1


class TestManagerLifecycle:
    """Tests for start/stop lifecycle."""

    @pytest.mark.asyncio
    async def test_start_connects_and_creates_tasks(self):
        mgr = _make_manager(health_check_interval=0.1)
        await mgr.start()
        assert mgr._running and mgr._status == ConnectionStatus.CONNECTED
        assert mgr._message_loop_task and mgr._health_check_task
        mgr._ws_client.connect.assert_awaited_once()
        await mgr.stop()

    @pytest.mark.asyncio
    async def test_start_ignores_duplicate(self, caplog):
        mgr = _make_manager(health_check_interval=0.1)
        caplog.set_level(logging.WARNING)
        await mgr.start()
        await mgr.start()
        assert any("already running" in r.message.lower() for r in caplog.records)
        await mgr.stop()

    @pytest.mark.asyncio
    async def test_start_restores_subscriptions(self):
        mgr = _make_manager(health_check_interval=0.1)
        mgr._subscriptions = {("R", "NSE")}
        await mgr.start()
        mgr._ws_client.subscribe.assert_awaited_once()
        await mgr.stop()

    @pytest.mark.asyncio
    async def test_start_reraises_on_failure(self):
        mgr = _make_manager(health_check_interval=0.1)
        mgr._ws_client.connect = AsyncMock(side_effect=ConnectionError("refused"))
        with pytest.raises(ConnectionError, match="refused"):
            await mgr.start()
        assert not mgr._running

    @pytest.mark.asyncio
    async def test_stop_drains_queue(self):
        mgr = _make_manager(health_check_interval=0.1)
        await mgr.start()
        tick = _make_tick()
        await mgr._tick_queue.put(tick)
        received = []
        mgr._subscribers.append(lambda t: received.append(t))
        await mgr.stop()
        assert len(received) >= 1

    @pytest.mark.asyncio
    async def test_stop_ignores_when_not_running(self):
        mgr = _make_manager()
        await mgr.stop()  # should not raise

    @pytest.mark.asyncio
    async def test_start_stop_idempotent(self):
        mgr = _make_manager(health_check_interval=0.1)
        for _ in range(3):
            await mgr.start()
            assert mgr._running
            await mgr.stop()
            assert not mgr._running

    @pytest.mark.asyncio
    async def test_context_manager(self):
        mgr = _make_manager(health_check_interval=0.1)
        async with mgr as m:
            assert m._running
        assert not mgr._running


class TestManagerSubscriptions:
    """Tests for subscribe/unsubscribe tracking."""

    @pytest.mark.asyncio
    async def test_subscribe_async(self):
        mgr = _make_manager()
        mgr._status = ConnectionStatus.CONNECTED
        mgr._running = True
        await mgr._subscribe_async([("R", "NSE")])
        assert ("R", "NSE") in mgr._subscriptions
        mgr._ws_client.subscribe.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_unsubscribe_async(self):
        mgr = _make_manager()
        mgr._status = ConnectionStatus.CONNECTED
        mgr._running = True
        mgr._subscriptions = {("R", "NSE"), ("T", "NSE")}
        await mgr._unsubscribe_async({("R", "NSE")})
        assert ("R", "NSE") not in mgr._subscriptions

    def test_get_active_subscriptions(self):
        mgr = _make_manager()
        mgr._subscriptions = {("R", "NSE"), ("T", "NSE")}
        assert len(mgr.get_active_subscriptions()) == 2

    def test_restore_subscriptions(self):
        mgr = _make_manager()
        mgr.restore_subscriptions([("I", "NSE")])
        assert ("I", "NSE") in mgr._subscriptions


class TestManagerHealthMonitoring:
    """Tests for health status and metrics."""

    def test_initial_state(self):
        mgr = _make_manager()
        h = mgr.get_health_status()
        assert h.status == ConnectionStatus.DISCONNECTED
        assert h.messages_total == 0 and h.reconnect_count == 0

    def test_records_messages(self):
        mgr = _make_manager()
        mgr._on_tick_received(_make_tick())
        assert mgr._metrics.messages_total == 1

    def test_messages_per_second(self):
        mgr = _make_manager(message_rate_window=1.0)
        now = time.monotonic()
        for _ in range(10):
            mgr._metrics.message_timestamps.append(now)
        h = mgr.get_health_status()
        assert h.messages_per_second > 0

    def test_last_error(self):
        mgr = _make_manager()
        mgr._metrics.last_error = "Connection refused"
        assert mgr.get_health_status().last_error == "Connection refused"


class TestManagerReconnection:
    """Tests for reconnection logic."""

    @pytest.mark.asyncio
    async def test_reconnect_succeeds(self):
        mgr = _make_manager(reconnect_delay=0.01, max_reconnect_attempts=2)
        mgr._running = True
        mgr._subscriptions = {("R", "NSE")}
        await mgr._reconnect()
        assert mgr._metrics.reconnect_count == 1

    @pytest.mark.asyncio
    async def test_reconnect_skips_when_disconnecting(self):
        mgr = _make_manager()
        mgr._status = ConnectionStatus.DISCONNECTING
        mgr._running = True
        await mgr._reconnect()
        mgr._ws_client.connect.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_reconnect_skips_when_reconnecting(self):
        mgr = _make_manager()
        mgr._status = ConnectionStatus.RECONNECTING
        mgr._running = True
        await mgr._reconnect()


# ═══════════════════════════════════════════════════════════════════════════════
# DhanWebSocketClient Tests (SDK-based)
# ═══════════════════════════════════════════════════════════════════════════════
# Note: The SDK-based client uses dhanhq.marketfeed.MarketFeed with background
# threading. Old async WebSocket tests (heartbeat, reconnection, binary parsing)
# have been removed as they tested the deprecated custom binary parser.
# New SDK-based tests should verify security_id resolution and callback wiring.


class TestClientBasic:
    """Basic tests for SDK-based WebSocket client."""

    def test_is_connected_false_initially(self):
        """Client should report disconnected before connect() is called."""
        client = DhanWebSocketClient(access_token="t")
        assert not client.is_connected()

    def test_on_tick_registers_callback(self):
        """on_tick() should store the callback."""
        client = DhanWebSocketClient(access_token="t")
        cb = MagicMock()
        client.on_tick(cb)
        assert client._tick_callback is cb

    def test_repr_disconnected(self):
        """repr() should show disconnected state."""
        assert "disconnected" in repr(DhanWebSocketClient(access_token="t"))


# ── SDK wire contract tests (payloads captured live 2026-07-27) ──────────────


def _make_resolver(security_id="2885", wire_segment="NSE_EQ"):
    resolver = MagicMock()
    inst = MagicMock()
    inst.security_id = security_id
    resolver.resolve.return_value = inst
    resolver.wire_segment_of.return_value = wire_segment
    return resolver


# Real Full Data payload captured live from dhanhq SDK, 2026-07-27.
_FULL_DATA = {
    "type": "Full Data", "exchange_segment": 1, "security_id": 2885,
    "LTP": "1279.90", "LTQ": 1, "LTT": "12:23:58", "avg_price": "1282.85",
    "volume": 3143534, "total_sell_quantity": 905385, "total_buy_quantity": 618056,
    "OI": 0, "oi_day_high": 0, "oi_day_low": 0,
    "open": "1288.20", "close": "1278.00", "high": "1288.70", "low": "1278.50",
    "depth": [
        {"bid_quantity": 80, "ask_quantity": 2378, "bid_orders": 2, "ask_orders": 15,
         "bid_price": "1279.70", "ask_price": "1279.90"},
        {"bid_quantity": 150, "ask_quantity": 1013, "bid_orders": 3, "ask_orders": 9,
         "bid_price": "1279.50", "ask_price": "1280.00"},
    ],
}

# Real Quote Data shape (SDK process_quote — no depth, no symbol key).
_QUOTE_DATA = {
    "type": "Quote Data", "exchange_segment": 1, "security_id": 2885,
    "LTP": "1279.90", "LTQ": 44, "LTT": "12:23:58", "avg_price": "1282.85",
    "volume": 3143578, "total_sell_quantity": 905346, "total_buy_quantity": 618120,
    "open": "1288.20", "close": "1278.00", "high": "1288.70", "low": "1278.50",
}


class TestSubscribeSdkTupleFormat:
    """SDK v2 JSON packet requires string SecurityId and the instrument's
    own wire segment (an index lives on IDX_I=0, not the exchange default)."""

    @pytest.mark.asyncio
    async def test_security_id_is_string_in_sdk_tuple(self):
        client = DhanWebSocketClient(access_token="t", resolver=_make_resolver())
        await client.subscribe([("RELIANCE", "NSE")], mode="full")
        assert client._instruments == [(1, "2885", 21)]

    @pytest.mark.asyncio
    async def test_segment_comes_from_resolver_wire_segment(self):
        resolver = _make_resolver(security_id="13", wire_segment="IDX_I")
        client = DhanWebSocketClient(access_token="t", resolver=resolver)
        await client.subscribe([("NIFTY", "NSE")], mode="quote")
        assert client._instruments == [(0, "13", 17)]

    @pytest.mark.asyncio
    async def test_index_full_mode_downgrades_to_quote(self):
        """Dhan serves no Full packets for indices (no depth) — full mode
        on IDX_I silently streams nothing, so downgrade to quote."""
        resolver = _make_resolver(security_id="13", wire_segment="IDX_I")
        client = DhanWebSocketClient(access_token="t", resolver=resolver)
        await client.subscribe([("NIFTY", "NSE")], mode="full")
        assert client._instruments == [(0, "13", 17)]

    @pytest.mark.asyncio
    async def test_subscribe_records_sid_to_symbol_mapping(self):
        client = DhanWebSocketClient(access_token="t", resolver=_make_resolver())
        await client.subscribe([("RELIANCE", "NSE")])
        assert client._symbol_by_sid["2885"] == "RELIANCE"


class TestParseSdkData:
    """SDK payloads carry security_id/LTP/volume/depth — never symbol,
    last_price or best_bid_price. Parse must use the real keys."""

    def _client(self):
        client = DhanWebSocketClient(access_token="t")
        client._symbol_by_sid["2885"] = "RELIANCE"
        return client

    def test_parses_full_data_with_depth_bid_ask(self):
        tick = self._client()._parse_sdk_data(dict(_FULL_DATA))
        assert tick is not None
        assert tick.symbol == "RELIANCE"
        assert tick.ltp == Decimal("1279.90")
        assert tick.bid == Decimal("1279.70")  # depth[0].bid_price
        assert tick.ask == Decimal("1279.90")  # depth[0].ask_price
        assert tick.cumulative_volume == 3143534

    def test_parses_quote_data_without_depth(self):
        tick = self._client()._parse_sdk_data(dict(_QUOTE_DATA))
        assert tick is not None
        assert tick.ltp == Decimal("1279.90")
        assert tick.bid == Decimal("0")
        assert tick.ask == Decimal("0")

    def test_unknown_sid_falls_back_to_sid_string(self):
        client = DhanWebSocketClient(access_token="t")
        tick = client._parse_sdk_data(dict(_QUOTE_DATA))
        assert tick is not None
        assert tick.symbol == "2885"

    def test_missing_security_id_returns_none(self):
        assert self._client()._parse_sdk_data({"type": "Quote Data"}) is None

    def test_volume_delta_across_ticks(self):
        client = self._client()
        first = client._parse_sdk_data(dict(_FULL_DATA))
        second = client._parse_sdk_data({**_FULL_DATA, "volume": 3143634})
        assert first.delta_volume == 0  # baseline
        assert second.delta_volume == 100
        assert second.cumulative_volume == 3143634



class TestSubscribePairsMode:
    """W5: subscribe_pairs must pass mode through to the ws client."""

    @pytest.mark.asyncio
    async def test_subscribe_pairs_forwards_mode(self):
        mgr = _make_manager()
        mgr._status = ConnectionStatus.CONNECTED
        mgr._running = True
        await mgr.subscribe_pairs([("TCS", "NSE")], mode="full")
        mgr._ws_client.subscribe.assert_awaited_once_with([("TCS", "NSE")], mode="full")

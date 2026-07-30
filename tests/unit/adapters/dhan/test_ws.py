from __future__ import annotations

import threading
import time as _time
from unittest.mock import MagicMock, patch

import pytest

from scalpr.adapters.dhan._ws import DhanWebSocket, WSState
from scalpr.engine.clock import StaticClock

# ── Helpers ──────────────────────────────────────────────────────────


def _await_state(ws: DhanWebSocket, target: WSState, timeout: float = 3.0) -> None:
    """Wait for ws.state to reach target. Uses real time to avoid mock interference."""
    deadline = _time.monotonic() + timeout
    while _time.monotonic() < deadline:
        if ws.state == target:
            return
        _time.sleep(0.005)
    raise AssertionError(f"State did not become {target} within {timeout}s (was {ws.state})")


# ── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def mock_sdk():
    """Mock dhanhq SDK MarketFeed.

    Each feed instance gets its own exit event so feed.run() can be
    unblocked independently per reconnect cycle.

    Yields feeds list where feeds[i] is the i-th created feed mock.
    Call feeds[i].close_connection() to unblock feeds[i].run().
    """
    feeds: list[MagicMock] = []

    def _make_feed(
        dhan_context=None,
        instruments=None,
        version="v2",
        on_connect=None,
        on_message=None,
        on_close=None,
        on_error=None,
    ):
        feed_exit = threading.Event()
        feed = MagicMock()
        feed._dhan_context = dhan_context
        feed._instruments = instruments
        feed.on_connect = on_connect
        feed.on_message = on_message
        feed.on_close = on_close
        feed.on_error = on_error
        feed.run.side_effect = lambda: feed_exit.wait(timeout=3)
        feed.close_connection.side_effect = lambda: feed_exit.set()
        feed._exit_event = feed_exit
        feeds.append(feed)
        return feed

    with patch("scalpr.adapters.dhan._ws._sdk_market_feed_class") as mock_fn:
        mock_cls = MagicMock()
        mock_cls.side_effect = _make_feed
        mock_fn.return_value = mock_cls
        yield feeds


@pytest.fixture
def ws(mock_sdk):
    return DhanWebSocket(access_token="test_token", client_id="test_client")


# ── FSM state transitions ───────────────────────────────────────────


class TestFSMInitial:
    def test_initial_state_is_disconnected(self, ws: DhanWebSocket) -> None:
        assert ws.state == WSState.DISCONNECTED


class TestFSMConnect:
    def test_connect_transitions_to_connecting(self, ws: DhanWebSocket) -> None:
        ws.connect()
        assert ws.state == WSState.CONNECTING

    def test_connect_from_connecting_is_noop(self, ws: DhanWebSocket) -> None:
        ws.connect()
        ws.connect()
        assert ws.state == WSState.CONNECTING

    def test_connect_from_connected_is_noop(self, ws: DhanWebSocket) -> None:
        ws.connect()
        ws._on_connect(None)  # simulate SDK on_connect via triggered callback
        ws.connect()
        assert ws.state == WSState.CONNECTED


class TestFSMHandshake:
    def test_handshake_success_transitions_to_connected(self, ws: DhanWebSocket, mock_sdk) -> None:
        feeds = mock_sdk
        ws.connect()
        assert ws.state == WSState.CONNECTING
        feeds[0].on_connect(feeds[0])
        _await_state(ws, WSState.CONNECTED)
        assert ws.state == WSState.CONNECTED

    def test_handshake_success_resets_retry_count(self, ws: DhanWebSocket, mock_sdk) -> None:
        feeds = mock_sdk
        ws._retry_count = 3
        ws.connect()
        feeds[0].on_connect(feeds[0])
        _await_state(ws, WSState.CONNECTED)
        assert ws._retry_count == 0

    def test_handshake_replays_subscriptions(self, ws: DhanWebSocket, mock_sdk) -> None:
        feeds = mock_sdk
        ws.subscribe([("RELIANCE", "NSE_EQ")])
        ws.connect()
        deadline = _time.monotonic() + 3.0
        while _time.monotonic() < deadline and not feeds:
            _time.sleep(0.005)
        assert feeds, "MarketFeed mock was not created"
        feeds[0].on_connect(feeds[0])
        _await_state(ws, WSState.CONNECTED)
        feeds[0].subscribe_symbols.assert_called_once()


class TestFSMClose:
    def test_close_transitions_to_reconnecting(self, ws: DhanWebSocket, mock_sdk) -> None:
        feeds = mock_sdk
        ws.connect()
        feeds[0].on_connect(feeds[0])
        _await_state(ws, WSState.CONNECTED)
        feeds[0].on_close(feeds[0])
        assert ws.state == WSState.RECONNECTING

    def test_close_while_connecting_does_nothing(self, ws: DhanWebSocket, mock_sdk) -> None:
        feeds = mock_sdk
        ws.connect()
        feeds[0].on_close(feeds[0])
        assert ws.state == WSState.CONNECTING

    def test_error_transitions_to_reconnecting(self, ws: DhanWebSocket, mock_sdk) -> None:
        feeds = mock_sdk
        ws.connect()
        feeds[0].on_connect(feeds[0])
        _await_state(ws, WSState.CONNECTED)
        feeds[0].on_error(feeds[0], Exception("test"))
        assert ws.state == WSState.RECONNECTING


class TestFSMMaxRetries:
    def test_max_retries_transitions_to_disconnected_permanent(self, ws: DhanWebSocket, mock_sdk) -> None:
        feeds = mock_sdk
        ws.connect()
        feeds[0].on_connect(feeds[0])
        _await_state(ws, WSState.CONNECTED)

        ws._retry_count = ws.MAX_RETRIES
        feeds[0].on_close(feeds[0])
        assert ws.state == WSState.RECONNECTING

        feeds[0].close_connection()
        _await_state(ws, WSState.DISCONNECTED_PERMANENT)

    def test_connect_resets_from_disconnected_permanent(self, ws: DhanWebSocket, mock_sdk) -> None:
        feeds = mock_sdk
        ws.connect()
        feeds[0].on_connect(feeds[0])
        _await_state(ws, WSState.CONNECTED)

        ws._retry_count = ws.MAX_RETRIES
        feeds[0].on_close(feeds[0])
        feeds[0].close_connection()
        _await_state(ws, WSState.DISCONNECTED_PERMANENT)

        ws._thread.join(timeout=2)
        ws.connect()
        _await_state(ws, WSState.CONNECTING)
        assert ws._retry_count == 0


class TestFSMDisconnect:
    def test_disconnect_sets_disconnected(self, ws: DhanWebSocket, mock_sdk) -> None:
        feeds = mock_sdk
        ws.connect()
        feeds[0].on_connect(feeds[0])
        _await_state(ws, WSState.CONNECTED)
        ws.disconnect()
        assert ws.state == WSState.DISCONNECTED

    def test_disconnect_when_disconnected_is_noop(self, ws: DhanWebSocket) -> None:
        ws.disconnect()
        assert ws.state == WSState.DISCONNECTED


# ── Subscription management ─────────────────────────────────────────


class TestSubscriptionSet:
    def test_subscribe_adds_to_internal_set(self, ws: DhanWebSocket) -> None:
        ws.subscribe([("RELIANCE", "NSE_EQ")])
        assert ("RELIANCE", "NSE_EQ") in ws._subscriptions

    def test_unsubscribe_removes_from_set(self, ws: DhanWebSocket) -> None:
        ws.subscribe([("RELIANCE", "NSE_EQ"), ("TCS", "NSE_EQ")])
        ws.unsubscribe([("RELIANCE", "NSE_EQ")])
        assert ("RELIANCE", "NSE_EQ") not in ws._subscriptions
        assert ("TCS", "NSE_EQ") in ws._subscriptions

    def test_subscribe_multiple_adds_all(self, ws: DhanWebSocket) -> None:
        ids = [("A", "NSE_EQ"), ("B", "NSE_EQ"), ("C", "NSE_EQ")]
        ws.subscribe(ids)
        assert ws._subscriptions == set(ids)

    def test_subscribe_empty_list_noop(self, ws: DhanWebSocket) -> None:
        ws.subscribe([])
        assert ws._subscriptions == set()

    def test_unsubscribe_nonexistent_noop(self, ws: DhanWebSocket) -> None:
        ws.subscribe([("RELIANCE", "NSE_EQ")])
        ws.unsubscribe([("TCS", "NSE_EQ")])
        assert ws._subscriptions == {("RELIANCE", "NSE_EQ")}

    def test_subscribe_sends_frame_when_connected(self, ws: DhanWebSocket, mock_sdk) -> None:
        feeds = mock_sdk
        ws.connect()
        feeds[0].on_connect(feeds[0])
        _await_state(ws, WSState.CONNECTED)
        ws.subscribe([("RELIANCE", "NSE_EQ")])
        feeds[0].subscribe_symbols.assert_called_once()

    def test_subscribe_does_not_send_when_disconnected(self, ws: DhanWebSocket, mock_sdk) -> None:
        feeds = mock_sdk
        ws.connect()
        feeds[0].on_connect(feeds[0])
        _await_state(ws, WSState.CONNECTED)
        feeds[0].subscribe_symbols.reset_mock()
        ws.disconnect()
        ws.subscribe([("RELIANCE", "NSE_EQ")])
        feeds[0].subscribe_symbols.assert_not_called()

    def test_unsubscribe_sends_frame_when_connected(self, ws: DhanWebSocket, mock_sdk) -> None:
        feeds = mock_sdk
        ws.connect()
        feeds[0].on_connect(feeds[0])
        _await_state(ws, WSState.CONNECTED)
        ws.subscribe([("RELIANCE", "NSE_EQ")])
        feeds[0].subscribe_symbols.reset_mock()
        ws.unsubscribe([("RELIANCE", "NSE_EQ")])
        feeds[0].unsubscribe_symbols.assert_called_once()


# ── Backoff ──────────────────────────────────────────────────────────


class TestBackoff:
    def test_backoff_sequence_matches_expected(self) -> None:
        assert DhanWebSocket.BACKOFF == [1.0, 2.0, 4.0, 8.0, 16.0, 30.0]

    def test_backoff_capped_at_30s(self) -> None:
        assert max(DhanWebSocket.BACKOFF) == 30.0

    def test_backoff_length_matches_max_retries(self) -> None:
        assert len(DhanWebSocket.BACKOFF) > DhanWebSocket.MAX_RETRIES

    def test_backoff_resets_on_successful_connect(self, ws: DhanWebSocket, mock_sdk) -> None:
        feeds = mock_sdk
        ws._retry_count = 3
        ws.connect()
        feeds[0].on_connect(feeds[0])
        _await_state(ws, WSState.CONNECTED)
        assert ws._retry_count == 0

    def test_backoff_retry_count_increments_on_reconnect(self, ws: DhanWebSocket, mock_sdk) -> None:
        feeds = mock_sdk
        ws.connect()
        feeds[0].on_connect(feeds[0])
        _await_state(ws, WSState.CONNECTED)

        ws._retry_count = 0
        feeds[0].on_close(feeds[0])
        feeds[0].close_connection()
        _await_state(ws, WSState.CONNECTING)
        assert ws._retry_count == 1

    def test_backoff_delay_capped_values(self) -> None:
        for i in range(DhanWebSocket.MAX_RETRIES):
            idx = min(i, len(DhanWebSocket.BACKOFF) - 1)
            assert DhanWebSocket.BACKOFF[idx] <= 30.0

    def test_backoff_clock_accepted(self) -> None:
        clock = StaticClock()
        ws = DhanWebSocket(access_token="t", client_id="c", clock=clock)
        assert ws._clock is clock


# ── Tick handling ────────────────────────────────────────────────────


class TestTickHandling:
    def test_tick_calls_on_tick(self, ws: DhanWebSocket, mock_sdk) -> None:
        received = []

        def cb(tick):
            received.append(tick)

        ws.set_tick_callback(cb)
        feeds = mock_sdk
        ws.connect()
        feeds[0].on_connect(feeds[0])
        _await_state(ws, WSState.CONNECTED)
        feeds[0].on_message(feeds[0], {
            "type": "Quote Data",
            "security_id": "123",
            "LTP": "1500.50",
            "volume": 10000,
        })
        assert len(received) == 1

    def test_tick_callback_error_does_not_crash(self, ws: DhanWebSocket, mock_sdk) -> None:
        calls = []

        def cb(tick):
            calls.append(1)
            raise ValueError("boom")

        ws.set_tick_callback(cb)
        feeds = mock_sdk
        ws.connect()
        feeds[0].on_connect(feeds[0])
        _await_state(ws, WSState.CONNECTED)
        feeds[0].on_message(feeds[0], {
            "type": "Quote Data",
            "security_id": "123",
            "LTP": "1500.50",
        })
        assert len(calls) == 1

    def test_no_on_tick_no_error(self, ws: DhanWebSocket, mock_sdk) -> None:
        feeds = mock_sdk
        ws.connect()
        feeds[0].on_connect(feeds[0])
        _await_state(ws, WSState.CONNECTED)
        feeds[0].on_message(feeds[0], {
            "type": "Quote Data",
            "security_id": "123",
            "LTP": "1500.50",
        })

    def test_unknown_message_type_ignored(self, ws: DhanWebSocket, mock_sdk) -> None:
        received = []

        def cb(tick):
            received.append(tick)

        ws.set_tick_callback(cb)
        feeds = mock_sdk
        ws.connect()
        feeds[0].on_connect(feeds[0])
        _await_state(ws, WSState.CONNECTED)
        feeds[0].on_message(feeds[0], {"type": "Unknown", "data": "x"})
        assert len(received) == 0

    def test_empty_message_ignored(self, ws: DhanWebSocket, mock_sdk) -> None:
        received = []

        def cb(tick):
            received.append(tick)

        ws.set_tick_callback(cb)
        feeds = mock_sdk
        ws.connect()
        feeds[0].on_connect(feeds[0])
        _await_state(ws, WSState.CONNECTED)
        feeds[0].on_message(feeds[0], None)
        assert len(received) == 0

    def test_tick_no_security_id_returns_none(self, ws: DhanWebSocket) -> None:
        tick = ws._parse_sdk_data({"LTP": "100"})
        assert tick is None

    def test_tick_with_depth_parses_bid_ask(self, ws: DhanWebSocket) -> None:
        data = {
            "type": "Full Data",
            "security_id": "123",
            "LTP": "1500.50",
            "volume": 10000,
            "depth": [{"bid_price": "1499", "ask_price": "1501"}],
        }
        tick = ws._parse_sdk_data(data)
        assert tick is not None
        assert tick.bid == 1499
        assert tick.ask == 1501


# ── Thread safety ────────────────────────────────────────────────────


class TestThreadSafety:
    def test_concurrent_subscribe_unsubscribe_no_crash(self, ws: DhanWebSocket) -> None:
        errors = []

        def sub_loop():
            try:
                for i in range(100):
                    ws.subscribe([(f"S{i}", "NSE_EQ")])
            except Exception as e:
                errors.append(e)

        def unsub_loop():
            try:
                for i in range(100):
                    ws.unsubscribe([(f"S{i}", "NSE_EQ")])
            except Exception as e:
                errors.append(e)

        t1 = threading.Thread(target=sub_loop, daemon=True)
        t2 = threading.Thread(target=unsub_loop, daemon=True)
        t1.start()
        t2.start()
        t1.join(timeout=5)
        t2.join(timeout=5)
        assert not errors

    def test_state_is_thread_safe(self, ws: DhanWebSocket, mock_sdk) -> None:
        reads: list[WSState] = []

        def read_loop():
            for _ in range(100):
                reads.append(ws.state)

        feeds = mock_sdk
        ws.connect()
        t = threading.Thread(target=read_loop, daemon=True)
        t.start()
        feeds[0].on_connect(feeds[0])
        feeds[0].on_close(feeds[0])
        feeds[0].close_connection()
        t.join(timeout=2)
        assert len(reads) == 100
        assert all(isinstance(s, WSState) for s in reads)

    def test_concurrent_connect_disconnect_no_crash(self, ws: DhanWebSocket, mock_sdk) -> None:
        errors = []

        def toggle_loop():
            try:
                for _ in range(10):
                    ws.connect()
                    ws.disconnect()
            except Exception as e:
                errors.append(e)

        ts = [threading.Thread(target=toggle_loop, daemon=True) for _ in range(4)]
        for t in ts:
            t.start()
        for t in ts:
            t.join(timeout=5)
        assert not errors


# ── Edge cases ───────────────────────────────────────────────────────


class TestEdgeCases:
    def test_set_tick_callback_overwrites(self, ws: DhanWebSocket) -> None:
        results: list[int] = []

        def cb1(t):
            results.append(1)

        def cb2(t):
            results.append(2)

        ws.set_tick_callback(cb1)
        ws.set_tick_callback(cb2)
        assert ws._on_tick is cb2

    def test_state_property_returns_current(self, ws: DhanWebSocket) -> None:
        assert ws.state == WSState.DISCONNECTED

    def test_state_is_enum_not_string(self, ws: DhanWebSocket) -> None:
        assert isinstance(ws.state, WSState)

    def test_connect_when_already_connected_noop(self, ws: DhanWebSocket, mock_sdk) -> None:
        feeds = mock_sdk
        ws.connect()
        feeds[0].on_connect(feeds[0])
        _await_state(ws, WSState.CONNECTED)
        ws.connect()
        assert ws.state == WSState.CONNECTED


@pytest.mark.parametrize("method,args", [
    ("connect", []),
    ("disconnect", []),
    ("subscribe", [[("S", "NSE_EQ")]]),
    ("unsubscribe", [[("S", "NSE_EQ")]]),
])
def test_public_methods_return_none(ws: DhanWebSocket, method: str, args: list) -> None:
    result = getattr(ws, method)(*args)
    assert result is None

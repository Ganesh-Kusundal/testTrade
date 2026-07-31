from __future__ import annotations

import asyncio
import threading
from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from scalpr.adapters.dhan._types import MarketDepthLevel, MarketDepthSnapshot
from scalpr.adapters.dhan._ws import DhanWebSocket

# ── Helpers ──────────────────────────────────────────────────────────


def _make_bid_levels(count: int = 5, base_price: float = 100.0) -> list[dict]:
    return [
        {"price": base_price - i * 0.5, "quantity": 1000 - i * 100, "orders": 10 - i}
        for i in range(count)
    ]


def _make_ask_levels(count: int = 5, base_price: float = 101.0) -> list[dict]:
    return [
        {"price": base_price + i * 0.5, "quantity": 800 - i * 80, "orders": 8 - i}
        for i in range(count)
    ]


# ── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def mock_sdk():
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
        feed = MagicMock()
        feed._dhan_context = dhan_context
        feed._instruments = instruments
        feed.on_connect = on_connect
        feed.on_message = on_message
        feed.on_close = on_close
        feed.on_error = on_error
        # Call on_connect synchronously so _run_feed completes immediately
        if on_connect:
            on_connect(feed)
        feed.run.side_effect = lambda: None
        feed.close_connection.side_effect = lambda: None
        feeds.append(feed)
        return feed

    with patch("scalpr.adapters.dhan._ws._sdk_market_feed_class") as mock_fn:
        mock_cls = MagicMock()
        mock_cls.side_effect = _make_feed
        mock_fn.return_value = mock_cls
        yield feeds


async def _depth_recv_noop():
    raise ConnectionError("mock recv end")


async def _depth_connect_noop():
    pass


@pytest.fixture
def mock_depth_sdk():
    feeds: list[Any] = []

    def _make_feed(dhan_context=None, instruments=None, depth_level=20):
        feed = MagicMock()
        feed.depth_level = depth_level
        feed._instruments = instruments or []
        feed.close_connection = MagicMock()
        feed.subscribe_symbols = MagicMock()
        feed.unsubscribe_symbols = MagicMock()
        feed.process_data = MagicMock()
        feed.connect = _depth_connect_noop

        feed.ws = MagicMock()
        feed.ws.recv = _depth_recv_noop

        feed._loop = asyncio.new_event_loop()
        feed.loop = MagicMock()
        feed.loop.run_until_complete.side_effect = (
            lambda coro: feed._loop.run_until_complete(coro)
        )

        feeds.append(feed)
        return feed

    mock_cls = MagicMock()
    mock_cls.side_effect = _make_feed
    with patch("scalpr.adapters.dhan._ws._full_depth_class", return_value=mock_cls):
        yield feeds


@pytest.fixture
def ws(mock_sdk, mock_depth_sdk):
    return DhanWebSocket(access_token="test_token", client_id="test_client")


# ── Depth subscription set ──────────────────────────────────────────


class TestDepthSubscriptionSet:
    def test_subscribe_depth_adds_to_set(self, ws: DhanWebSocket) -> None:
        ws.subscribe_depth([("RELIANCE", "NSE_EQ")])
        assert ("RELIANCE", "NSE_EQ") in ws._depth_subscriptions[20]

    def test_subscribe_depth_multiple_adds_all(self, ws: DhanWebSocket) -> None:
        ids = [("A", "NSE_EQ"), ("B", "NSE_FNO"), ("C", "IDX_I")]
        ws.subscribe_depth(ids)
        assert ws._depth_subscriptions[20] == set(ids)

    def test_subscribe_depth_empty_list_noop(self, ws: DhanWebSocket) -> None:
        ws.subscribe_depth([])
        assert ws._depth_subscriptions[20] == set()

    def test_subscribe_depth_duplicates_deduped(self, ws: DhanWebSocket) -> None:
        ws.subscribe_depth([("RELIANCE", "NSE_EQ")])
        ws.subscribe_depth([("RELIANCE", "NSE_EQ")])
        assert ws._depth_subscriptions[20] == {("RELIANCE", "NSE_EQ")}

    def test_unsubscribe_depth_removes_from_set(self, ws: DhanWebSocket) -> None:
        ws.subscribe_depth([("RELIANCE", "NSE_EQ"), ("TCS", "NSE_EQ")])
        ws.unsubscribe_depth([("RELIANCE", "NSE_EQ")])
        assert ("RELIANCE", "NSE_EQ") not in ws._depth_subscriptions[20]
        assert ("TCS", "NSE_EQ") in ws._depth_subscriptions[20]

    def test_unsubscribe_depth_nonexistent_noop(self, ws: DhanWebSocket) -> None:
        ws.subscribe_depth([("RELIANCE", "NSE_EQ")])
        ws.unsubscribe_depth([("TCS", "NSE_EQ")])
        assert ws._depth_subscriptions[20] == {("RELIANCE", "NSE_EQ")}

    def test_subscribe_depth_does_not_affect_quote_subs(self, ws: DhanWebSocket) -> None:
        ws.subscribe([("INFY", "NSE_EQ")])
        ws.subscribe_depth([("RELIANCE", "NSE_EQ")])
        assert ws._subscriptions == {("INFY", "NSE_EQ")}
        assert ws._depth_subscriptions[20] == {("RELIANCE", "NSE_EQ")}


# ── Depth feed lifecycle ────────────────────────────────────────────


class TestDepthFeedLifecycle:
    def _connect_sync(self, ws: DhanWebSocket, mock_sdk: list) -> None:
        ws._run_feed()

    def test_subscribe_depth_starts_feed_when_connected(
        self, ws: DhanWebSocket, mock_sdk, mock_depth_sdk,
    ) -> None:
        self._connect_sync(ws, mock_sdk)
        ws.subscribe_depth([("RELIANCE", "NSE_EQ")])
        assert ws._depth_feeds.get(20) is not None
        ws._stop_depth_feed()

    def test_subscribe_depth_queues_command_when_feed_running(
        self, ws: DhanWebSocket, mock_sdk, mock_depth_sdk,
    ) -> None:
        self._connect_sync(ws, mock_sdk)
        ws.subscribe_depth([("A", "NSE_EQ")])
        qsize_before = ws._depth_cmd_queues[20].qsize()
        ws.subscribe_depth([("B", "NSE_EQ")])
        assert ws._depth_cmd_queues[20].qsize() == qsize_before + 1
        ws._stop_depth_feed()

    def test_unsubscribe_depth_queues_command_when_feed_running(
        self, ws: DhanWebSocket, mock_sdk, mock_depth_sdk,
    ) -> None:
        self._connect_sync(ws, mock_sdk)
        ws.subscribe_depth([("A", "NSE_EQ")])
        ws._depth_cmd_queues[20].queue.clear()
        ws.unsubscribe_depth([("A", "NSE_EQ")])
        assert ws._depth_cmd_queues[20].qsize() >= 1
        cmd = ws._depth_cmd_queues[20].get_nowait()
        assert cmd["action"] == "unsubscribe"
        ws._stop_depth_feed()

    def test_subscribe_depth_does_not_start_feed_when_disconnected(
        self, ws: DhanWebSocket,
    ) -> None:
        ws.subscribe_depth([("RELIANCE", "NSE_EQ")])
        assert ws._depth_feeds.get(20) is None
        assert ws._depth_threads.get(20) is None

    def test_start_depth_feed_sets_depth_feed(
        self, ws: DhanWebSocket, mock_depth_sdk,
    ) -> None:
        ws._depth_subscriptions[20].update([("RELIANCE", "NSE_EQ")])
        ws._start_depth_feed()
        assert ws._depth_feeds.get(20) is not None
        ws._stop_depth_feed()

    def test_stop_depth_feed_cleans_up(
        self, ws: DhanWebSocket, mock_depth_sdk,
    ) -> None:
        ws._depth_subscriptions[20].update([("RELIANCE", "NSE_EQ")])
        ws._start_depth_feed()
        ws._stop_depth_feed()
        assert ws._depth_feeds.get(20) is None

    def test_disconnect_stops_depth_feed(
        self, ws: DhanWebSocket, mock_sdk, mock_depth_sdk,
    ) -> None:
        self._connect_sync(ws, mock_sdk)
        ws.subscribe_depth([("RELIANCE", "NSE_EQ")])
        assert ws._depth_feeds.get(20) is not None
        ws.disconnect()
        assert ws._depth_feeds.get(20) is None

    def test_on_connect_starts_depth_feed_for_pending_subs(
        self, ws: DhanWebSocket, mock_sdk, mock_depth_sdk,
    ) -> None:
        ws.subscribe_depth([("RELIANCE", "NSE_EQ")])
        self._connect_sync(ws, mock_sdk)
        assert ws._depth_feeds.get(20) is not None
        ws._stop_depth_feed()

    def test_start_depth_feed_noop_when_no_subscriptions(
        self, ws: DhanWebSocket, mock_depth_sdk,
    ) -> None:
        ws._start_depth_feed()
        assert ws._depth_feeds.get(20) is None


# ── Depth SDK instrument conversion ─────────────────────────────────


class TestDepthSDKConversion:
    def test_to_depth_sdk_rejects_unknown_segment(self) -> None:
        with pytest.raises(ValueError, match="does not support wire segment"):
            DhanWebSocket._to_depth_sdk_instruments([("100", "UNKNOWN")])

    def test_to_depth_sdk_maps_nse_eq(self) -> None:
        result = DhanWebSocket._to_depth_sdk_instruments([("100", "NSE_EQ")])
        assert result == [(1, "100")]

    def test_to_depth_sdk_maps_nse_fno(self) -> None:
        result = DhanWebSocket._to_depth_sdk_instruments([("100", "NSE_FNO")])
        assert result == [(2, "100")]

    def test_to_depth_sdk_rejects_bse_eq(self) -> None:
        with pytest.raises(ValueError, match="does not support wire segment"):
            DhanWebSocket._to_depth_sdk_instruments([("100", "BSE_EQ")])

    def test_to_depth_sdk_deduplicates(self) -> None:
        result = DhanWebSocket._to_depth_sdk_instruments([("100", "NSE_EQ"), ("100", "NSE_EQ")])
        assert len(result) == 1


# ── Depth callback ──────────────────────────────────────────────────


class TestDepthCallback:
    def test_set_depth_callback_overwrites(self, ws: DhanWebSocket) -> None:
        def cb1(_):
            pass

        def cb2(_):
            pass

        ws.set_depth_callback(cb1)
        ws.set_depth_callback(cb2)
        assert ws._on_depth_tick is cb2

    def test_accumulate_depth_update_calls_callback(self, ws: DhanWebSocket) -> None:
        received: list[MarketDepthSnapshot] = []
        ws.set_depth_callback(received.append)

        buffer: dict = {}
        bids = _make_bid_levels(5)
        asks = _make_ask_levels(5)

        ws._accumulate_depth_update(buffer, {
            "security_id": 100,
            "exchange_segment": 1,
            "type": "Bid",
            "depth": bids,
        })
        assert len(received) == 0

        ws._accumulate_depth_update(buffer, {
            "security_id": 100,
            "exchange_segment": 1,
            "type": "Ask",
            "depth": asks,
        })
        assert len(received) == 1
        snap = received[0]
        assert snap.security_id == "100"
        assert snap.exchange == "NSE_EQ"
        assert len(snap.levels) == 5

    def test_accumulate_depth_callback_error_does_not_crash(self, ws: DhanWebSocket) -> None:
        calls: list[int] = []

        def cb(_):
            calls.append(1)
            raise ValueError("boom")

        ws.set_depth_callback(cb)
        buffer: dict = {}
        ws._accumulate_depth_update(buffer, {
            "security_id": 100, "exchange_segment": 1, "type": "Bid", "depth": _make_bid_levels(1),
        })
        ws._accumulate_depth_update(buffer, {
            "security_id": 100, "exchange_segment": 1, "type": "Ask", "depth": _make_ask_levels(1),
        })
        assert len(calls) == 1

    def test_accumulate_depth_no_callback_no_error(self, ws: DhanWebSocket) -> None:
        buffer: dict = {}
        ws._accumulate_depth_update(buffer, {
            "security_id": 100, "exchange_segment": 1, "type": "Bid", "depth": _make_bid_levels(1),
        })
        ws._accumulate_depth_update(buffer, {
            "security_id": 100, "exchange_segment": 1, "type": "Ask", "depth": _make_ask_levels(1),
        })

    def test_accumulate_depth_unmatched_bid_no_callback(self, ws: DhanWebSocket) -> None:
        received: list[MarketDepthSnapshot] = []
        ws.set_depth_callback(received.append)

        buffer: dict = {}
        ws._accumulate_depth_update(buffer, {
            "security_id": 100, "exchange_segment": 1, "type": "Bid", "depth": _make_bid_levels(1),
        })
        assert len(received) == 0

    def test_accumulate_depth_multiple_instruments(self, ws: DhanWebSocket) -> None:
        received: list[MarketDepthSnapshot] = []
        ws.set_depth_callback(received.append)

        buffer: dict = {}
        ws._accumulate_depth_update(buffer, {
            "security_id": 100, "exchange_segment": 1, "type": "Bid", "depth": _make_bid_levels(1),
        })
        ws._accumulate_depth_update(buffer, {
            "security_id": 200, "exchange_segment": 1, "type": "Bid", "depth": _make_bid_levels(1),
        })
        assert len(received) == 0

        ws._accumulate_depth_update(buffer, {
            "security_id": 100, "exchange_segment": 1, "type": "Ask", "depth": _make_ask_levels(1),
        })
        assert len(received) == 1
        assert received[0].security_id == "100"

        ws._accumulate_depth_update(buffer, {
            "security_id": 200, "exchange_segment": 1, "type": "Ask", "depth": _make_ask_levels(1),
        })
        assert len(received) == 2
        assert received[1].security_id == "200"


# ── Combine depth snapshot ──────────────────────────────────────────


class TestCombineDepthSnapshot:
    def test_combine_produces_correct_count(self, ws: DhanWebSocket) -> None:
        bids = _make_bid_levels(5)
        asks = _make_ask_levels(5)
        snap = ws._combine_depth_snapshot("100", "NSE_EQ", bids, asks)
        assert len(snap.levels) == 5

    def test_combine_sorts_bids_descending(self, ws: DhanWebSocket) -> None:
        bids = [{"price": 101, "quantity": 100, "orders": 1},
                {"price": 100, "quantity": 200, "orders": 2}]
        asks = [{"price": 102, "quantity": 50, "orders": 1},
                {"price": 103, "quantity": 60, "orders": 2}]
        snap = ws._combine_depth_snapshot("100", "NSE_EQ", bids, asks)
        assert snap.levels[0].bid_price == 101
        assert snap.levels[1].bid_price == 100

    def test_combine_sorts_asks_ascending(self, ws: DhanWebSocket) -> None:
        bids = [{"price": 100, "quantity": 100, "orders": 1},
                {"price": 99, "quantity": 200, "orders": 2}]
        asks = [{"price": 103, "quantity": 60, "orders": 2},
                {"price": 102, "quantity": 50, "orders": 1}]
        snap = ws._combine_depth_snapshot("100", "NSE_EQ", bids, asks)
        assert snap.levels[0].ask_price == 102
        assert snap.levels[1].ask_price == 103

    def test_combine_handles_unequal_lengths(self, ws: DhanWebSocket) -> None:
        bids = _make_bid_levels(5)
        asks = _make_ask_levels(3)
        snap = ws._combine_depth_snapshot("100", "NSE_EQ", bids, asks)
        assert len(snap.levels) == 3

    def test_combine_handles_empty_levels(self, ws: DhanWebSocket) -> None:
        snap = ws._combine_depth_snapshot("100", "NSE_EQ", [], [])
        assert len(snap.levels) == 0

    def test_combine_sets_timestamp(self, ws: DhanWebSocket) -> None:
        bids = _make_bid_levels(1)
        asks = _make_ask_levels(1)
        snap = ws._combine_depth_snapshot("100", "NSE_EQ", bids, asks)
        assert isinstance(snap.timestamp, datetime)
        assert snap.timestamp.tzinfo is not None

    def test_combine_level_fields_correct(self, ws: DhanWebSocket) -> None:
        bids = [{"price": 100.5, "quantity": 1000, "orders": 5}]
        asks = [{"price": 101.5, "quantity": 800, "orders": 3}]
        snap = ws._combine_depth_snapshot("100", "NSE_EQ", bids, asks)
        level = snap.levels[0]
        assert level.bid_price == 100.5
        assert level.bid_qty == 1000
        assert level.bid_orders == 5
        assert level.ask_price == 101.5
        assert level.ask_qty == 800
        assert level.ask_orders == 3

    def test_combine_snapshot_security_id_and_exchange(self, ws: DhanWebSocket) -> None:
        bids = _make_bid_levels(2)
        asks = _make_ask_levels(2)
        snap = ws._combine_depth_snapshot("999", "BSE_EQ", bids, asks)
        assert snap.security_id == "999"
        assert snap.exchange == "BSE_EQ"


# ── MarketDepthLevel/MarketDepthSnapshot DTOs ───────────────────────


class TestMarketDepthDTOs:
    def test_market_depth_level_frozen(self) -> None:
        level = MarketDepthLevel(100.0, 1000, 101.0, 800, 5, 3)
        with pytest.raises(AttributeError):
            level.bid_price = 99.0

    def test_market_depth_snapshot_frozen(self) -> None:
        levels = [MarketDepthLevel(100.0, 1000, 101.0, 800, 5, 3)]
        snap = MarketDepthSnapshot("100", "NSE_EQ", datetime.now(timezone.utc), levels)
        with pytest.raises(AttributeError):
            snap.security_id = "200"


# ── Thread safety ───────────────────────────────────────────────────


class TestDepthThreadSafety:
    def test_concurrent_subscribe_unsubscribe_depth_no_crash(self, ws: DhanWebSocket) -> None:
        errors: list[Exception] = []

        def sub_loop():
            try:
                for i in range(50):
                    ws.subscribe_depth([(f"S{i}", "NSE_EQ")])
            except Exception as e:
                errors.append(e)

        def unsub_loop():
            try:
                for i in range(50):
                    ws.unsubscribe_depth([(f"S{i}", "NSE_EQ")])
            except Exception as e:
                errors.append(e)

        t1 = threading.Thread(target=sub_loop, daemon=True)
        t2 = threading.Thread(target=unsub_loop, daemon=True)
        t1.start()
        t2.start()
        t1.join(timeout=5)
        t2.join(timeout=5)
        assert not errors

    def test_concurrent_quote_and_depth_sub_no_crash(self, ws: DhanWebSocket) -> None:
        errors: list[Exception] = []

        def quote_loop():
            try:
                for i in range(50):
                    ws.subscribe([(f"Q{i}", "NSE_EQ")])
            except Exception as e:
                errors.append(e)

        def depth_loop():
            try:
                for i in range(50):
                    ws.subscribe_depth([(f"D{i}", "NSE_EQ")])
            except Exception as e:
                errors.append(e)

        t1 = threading.Thread(target=quote_loop, daemon=True)
        t2 = threading.Thread(target=depth_loop, daemon=True)
        t1.start()
        t2.start()
        t1.join(timeout=5)
        t2.join(timeout=5)
        assert not errors


# ── Depth command queue processing ──────────────────────────────────


class TestDepthCommandQueue:
    def test_process_depth_commands_subscribe(self, ws: DhanWebSocket) -> None:
        feed = MagicMock()
        ws._depth_cmd_queues[20].put({"action": "subscribe", "ids": [("100", "NSE_EQ")]})
        ws._process_depth_commands_sync(feed)
        feed.subscribe_symbols.assert_called_once_with([(1, "100")])

    def test_process_depth_commands_unsubscribe(self, ws: DhanWebSocket) -> None:
        feed = MagicMock()
        ws._depth_cmd_queues[20].put({"action": "unsubscribe", "ids": [("100", "NSE_EQ")]})
        ws._process_depth_commands_sync(feed)
        feed.unsubscribe_symbols.assert_called_once_with([(1, "100")])

    def test_process_depth_commands_empty_queue(self, ws: DhanWebSocket) -> None:
        feed = MagicMock()
        feed.subscribe_symbols.reset_mock()
        ws._process_depth_commands_sync(feed)
        feed.subscribe_symbols.assert_not_called()
        feed.unsubscribe_symbols.assert_not_called()

    def test_process_depth_commands_multiple(self, ws: DhanWebSocket) -> None:
        feed = MagicMock()
        ws._depth_cmd_queues[20].put({"action": "subscribe", "ids": [("100", "NSE_EQ")]})
        ws._depth_cmd_queues[20].put({"action": "subscribe", "ids": [("200", "NSE_FNO")]})
        ws._process_depth_commands_sync(feed)
        assert feed.subscribe_symbols.call_count == 2
        feed.subscribe_symbols.assert_any_call([(1, "100")])
        feed.subscribe_symbols.assert_any_call([(2, "200")])

    def test_subscribe_depth_queues_when_feed_running(self, ws: DhanWebSocket) -> None:
        feed = MagicMock()
        ws._depth_feeds[20] = feed
        ws.subscribe_depth([("100", "NSE_EQ")])
        assert ws._depth_cmd_queues[20].qsize() >= 1
        ws._process_depth_commands_sync(feed)
        feed.subscribe_symbols.assert_called_once_with([(1, "100")])

    def test_unsubscribe_depth_queues_when_feed_running(self, ws: DhanWebSocket) -> None:
        feed = MagicMock()
        ws._depth_feeds[20] = feed
        ws.subscribe_depth([("100", "NSE_EQ")])
        ws._depth_cmd_queues[20].queue.clear()
        ws.unsubscribe_depth([("100", "NSE_EQ")])
        assert ws._depth_cmd_queues[20].qsize() >= 1
        ws._process_depth_commands_sync(feed)
        feed.unsubscribe_symbols.assert_called_once_with([(1, "100")])


# ── Public method contracts ─────────────────────────────────────────


@pytest.mark.parametrize("method,args", [
    ("set_depth_callback", [lambda x: None]),
    ("subscribe_depth", [[("S", "NSE_EQ")]]),
    ("unsubscribe_depth", [[("S", "NSE_EQ")]]),
])
def test_depth_public_methods_return_none(ws: DhanWebSocket, method: str, args: list) -> None:
    result = getattr(ws, method)(*args)
    assert result is None


class TestMarketDepthDf:
    def test_market_depth_df_keeps_unpaired_levels(self) -> None:
        pytest.importorskip("pytz")
        from scalpr.adapters.dhan._market_data_client import MarketDataClient

        raw = {
            "depth": {
                "bid": [
                    {"price": "100", "quantity": 10, "orders": 1},
                    {"price": "99", "quantity": 20, "orders": 2},
                ],
                "ask": [{"price": "101", "quantity": 5, "orders": 1}],
            },
        }
        rows = MarketDataClient._market_depth_df(raw)
        assert len(rows) == 2
        assert rows[1]["bid_price"] == 99.0
        assert rows[1]["ask_price"] is None


# ── _types DTO construction ─────────────────────────────────────────


class TestTypesConstruction:
    def test_market_depth_level_construction(self) -> None:
        level = MarketDepthLevel(
            bid_price=100.0, bid_qty=1000, ask_price=101.0,
            ask_qty=800, bid_orders=5, ask_orders=3,
        )
        assert level.bid_price == 100.0
        assert level.bid_qty == 1000
        assert level.ask_price == 101.0
        assert level.ask_qty == 800
        assert level.bid_orders == 5
        assert level.ask_orders == 3

    def test_market_depth_snapshot_construction(self) -> None:
        levels = [MarketDepthLevel(100.0, 1000, 101.0, 800, 5, 3)]
        ts = datetime.now(timezone.utc)
        snap = MarketDepthSnapshot(
            security_id="100", exchange="NSE_EQ", timestamp=ts, levels=levels,
        )
        assert snap.security_id == "100"
        assert snap.exchange == "NSE_EQ"
        assert snap.timestamp == ts
        assert snap.levels == levels

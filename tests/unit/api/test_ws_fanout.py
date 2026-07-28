"""WS fan-out backpressure — plan Phase 5 (p5-ws).

Verifies the per-client bounded-queue design: a slow client never blocks
the producer or other clients; overflow drops the OLDEST frame
(freshest-data-wins); broadcast respects symbol subscriptions.
"""
from __future__ import annotations

import json

from scalpr.api.ws_manager import ClientChannel, WsFanout, serialize


class TestClientChannel:
    def test_publish_then_next_frame_fifo(self):
        ch = ClientChannel(maxsize=4)
        ch.publish({"type": "tick", "n": 1})
        ch.publish({"type": "tick", "n": 2})
        assert json.loads(ch._queue.get_nowait())["n"] == 1
        assert json.loads(ch._queue.get_nowait())["n"] == 2

    def test_overflow_drops_oldest_keeps_newest(self):
        ch = ClientChannel(maxsize=3)
        for n in range(6):  # 0..5 into a queue of 3
            ch.publish({"n": n})
        got = [json.loads(ch._queue.get_nowait())["n"] for _ in range(3)]
        assert got == [3, 4, 5]  # newest survive, oldest dropped
        assert ch.dropped == 3

    def test_publish_never_blocks(self):
        # put_nowait/get_nowait only — a full queue must not await/hang
        ch = ClientChannel(maxsize=1)
        for n in range(1000):
            ch.publish({"n": n})
        assert ch.dropped == 999
        assert json.loads(ch._queue.get_nowait())["n"] == 999

    async def test_next_frame_delivers(self):
        ch = ClientChannel(maxsize=2)
        ch.publish({"type": "quote"})
        frame = await ch.next_frame()
        assert json.loads(frame)["type"] == "quote"


class TestWsFanout:
    def test_broadcast_reaches_all_clients(self):
        fanout = WsFanout(maxsize=8)
        a, b = fanout.register(), fanout.register()
        fanout.broadcast({"type": "tick"})
        assert a._queue.qsize() == 1
        assert b._queue.qsize() == 1

    def test_symbol_filter_only_hits_subscribers(self):
        fanout = WsFanout(maxsize=8)
        sub = fanout.register()
        sub.subscriptions.add("RELIANCE")
        other = fanout.register()
        other.subscriptions.add("TCS")
        fanout.broadcast({"type": "tick", "symbol": "RELIANCE"}, symbol="RELIANCE")
        assert sub._queue.qsize() == 1
        assert other._queue.qsize() == 0

    def test_slow_client_does_not_affect_fast_client(self):
        fanout = WsFanout(maxsize=2)
        slow, fast = fanout.register(), fanout.register()
        # fast client drains; slow client never reads
        for n in range(10):
            fanout.broadcast({"n": n})
            fast._queue.get_nowait()
        assert fast.dropped == 0
        assert slow.dropped == 8  # kept only the freshest 2 of 10
        kept = [json.loads(slow._queue.get_nowait())["n"] for _ in range(2)]
        assert kept == [8, 9]

    def test_unregister_stops_delivery(self):
        fanout = WsFanout()
        ch = fanout.register()
        fanout.unregister(ch)
        fanout.broadcast({"type": "tick"})
        assert fanout.client_count == 0
        assert ch._queue.qsize() == 0


class TestSerializer:
    def test_compact_json_and_default_str(self):
        from decimal import Decimal
        out = serialize({"type": "pnl", "value": Decimal("12.50")})
        assert out == '{"type":"pnl","value":"12.50"}'  # compact, Decimal→str

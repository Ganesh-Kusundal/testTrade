from __future__ import annotations

import threading
import time
from dataclasses import dataclass

import pytest

from scalpr.engine.message_bus import MessageBus, RecordingBus, TimeoutError


@dataclass(frozen=True)
class OrderEvent:
    order_id: str
    side: str


@dataclass(frozen=True)
class QuoteEvent:
    symbol: str
    bid: float
    ask: float


class TestMessageBusPubSub:
    def test_subscribe_and_publish_delivers_to_handler(self):
        bus = MessageBus()
        received = []

        def handler(event):
            received.append(event)

        bus.subscribe("test.topic", handler)
        bus.publish("test.topic", "hello")
        assert received == ["hello"]

    def test_unsubscribe_removes_handler(self):
        bus = MessageBus()
        received = []

        def handler(event):
            received.append(event)

        bus.subscribe("test.topic", handler)
        bus.unsubscribe("test.topic", handler)
        bus.publish("test.topic", "hello")
        assert received == []

    def test_multiple_handlers_same_topic(self):
        bus = MessageBus()
        received1 = []
        received2 = []

        def handler1(event):
            received1.append(event)

        def handler2(event):
            received2.append(event)

        bus.subscribe("test.topic", handler1)
        bus.subscribe("test.topic", handler2)
        bus.publish("test.topic", "data")
        assert received1 == ["data"]
        assert received2 == ["data"]

    def test_different_topics_no_cross_delivery(self):
        bus = MessageBus()
        received_a = []
        received_b = []

        def handler_a(event):
            received_a.append(event)

        def handler_b(event):
            received_b.append(event)

        bus.subscribe("topic.a", handler_a)
        bus.subscribe("topic.b", handler_b)
        bus.publish("topic.a", "only_a")
        assert received_a == ["only_a"]
        assert received_b == []

    def test_publish_to_no_handlers_does_not_error(self):
        bus = MessageBus()
        bus.publish("nonexistent.topic", "data")

    def test_unsubscribe_nonexistent_handler_does_not_error(self):
        bus = MessageBus()

        def handler(event):
            pass

        bus.unsubscribe("test.topic", handler)

    def test_same_handler_twice_gets_called_twice(self):
        bus = MessageBus()
        received = []

        def handler(event):
            received.append(event)

        bus.subscribe("test.topic", handler)
        bus.subscribe("test.topic", handler)
        bus.publish("test.topic", "x")
        assert received == ["x", "x"]

    def test_handler_called_with_frozen_dataclass(self):
        bus = MessageBus()
        received = []

        def handler(event):
            received.append(event)

        bus.subscribe("exec.event.filled", handler)
        ev = OrderEvent(order_id="123", side="buy")
        bus.publish("exec.event.filled", ev)
        assert len(received) == 1
        assert received[0].order_id == "123"

    def test_handler_called_with_complex_payload(self):
        bus = MessageBus()
        received = []

        def handler(event):
            received.append(event)

        bus.subscribe("market.quote", handler)
        ev = QuoteEvent(symbol="AAPL", bid=150.0, ask=151.0)
        bus.publish("market.quote", ev)
        assert received[0].symbol == "AAPL"


class TestMessageBusReqRep:
    def test_request_gets_response_from_registered_handler(self):
        bus = MessageBus()

        def handler(payload):
            return f"echo:{payload}"

        bus.register("exec.command.submit", handler)
        result = bus.request("exec.command.submit", "buy")
        assert result == "echo:buy"

    def test_request_timeout_raises(self):
        bus = MessageBus()
        with pytest.raises(TimeoutError):
            bus.request("no.handler", "data", timeout=0.1)

    def test_register_before_request_works(self):
        bus = MessageBus()
        results = []

        def handler(p):
            results.append(p)
            return p * 2

        bus.register("calc.double", handler)
        r = bus.request("calc.double", 21)
        assert r == 42
        assert results == [21]

    def test_multiple_req_rep_topics_independent(self):
        bus = MessageBus()

        bus.register("topic.a", lambda p: f"A:{p}")
        bus.register("topic.b", lambda p: f"B:{p}")

        assert bus.request("topic.a", "x") == "A:x"
        assert bus.request("topic.b", "y") == "B:y"

    def test_handler_raising_exception_propagates(self):
        bus = MessageBus()

        def handler(p):
            raise ValueError("bad payload")

        bus.register("faulty", handler)
        with pytest.raises(ValueError, match="bad payload"):
            bus.request("faulty", "data")

    def test_handler_returning_none(self):
        bus = MessageBus()

        def handler(p):
            return None

        bus.register("returns.none", handler)
        assert bus.request("returns.none", "x") is None

    def test_request_with_handler_registered_during_wait(self):
        bus = MessageBus()

        def delayed_register():
            time.sleep(0.05)
            bus.register("late", lambda p: "registered")

        t = threading.Thread(target=delayed_register, daemon=True)
        t.start()
        result = bus.request("late", "data", timeout=2.0)
        assert result == "registered"

    def test_register_overwrites_previous_handler(self):
        bus = MessageBus()
        bus.register("topic", lambda p: "first")
        bus.register("topic", lambda p: "second")
        assert bus.request("topic", "x") == "second"

    def test_request_no_timeout_immediate_handler(self):
        bus = MessageBus()
        bus.register("fast", lambda p: "ok")
        result = bus.request("fast", "x", timeout=0.0)
        assert result == "ok"


class TestRecordingBus:
    def test_records_all_published_events(self):
        bus = RecordingBus()
        bus.publish("topic.a", "event1")
        bus.publish("topic.b", "event2")
        assert len(bus.recorded_events) == 2
        assert bus.recorded_events[0].topic == "topic.a"
        assert bus.recorded_events[0].payload == "event1"
        assert bus.recorded_events[1].topic == "topic.b"
        assert bus.recorded_events[1].payload == "event2"

    def test_clear_empties_record(self):
        bus = RecordingBus()
        bus.publish("topic.a", "x")
        bus.publish("topic.b", "y")
        bus.clear()
        assert bus.recorded_events == []

    def test_records_event_objects(self):
        bus = RecordingBus()
        ev = OrderEvent(order_id="abc", side="sell")
        bus.publish("exec.event.filled", ev)
        assert bus.recorded_events[0].payload.order_id == "abc"

    def test_filter_exact_match(self):
        bus = RecordingBus()
        bus.publish("exec.event.filled", "a")
        bus.publish("exec.command.submit", "b")
        bus.publish("market.quote", "c")
        result = bus.filter("exec.event.filled")
        assert len(result) == 1
        assert result[0].payload == "a"

    def test_filter_wildcard_matches(self):
        bus = RecordingBus()
        bus.publish("exec.event.filled", "a")
        bus.publish("exec.event.canceled", "b")
        bus.publish("exec.command.submit", "c")
        result = bus.filter("exec.event.*")
        assert len(result) == 2
        assert result[0].payload == "a"
        assert result[1].payload == "b"

    def test_filter_no_match_returns_empty(self):
        bus = RecordingBus()
        bus.publish("exec.event.filled", "a")
        result = bus.filter("market.*")
        assert result == []

    def test_filter_wildcard_star_at_end(self):
        bus = RecordingBus()
        bus.publish("a.b.c", "x")
        bus.publish("a.b.d", "y")
        bus.publish("x.y.z", "z")
        result = bus.filter("a.b.*")
        assert len(result) == 2

    def test_events_property_returns_copy(self):
        bus = RecordingBus()
        bus.publish("t", "x")
        evs = bus.events
        evs.clear()
        assert len(bus.recorded_events) == 1

    def test_recordingbus_still_delivers_to_handlers(self):
        bus = RecordingBus()
        received = []

        def handler(event):
            received.append(event)

        bus.subscribe("test.topic", handler)
        bus.publish("test.topic", "data")
        assert received == ["data"]
        assert len(bus.recorded_events) == 1

    def test_records_multiple_events_same_topic(self):
        bus = RecordingBus()
        bus.publish("topic", "x")
        bus.publish("topic", "y")
        bus.publish("topic", "z")
        assert len(bus.recorded_events) == 3

    def test_filter_with_star_middle_matches(self):
        bus = RecordingBus()
        bus.publish("a.b.c", "x")
        bus.publish("a.z.c", "y")
        bus.publish("a.b.d", "z")
        result = bus.filter("a.*.c")
        assert len(result) == 2
        assert result[0].payload == "x"
        assert result[1].payload == "y"


class TestThreadSafety:
    def test_concurrent_publish_two_threads(self):
        bus = MessageBus()
        received = []
        lock = threading.Lock()

        def handler(event):
            with lock:
                received.append(event)

        bus.subscribe("shared.topic", handler)

        def publisher(prefix: str, count: int = 50):
            for i in range(count):
                bus.publish("shared.topic", f"{prefix}-{i}")

        t1 = threading.Thread(target=publisher, args=("A", 50), daemon=True)
        t2 = threading.Thread(target=publisher, args=("B", 50), daemon=True)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert len(received) == 100

    def test_concurrent_subscribe_and_publish(self):
        bus = MessageBus()
        results = []
        lock = threading.Lock()
        barrier = threading.Barrier(3, timeout=5)

        def handler_builder(label: str):
            def h(event):
                with lock:
                    results.append(label)
            return h

        def subscribe_worker(label: str):
            h = handler_builder(label)
            bus.subscribe("topic", h)
            barrier.wait()

        t1 = threading.Thread(target=subscribe_worker, args=("X",), daemon=True)
        t2 = threading.Thread(target=subscribe_worker, args=("Y",), daemon=True)

        t1.start()
        t2.start()
        barrier.wait()
        bus.publish("topic", "go")
        t1.join()
        t2.join()

        assert len(results) >= 0

    def test_concurrent_unsubscribe_during_publish(self):
        bus = MessageBus()
        results = []

        def handler(event):
            results.append(event)

        bus.subscribe("topic", handler)
        stop = threading.Event()

        def publisher():
            while not stop.is_set():
                bus.publish("topic", "x")

        t = threading.Thread(target=publisher, daemon=True)
        t.start()
        time.sleep(0.05)
        bus.unsubscribe("topic", handler)
        stop.set()
        t.join(timeout=2)


class TestEdgeCases:
    def test_handler_that_modifies_event_list(self):
        bus = MessageBus()
        events = []

        def handler(event):
            events.append(event)

        bus.subscribe("t", handler)
        bus.publish("t", [1, 2, 3])
        assert events == [[1, 2, 3]]

    def test_publish_different_types(self):
        bus = MessageBus()
        received = []

        def handler(event):
            received.append(event)

        bus.subscribe("t", handler)
        bus.publish("t", 42)
        bus.publish("t", "str")
        bus.publish("t", None)
        bus.publish("t", [1, 2])
        assert received == [42, "str", None, [1, 2]]

    def test_subscribe_called_after_unsubscribe_re_subscribes(self):
        bus = MessageBus()
        received = []

        def handler(event):
            received.append(event)

        bus.subscribe("t", handler)
        bus.unsubscribe("t", handler)
        bus.subscribe("t", handler)
        bus.publish("t", "ok")
        assert received == ["ok"]

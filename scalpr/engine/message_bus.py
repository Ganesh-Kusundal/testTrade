from __future__ import annotations

import threading
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, NamedTuple


@dataclass(frozen=True)
class Event:
    topic: str
    payload: Any


class TimeoutError(Exception):
    pass


class MessageBus:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._subscribers: dict[str, list[Callable[[Any], None]]] = defaultdict(list)
        self._req_handlers: dict[str, Callable[[Any], Any]] = {}
        self._req_events: dict[str, threading.Event] = {}
        self._req_responses: dict[str, Any] = {}

    # Pub/Sub

    def subscribe(self, topic: str, handler: Callable[[Any], None]) -> None:
        with self._lock:
            self._subscribers[topic].append(handler)

    def unsubscribe(self, topic: str, handler: Callable[[Any], None]) -> None:
        with self._lock:
            handlers = self._subscribers.get(topic, [])
            if handler in handlers:
                handlers.remove(handler)

    def publish(self, topic: str, event: Any) -> None:
        with self._lock:
            targets = list(self._subscribers.get(topic, []))
        for handler in targets:
            handler(event)

    # Req/Rep

    def register(self, topic: str, handler: Callable[[Any], Any]) -> None:
        with self._lock:
            self._req_handlers[topic] = handler
            ev = self._req_events.get(topic)
            if ev is not None:
                ev.set()

    def request(self, topic: str, payload: Any, timeout: float = 5.0) -> Any:
        handler = self._req_handlers.get(topic)
        if handler is not None:
            return handler(payload)

        ev = threading.Event()
        with self._lock:
            self._req_events[topic] = ev
            handler = self._req_handlers.get(topic)
            if handler is not None:
                return handler(payload)
        ev.wait(timeout=timeout)
        if not ev.is_set():
            raise TimeoutError(f"No handler registered for '{topic}' within {timeout}s")
        handler = self._req_handlers.get(topic)
        if handler is None:
            raise TimeoutError(f"No handler registered for '{topic}'")
        return handler(payload)


class RecordedEvent(NamedTuple):
    topic: str
    payload: Any


class RecordingBus(MessageBus):
    def __init__(self) -> None:
        super().__init__()
        self.recorded_events: list[RecordedEvent] = []

    def publish(self, topic: str, event: Any) -> None:
        self.recorded_events.append(RecordedEvent(topic, event))
        super().publish(topic, event)

    def clear(self) -> None:
        self.recorded_events.clear()

    @property
    def events(self) -> list[RecordedEvent]:
        return list(self.recorded_events)

    def filter(self, topic_pattern: str) -> list[RecordedEvent]:
        parts = topic_pattern.split(".")
        result = []
        for rec in self.recorded_events:
            rec_parts = rec.topic.split(".")
            if len(parts) != len(rec_parts):
                continue
            match = True
            for p, rp in zip(parts, rec_parts, strict=False):
                if p != "*" and p != rp:
                    match = False
                    break
            if match:
                result.append(rec)
        return result

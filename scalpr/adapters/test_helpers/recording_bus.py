from __future__ import annotations

from collections.abc import Callable
from typing import Any

from scalpr.engine.message_bus import MessageBus


class RecordingBus:
    def __init__(self, bus: MessageBus | None = None) -> None:
        self._bus = bus or MessageBus()
        self._recorded: list[tuple[str, Any]] = []

    @property
    def recorded_events(self) -> list[tuple[str, Any]]:
        return list(self._recorded)

    def events_for(self, topic_pattern: str) -> list[Any]:
        parts = topic_pattern.split(".")
        result = []
        for topic, payload in self._recorded:
            rec_parts = topic.split(".")
            if len(parts) != len(rec_parts):
                continue
            match = True
            for p, rp in zip(parts, rec_parts, strict=False):
                if p != "*" and p != rp:
                    match = False
                    break
            if match:
                result.append(payload)
        return result

    def clear(self) -> None:
        self._recorded.clear()

    def subscribe(self, topic: str, handler: Callable[[Any], None]) -> None:
        self._recorded.append(("subscribe", (topic, handler)))
        self._bus.subscribe(topic, handler)

    def publish(self, topic: str, event: Any) -> None:
        self._recorded.append((topic, event))
        self._bus.publish(topic, event)

    def request(self, topic: str, payload: Any, timeout: float = 5.0) -> Any:
        self._recorded.append(("request", (topic, payload)))
        return self._bus.request(topic, payload, timeout=timeout)

    def register(self, topic: str, handler: Callable[[Any], Any]) -> None:
        self._recorded.append(("register", (topic, handler)))
        self._bus.register(topic, handler)

    @property
    def bus(self) -> MessageBus:
        return self._bus

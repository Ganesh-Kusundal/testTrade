"""WebSocket fan-out manager — per-client bounded queues, drop-oldest.

One serializer for market AND replay streams (plan Task 7: "replay ≡ live
streaming"). A slow client never blocks the producer or other clients:
each client has its own bounded asyncio.Queue; when full, the OLDEST
message is dropped to make room (freshest-data-wins for market ticks).
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_QUEUE_SIZE = 256


def serialize(message: dict[str, Any]) -> str:
    """The single WS serializer — both /ws/market and /ws/replay use it."""
    return json.dumps(message, separators=(",", ":"), default=str)


class ClientChannel:
    """A single client's bounded outbound queue with drop-oldest overflow."""

    def __init__(self, maxsize: int = DEFAULT_QUEUE_SIZE) -> None:
        self._queue: asyncio.Queue[str] = asyncio.Queue(maxsize=maxsize)
        self.dropped = 0
        self.subscriptions: set[str] = set()

    def publish(self, message: dict[str, Any]) -> None:
        """Enqueue for this client; drop the oldest frame if the queue is full."""
        payload = serialize(message)
        while True:
            try:
                self._queue.put_nowait(payload)
                return
            except asyncio.QueueFull:
                try:
                    self._queue.get_nowait()
                    self.dropped += 1
                except asyncio.QueueEmpty:  # pragma: no cover - race window
                    pass

    async def next_frame(self) -> str:
        return await self._queue.get()


class WsFanout:
    """Registry of connected clients for one stream (market or a replay session)."""

    def __init__(self, maxsize: int = DEFAULT_QUEUE_SIZE) -> None:
        self._maxsize = maxsize
        self._clients: set[ClientChannel] = set()

    def register(self) -> ClientChannel:
        channel = ClientChannel(maxsize=self._maxsize)
        self._clients.add(channel)
        return channel

    def unregister(self, channel: ClientChannel) -> None:
        self._clients.discard(channel)

    @property
    def client_count(self) -> int:
        return len(self._clients)

    def broadcast(self, message: dict[str, Any], symbol: str | None = None) -> None:
        """Send to every client; if symbol given, only to clients subscribed to it."""
        for channel in self._clients:
            if symbol is not None and symbol not in channel.subscriptions:
                continue
            channel.publish(message)

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from scalpr.domain.tick import Tick
from scalpr.market_data.feed_port import IMarketDataFeed

logger = logging.getLogger(__name__)


class DhanMarketFeed(IMarketDataFeed):
    """WebSocket feed client for streaming real-time ticks from DhanHQ."""

    def __init__(self, client_id: str, access_token: str, buffer_size: int = 10000):
        self.client_id = client_id
        self.access_token = access_token
        self.queue: asyncio.Queue[Tick] = asyncio.Queue(maxsize=buffer_size)
        self._connected = False
        self._callback: Callable[[Tick], None] | None = None
        self._cumulative_vols: dict[str, int] = {}
        self._running = False
        self._loop_task: asyncio.Task[None] | None = None

    def connect(self) -> bool:
        self._connected = True
        self._running = True
        # In a real system, this starts websocket client task
        self._loop_task = asyncio.create_task(self._process_queue_loop())
        return True

    def disconnect(self) -> bool:
        self._connected = False
        self._running = False
        if self._loop_task:
            self._loop_task.cancel()
        return True

    def subscribe(self, symbols: list[str]) -> bool:
        logger.info(f"Subscribed to WebSocket feed for symbols: {symbols}")
        return True

    def unsubscribe(self, symbols: list[str]) -> bool:
        logger.info(f"Unsubscribed from WebSocket feed for symbols: {symbols}")
        return True

    def is_connected(self) -> bool:
        return self._connected

    def on_tick(self, callback: Callable[[Tick], None]) -> None:
        self._callback = callback

    def parse_raw_message(self, msg: dict[str, Any]) -> Tick | None:
        """Parse raw WS packet into domain Tick, calculating delta volume."""
        try:
            symbol = msg.get("symbol", "")
            if not symbol:
                return None

            ltp = Decimal(str(msg.get("ltp", "0")))
            bid = Decimal(str(msg.get("bid", "0")))
            ask = Decimal(str(msg.get("ask", "0")))
            cum_vol = int(msg.get("volume", 0))

            # Volume calculation: delta_volume = cum_vol - prev_vol
            prev_vol = self._cumulative_vols.get(symbol, cum_vol)
            delta_vol = max(0, cum_vol - prev_vol)
            self._cumulative_vols[symbol] = cum_vol

            exchange_ts_epoch = msg.get("timestamp", time.time())
            exchange_ts = datetime.fromtimestamp(exchange_ts_epoch, tz=timezone.utc)

            tick = Tick(
                symbol=symbol,
                ltp=ltp,
                bid=bid,
                ask=ask,
                delta_volume=delta_vol,
                cumulative_volume=cum_vol,
                exchange_timestamp=exchange_ts,
            )
            return tick
        except Exception as exc:
            logger.debug(f"Failed to parse raw tick: {exc}")
            return None

    async def put_tick(self, raw_msg: dict[str, Any]) -> bool:
        """Put raw message into the queue (with backpressure safety)."""
        tick = self.parse_raw_message(raw_msg)
        if tick is None:
            return False

        try:
            # Non-blocking put with max queue limit check
            self.queue.put_nowait(tick)
            return True
        except asyncio.QueueFull:
            logger.warning("Tick feed queue is full. Dropping tick.")
            return False

    async def _process_queue_loop(self) -> None:
        """Queue consumer loop that calls the tick callback."""
        while self._running:
            try:
                tick = await self.queue.get()
                if self._callback:
                    try:
                        self._callback(tick)
                    except Exception as exc:
                        logger.error(f"Error in tick callback: {exc}")
                self.queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error(f"Error in tick queue consumer: {exc}")
                await asyncio.sleep(0.1)

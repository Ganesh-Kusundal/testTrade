from __future__ import annotations

import asyncio
import enum
import logging
import queue
import threading
from collections.abc import Callable
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from scalpr.adapters.dhan._resolver import (
    full_depth_numeric_to_wire_segment,
    full_depth_sdk_pairs,
    market_feed_mode_int,
    market_feed_sdk_tuples,
    wire_segment_to_full_depth_numeric,
)
from scalpr.domain.tick import Tick
from scalpr.domain.values import ZERO
from scalpr.engine.clock import Clock, LiveClock

logger = logging.getLogger(__name__)

DEPTH_20_LIMIT = 100
DEPTH_200_LIMIT = 50
DEPTH_WARN_THRESHOLD = 0.8
_DEPTH_20_URL = "wss://depth-api-feed.dhan.co/twentydepth"
_DEPTH_200_URL = "wss://full-depth-api.dhan.co/"


class WSState(enum.Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    DISCONNECTED_PERMANENT = "disconnected_permanent"


# ── SDK helpers ──────────────────────────────────────────────────────


def _sdk_market_feed_class() -> type:
    """Return the dhanhq MarketFeed class (v2.2+ only).

    dhanhq < 2.2 is unsupported — the legacy DhanFeed subpackage fallback is
    removed; pin dhanhq>=2.2,<2.3 in pyproject.toml.
    """
    from dhanhq import MarketFeed
    return MarketFeed


def _sdk_mode_int(mode: str) -> int:
    return market_feed_mode_int(mode)


def _full_depth_class() -> type:
    """Return the dhanhq FullDepth class (v2.2+ top-level only)."""
    from dhanhq import FullDepth
    return FullDepth


def _get_dhan_context(client_id: str, access_token: str) -> Any:
    """Return a DhanContext instance (dhanhq >= 2.2 required)."""
    from dhanhq import DhanContext
    return DhanContext(client_id, access_token)


# ── DhanWebSocket ────────────────────────────────────────────────────


class DhanWebSocket:
    """WebSocket client for Dhan market data with FSM-based reconnection.

    Manages three independent WebSocket feeds:
        - Quote/tick feed via ``dhanhq.MarketFeed``
        - 20-level depth feed via ``dhanhq.FullDepth``
        - 200-level depth feed via ``dhanhq.FullDepth``

    FSM transitions (quote feed):
        DISCONNECTED -> connect() -> CONNECTING
        CONNECTING   -> handshake  -> CONNECTED
        CONNECTING   -> error      -> DISCONNECTED  (retry_count reset)
        CONNECTED    -> close/error -> RECONNECTING
        RECONNECTING -> backoff    -> CONNECTING
        RECONNECTING -> MAX_RETRIES -> DISCONNECTED_PERMANENT
        DISCONNECTED_PERMANENT -> connect() -> DISCONNECTED -> CONNECTING
    """

    BACKOFF: list[float] = [1.0, 2.0, 4.0, 8.0, 16.0, 30.0]  # noqa: RUF012
    MAX_RETRIES: int = 5
    MAX_SUBSCRIBERS: int = 1000
    _SUBSCRIBER_WARN_THRESHOLD: float = 0.85
    _DEPTH_RECV_TIMEOUT: float = 0.5

    def __init__(
        self,
        access_token: str,
        client_id: str,
        on_tick: Callable | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._access_token = access_token
        self._client_id = client_id
        self._on_tick = on_tick
        self._clock = clock or LiveClock()

        self._state = WSState.DISCONNECTED
        self._lock = threading.Lock()
        self._subscriptions: set[tuple[str, str]] = set()
        self._retry_count = 0

        self._feed: Any = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._cumulative_vols: dict[str, int] = {}

        self._depth_subscriptions: dict[int, set[tuple[str, str]]] = {20: set(), 200: set()}
        self._depth_feeds: dict[int, Any] = {}
        self._depth_threads: dict[int, threading.Thread] = {}
        self._depth_stops: dict[int, threading.Event] = {}
        self._on_depth_tick: Callable | None = None
        self._depth_cmd_queues: dict[int, queue.Queue] = {20: queue.Queue(), 200: queue.Queue()}
        self._depth_feed_readys: dict[int, threading.Event] = {}
        self._depth_cache: dict[str, Any] = {}  # latest depth snapshot per instrument

    # ── Public API: quote/tick ──────────────────────────────────────

    @property
    def state(self) -> WSState:
        with self._lock:
            return self._state

    @property
    def subscription_count(self) -> int:
        return len(self._subscriptions)

    @property
    def subscription_capacity_remaining(self) -> int:
        return self.MAX_SUBSCRIBERS - self.subscription_count

    @property
    def depth_subscription_count(self) -> int:
        return sum(len(v) for v in self._depth_subscriptions.values())

    @property
    def depth_subscription_count_20(self) -> int:
        return len(self._depth_subscriptions.get(20, set()))

    @property
    def depth_subscription_count_200(self) -> int:
        return len(self._depth_subscriptions.get(200, set()))

    @property
    def depth_capacity_remaining_20(self) -> int:
        return DEPTH_20_LIMIT - len(self._depth_subscriptions.get(20, set()))

    @property
    def depth_capacity_remaining_200(self) -> int:
        return DEPTH_200_LIMIT - len(self._depth_subscriptions.get(200, set()))

    def set_tick_callback(self, callback: Callable) -> None:
        self._on_tick = callback

    def connect(self) -> None:
        with self._lock:
            if self._state == WSState.DISCONNECTED_PERMANENT:
                self._retry_count = 0
                self._state = WSState.DISCONNECTED
            if self._state != WSState.DISCONNECTED:
                return
            self._state = WSState.CONNECTING

        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="dhan-ws")
        self._thread.start()

    def disconnect(self) -> None:
        with self._lock:
            self._state = WSState.DISCONNECTED
        self._stop.set()
        self._stop_depth_feed()
        if self._feed is not None:
            try:
                self._feed.close_connection()
            except Exception:
                logger.debug("ws_cleanup_failed", exc_info=True)

    def subscribe(self, security_ids: list[tuple[str, str]], mode: str = "quote") -> None:
        new_count = len(self._subscriptions) + len(security_ids)
        if new_count > self.MAX_SUBSCRIBERS:
            raise ValueError(f"Cannot subscribe {new_count} instruments (max {self.MAX_SUBSCRIBERS})")
        if len(self._subscriptions) >= self.MAX_SUBSCRIBERS * self._SUBSCRIBER_WARN_THRESHOLD:
            logger.warning("subscription_count_approaching_limit: %d/%d", new_count, self.MAX_SUBSCRIBERS)

        with self._lock:
            self._subscriptions.update(security_ids)

        if self.state == WSState.CONNECTED and self._feed is not None:
            instruments = self._to_sdk_instruments(security_ids, mode)
            try:
                self._feed.subscribe_symbols(instruments)
            except Exception as exc:
                logger.warning("subscribe_failed: %s", exc)

    def unsubscribe(self, security_ids: list[tuple[str, str]]) -> None:
        with self._lock:
            self._subscriptions.difference_update(security_ids)

        if self.state == WSState.CONNECTED and self._feed is not None:
            instruments = self._to_sdk_instruments(security_ids)
            try:
                self._feed.unsubscribe_symbols(instruments)
            except Exception as exc:
                logger.warning("unsubscribe_failed: %s", exc)

    # ── Public API: depth ───────────────────────────────────────────

    def set_depth_callback(self, callback: Callable) -> None:
        self._on_depth_tick = callback

    def subscribe_depth(self, security_ids: list[tuple[str, str]], level: int = 20) -> None:
        if level not in (20, 200):
            raise ValueError(f"Depth level must be 20 or 200, got {level}")

        # Validate segments up-front: FullDepth is NSE equity/F&O only.
        for _sid, seg in security_ids:
            wire_segment_to_full_depth_numeric(seg)

        current = len(self._depth_subscriptions[level])
        limit = DEPTH_20_LIMIT if level == 20 else DEPTH_200_LIMIT
        new_count = current + len(security_ids)
        if new_count > limit:
            raise ValueError(f"Cannot subscribe {new_count} instruments to {level}-depth (max {limit})")
        if current >= limit * DEPTH_WARN_THRESHOLD:
            logger.warning("depth_subscription_approaching_limit: level=%d %d/%d", level, current, limit)

        with self._lock:
            self._depth_subscriptions[level].update(security_ids)

        feed = self._depth_feeds.get(level)
        if feed is not None:
            self._depth_cmd_queues[level].put({"action": "subscribe", "ids": security_ids})
        elif self.state == WSState.CONNECTED:
            self._start_depth_feed(level=level)

    def unsubscribe_depth(self, security_ids: list[tuple[str, str]], level: int = 20) -> None:
        if level not in (20, 200):
            raise ValueError(f"Depth level must be 20 or 200, got {level}")

        with self._lock:
            self._depth_subscriptions[level].difference_update(security_ids)

        feed = self._depth_feeds.get(level)
        if feed is not None:
            self._depth_cmd_queues[level].put({"action": "unsubscribe", "ids": security_ids})

    # ── Background thread (quote feed reconnect loop) ───────────────

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self._run_feed()
            except Exception as exc:
                logger.exception("feed_error: %s", exc)

            if self._stop.is_set():
                break

            delay = self._next_reconnect_delay()
            if delay is None:
                break

            logger.info(
                "reconnecting in %.1fs (attempt %d/%d)",
                delay,
                self._retry_count,
                self.MAX_RETRIES,
            )
            self._stop.wait(delay)

            with self._lock:
                if self._state == WSState.RECONNECTING:
                    self._state = WSState.CONNECTING

    def _run_feed(self) -> None:
        MarketFeed = _sdk_market_feed_class()
        context = _get_dhan_context(self._client_id, self._access_token)
        with self._lock:
            instruments = self._all_sdk_instruments()

        feed = MarketFeed(
            dhan_context=context,
            instruments=instruments,
            version="v2",
            on_connect=self._on_connect,
            on_message=self._on_message,
            on_close=self._on_close,
            on_error=self._on_error,
        )
        self._feed = feed
        feed.run()
        self._feed = None

    def _next_reconnect_delay(self) -> float | None:
        with self._lock:
            if self._state == WSState.CONNECTING:
                self._state = WSState.DISCONNECTED
                self._retry_count = 0
                return None
            if self._state == WSState.RECONNECTING:
                if self._retry_count >= self.MAX_RETRIES:
                    self._state = WSState.DISCONNECTED_PERMANENT
                    return None
                idx = min(self._retry_count, len(self.BACKOFF) - 1)
                delay = self.BACKOFF[idx]
                self._retry_count += 1
                return delay
            return None

    # ── SDK callbacks (quote feed) ──────────────────────────────────

    def _on_connect(self, feed: Any) -> None:
        with self._lock:
            self._state = WSState.CONNECTED
            self._retry_count = 0
        self._resubscribe(feed)
        for level in (20, 200):
            with self._lock:
                has_subs = bool(self._depth_subscriptions.get(level))
            if has_subs:
                self._start_depth_feed(level=level)

    def _on_message(self, feed: Any, data: dict[str, Any]) -> None:
        if not data:
            return
        dtype = data.get("type", "")
        if dtype not in ("Ticker Data", "Quote Data", "Full Data"):
            return
        tick = self._parse_sdk_data(data)
        if tick and self._on_tick:
            try:
                self._on_tick(tick)
            except Exception as exc:
                logger.warning("tick_cb_error: %s", exc)

    def _on_close(self, feed: Any) -> None:
        with self._lock:
            if self._state == WSState.CONNECTED:
                self._state = WSState.RECONNECTING

    def _on_error(self, feed: Any, error: Any) -> None:
        logger.error("sdk_error: %s", error)
        with self._lock:
            if self._state == WSState.CONNECTED:
                self._state = WSState.RECONNECTING

    # ── Subscription helpers (quote feed) ───────────────────────────

    def _resubscribe(self, feed: Any) -> None:
        with self._lock:
            if not self._subscriptions:
                return
            instruments = self._all_sdk_instruments()
        try:
            feed.subscribe_symbols(instruments)
        except Exception as exc:
            logger.warning("resubscribe_failed: %s", exc)

    def _all_sdk_instruments(self) -> list[tuple[int, str, int]]:
        return market_feed_sdk_tuples(
            list(self._subscriptions), _sdk_mode_int("quote"),
        )

    @staticmethod
    def _to_sdk_instruments(
        security_ids: list[tuple[str, str]], mode: str = "quote",
    ) -> list[tuple[int, str, int]]:
        return market_feed_sdk_tuples(security_ids, _sdk_mode_int(mode))

    # ── Tick parsing ────────────────────────────────────────────────

    def _parse_sdk_data(self, data: dict[str, Any]) -> Tick | None:
        try:
            sid = data.get("security_id")
            if sid is None:
                return None
            symbol = str(sid)

            ltp = Decimal(str(data.get("LTP", "0")))

            depth = data.get("depth") or []
            if depth:
                bid = Decimal(str(depth[0].get("bid_price", "0")))
                ask = Decimal(str(depth[0].get("ask_price", "0")))
            else:
                bid = ask = ZERO

            raw_vol = data.get("volume", 0)
            cum_vol = int(raw_vol) if raw_vol is not None else 0
            prev_vol = self._cumulative_vols.get(symbol, cum_vol)
            delta_vol = max(0, cum_vol - prev_vol)
            self._cumulative_vols[symbol] = cum_vol

            return Tick(
                symbol=symbol,
                ltp=ltp,
                bid=bid,
                ask=ask,
                delta_volume=delta_vol,
                cumulative_volume=cum_vol,
                exchange_timestamp=datetime.now(timezone.utc),
            )
        except (ValueError, TypeError, KeyError) as exc:
            logger.debug("tick_parse_error: %s", exc)
            return None

    # ── Depth feed lifecycle ─────────────────────────────────────────

    def _start_depth_feed(self, level: int = 20) -> None:
        thread = self._depth_threads.get(level)
        if thread is not None and thread.is_alive():
            return
        with self._lock:
            if not self._depth_subscriptions.get(level):
                return
        stop_event = self._depth_stops.setdefault(level, threading.Event())
        stop_event.clear()
        ready = self._depth_feed_readys.setdefault(level, threading.Event())
        ready.clear()
        thread = threading.Thread(
            target=self._run_depth_feed, args=(level,), daemon=True, name=f"dhan-depth-{level}",
        )
        self._depth_threads[level] = thread
        thread.start()
        if not ready.wait(timeout=5):
            logger.warning("depth_feed_not_ready: level=%d", level)

    def _stop_depth_feed(self, level: int | None = None) -> None:
        levels = [level] if level is not None else list(self._depth_feeds.keys())
        for lvl in levels:
            stop = self._depth_stops.get(lvl)
            if stop:
                stop.set()
            feed = self._depth_feeds.pop(lvl, None)
            if feed:
                try:
                    feed.close_connection()
                except Exception:
                    logger.debug("ws_cleanup_failed", exc_info=True)
            thread = self._depth_threads.pop(lvl, None)
            if thread:
                thread.join(timeout=3)

    def _run_depth_feed(self, level: int = 20) -> None:
        FullDepth = _full_depth_class()
        try:
            with self._lock:
                instruments = list(self._depth_subscriptions.get(level, set()))
            if not instruments:
                return
            sdk_instruments = self._to_depth_sdk_instruments(instruments)
            context = _get_dhan_context(self._client_id, self._access_token)
            feed = FullDepth(
                dhan_context=context, instruments=sdk_instruments, depth_level=level,
            )
            self._depth_feeds[level] = feed
            ready = self._depth_feed_readys.get(level)
            if ready:
                ready.set()
            loop = feed.loop
            loop.run_until_complete(feed.connect())
            loop.run_until_complete(self._depth_recv_loop(feed, level=level))
        except BaseException:
            logger.exception("depth_feed_crashed: level=%d", level)
            self._depth_feeds.pop(level, None)
            raise
        finally:
            ready = self._depth_feed_readys.get(level)
            if ready and not ready.is_set():
                ready.set()

    async def _depth_recv_loop(self, feed: Any, level: int = 20) -> None:
        self._process_depth_commands_sync(feed, level=level)
        buffer: dict[str, dict[str, list[dict]]] = {}
        stop = self._depth_stops.get(level)
        while stop is not None and not stop.is_set():
            try:
                raw = await asyncio.wait_for(feed.ws.recv(), timeout=self._DEPTH_RECV_TIMEOUT)
            except asyncio.TimeoutError:
                self._process_depth_commands_sync(feed, level=level)
                continue
            except Exception:
                break
            remaining = raw
            while remaining:
                update = feed.process_data(remaining)
                if not update:
                    break
                remaining = update.pop("remaining_data", None)
                self._accumulate_depth_update(buffer, update)

    def _accumulate_depth_update(self, buffer: dict, update: dict) -> None:
        sec_id = str(update["security_id"])
        ex_code = update.get("exchange_segment", 1)
        ex_seg = full_depth_numeric_to_wire_segment(int(ex_code))
        depth_type = update["type"]
        levels = update["depth"]

        key = f"{ex_seg}:{sec_id}"
        entry = buffer.setdefault(key, {})
        entry[depth_type.lower()] = levels

        if "bid" in entry and "ask" in entry:
            snapshot = self._combine_depth_snapshot(
                sec_id, ex_seg, entry["bid"], entry["ask"],
            )
            cache_key = f"{ex_seg}:{sec_id}"
            self._depth_cache[cache_key] = snapshot
            if self._on_depth_tick:
                try:
                    self._on_depth_tick(snapshot)
                except Exception as exc:
                    logger.warning("depth_cb_error: %s", exc)
            buffer.pop(key, None)

    def _process_depth_commands_sync(self, feed: Any, level: int = 20) -> None:
        queue = self._depth_cmd_queues.get(level)
        if queue is None:
            return
        while not queue.empty():
            try:
                cmd = queue.get_nowait()
                ids = cmd["ids"]
                sdk_ids = full_depth_sdk_pairs(ids)
                if cmd["action"] == "subscribe":
                    feed.subscribe_symbols(sdk_ids)
                elif cmd["action"] == "unsubscribe":
                    feed.unsubscribe_symbols(sdk_ids)
            except queue.Empty:
                break

    # ── Depth data helpers ───────────────────────────────────────────

    @staticmethod
    def _to_depth_sdk_instruments(
        security_ids: list[tuple[str, str]],
    ) -> list[tuple[int, str]]:
        return full_depth_sdk_pairs(security_ids)

    def get_depth_snapshot(self, security_id: str, exchange: str) -> Any | None:
        """Return the latest cached depth snapshot for an instrument, or None."""
        key = f"{exchange}:{security_id}"
        return self._depth_cache.get(key)

    def is_depth_subscribed(self, security_id: str, exchange: str) -> bool:
        """Check if an instrument is subscribed to the depth feed."""
        return (security_id, exchange) in self._depth_subscriptions.get(20, set())

    def _combine_depth_snapshot(
        self, security_id: str, exchange: str,
        bid_levels: list[dict], ask_levels: list[dict],
    ) -> Any:
        from scalpr.adapters.dhan._types import MarketDepthLevel, MarketDepthSnapshot

        bid_sorted = sorted(bid_levels, key=lambda x: x["price"], reverse=True)
        ask_sorted = sorted(ask_levels, key=lambda x: x["price"])

        levels: list[MarketDepthLevel] = []
        min_len = min(len(bid_sorted), len(ask_sorted))

        for i in range(min_len):
            b = bid_sorted[i]
            a = ask_sorted[i]
            levels.append(MarketDepthLevel(
                bid_price=Decimal(str(b["price"])),
                bid_qty=int(b["quantity"]),
                ask_price=Decimal(str(a["price"])),
                ask_qty=int(a["quantity"]),
                bid_orders=int(b["orders"]),
                ask_orders=int(a["orders"]),
            ))

        return MarketDepthSnapshot(
            security_id=security_id,
            exchange=exchange,
            timestamp=datetime.now(timezone.utc),
            levels=levels,
        )

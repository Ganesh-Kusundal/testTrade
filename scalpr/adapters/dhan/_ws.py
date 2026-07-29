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

from scalpr.domain.tick import Tick
from scalpr.domain.values import ZERO
from scalpr.engine.clock import Clock, LiveClock

logger = logging.getLogger(__name__)

WS_URL = "wss://ws.dhan.co/marketfeed"

_WIRE_SEGMENT_TO_EXCH_CODE: dict[str, int] = {
    "NSE_EQ": 1,
    "NSE_FNO": 2,
    "BSE_EQ": 3,
    "BSE_FNO": 4,
    "MCX_EQ": 5,
    "MCX_COMM": 5,
    "IDX_I": 1,
    "NSE": 1,
    "BSE": 3,
}

_EXCH_CODE_TO_SEGMENT: dict[int, str] = {
    1: "NSE_EQ",
    2: "NSE_FNO",
    3: "BSE_EQ",
    4: "BSE_FNO",
    5: "MCX",
}


class WSState(enum.Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    DISCONNECTED_PERMANENT = "disconnected_permanent"


# ── SDK helpers ──────────────────────────────────────────────────────


def _sdk_market_feed_class() -> type:
    try:
        from dhanhq.marketfeed import MarketFeed
        return MarketFeed
    except ImportError:
        from dhanhq.marketfeed import DhanFeed
        return DhanFeed


def _sdk_mode_int(mode: str) -> int:
    TICKER, QUOTE, FULL = 15, 17, 21
    try:
        fcls = _sdk_market_feed_class()
        TICKER, QUOTE, FULL = fcls.Ticker, fcls.Quote, fcls.Full
    except (ImportError, AttributeError):
        pass
    return {"ltp": TICKER, "quote": QUOTE, "depth": QUOTE, "full": FULL}.get(mode, QUOTE)


class _DhanContextShim:
    def __init__(self, client_id: str, access_token: str) -> None:
        self._client_id = client_id
        self._access_token = access_token

    def get_client_id(self) -> str:
        return self._client_id

    def get_access_token(self) -> str:
        return self._access_token

    def get_dhan_http(self) -> None:
        return None

    def update_token(self, token: str) -> None:
        self._access_token = token


# ── DhanWebSocket ────────────────────────────────────────────────────


class DhanWebSocket:
    """WebSocket client for Dhan market data with FSM-based reconnection.

    Manages two independent WebSocket feeds:
        - Quote/tick feed via ``dhanhq.marketfeed.MarketFeed``
        - Market depth feed via ``dhanhq.fulldepth.FullDepth``

    FSM transitions (quote feed):
        DISCONNECTED -> connect() -> CONNECTING
        CONNECTING   -> handshake  -> CONNECTED
        CONNECTING   -> error      -> DISCONNECTED  (retry_count reset)
        CONNECTED    -> close/error -> RECONNECTING
        RECONNECTING -> backoff    -> CONNECTING
        RECONNECTING -> MAX_RETRIES -> DISCONNECTED_PERMANENT
        DISCONNECTED_PERMANENT -> connect() -> DISCONNECTED -> CONNECTING
    """

    BACKOFF: list[float] = [1.0, 2.0, 4.0, 8.0, 16.0, 30.0]
    MAX_RETRIES: int = 5
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

        self._depth_subscriptions: set[tuple[str, str]] = set()
        self._depth_feed: Any = None
        self._depth_thread: threading.Thread | None = None
        self._depth_stop = threading.Event()
        self._on_depth_tick: Callable | None = None
        self._depth_cmd_queue: queue.Queue = queue.Queue()
        self._depth_feed_ready: threading.Event | None = None

    # ── Public API: quote/tick ──────────────────────────────────────

    @property
    def state(self) -> WSState:
        with self._lock:
            return self._state

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
                pass

    def subscribe(self, security_ids: list[tuple[str, str]], mode: str = "quote") -> None:
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

    def subscribe_depth(self, security_ids: list[tuple[str, str]]) -> None:
        with self._lock:
            self._depth_subscriptions.update(security_ids)

        if self._depth_feed is not None:
            sdk_ids = self._to_depth_sdk_instruments(security_ids)
            self._depth_cmd_queue.put({"action": "subscribe", "ids": sdk_ids})
        else:
            with self._lock:
                state = self._state
            if state == WSState.CONNECTED:
                self._start_depth_feed()

    def unsubscribe_depth(self, security_ids: list[tuple[str, str]]) -> None:
        with self._lock:
            self._depth_subscriptions.difference_update(security_ids)

        if self._depth_feed is not None:
            sdk_ids = self._to_depth_sdk_instruments(security_ids)
            self._depth_cmd_queue.put({"action": "unsubscribe", "ids": sdk_ids})

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
        context = _DhanContextShim(self._client_id, self._access_token)
        with self._lock:
            instruments = self._all_sdk_instruments()

        feed = MarketFeed(
            dhan_context=context,
            instruments=instruments,
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
        with self._lock:
            has_depth_subs = bool(self._depth_subscriptions)
        if has_depth_subs:
            self._start_depth_feed()

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
        return [(1, s, 17) for s, _ in self._subscriptions]

    @staticmethod
    def _to_sdk_instruments(
        security_ids: list[tuple[str, str]], mode: str = "quote",
    ) -> list[tuple[int, str, int]]:
        mi = _sdk_mode_int(mode)
        return [(1, sid, mi) for sid, _ in security_ids]

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

    def _start_depth_feed(self) -> None:
        if self._depth_thread is not None and self._depth_thread.is_alive():
            return
        with self._lock:
            if not self._depth_subscriptions:
                return
        self._depth_stop.clear()
        self._depth_feed_ready = threading.Event()
        self._depth_thread = threading.Thread(
            target=self._run_depth_feed, daemon=True, name="dhan-depth",
        )
        self._depth_thread.start()
        if not self._depth_feed_ready.wait(timeout=5):
            logger.warning("depth_feed_not_ready_within_timeout")

    def _stop_depth_feed(self) -> None:
        self._depth_stop.set()
        if self._depth_feed is not None:
            try:
                self._depth_feed.close_connection()
            except Exception:
                pass
            self._depth_feed = None
        if self._depth_thread is not None:
            self._depth_thread.join(timeout=3)
            self._depth_thread = None

    def _run_depth_feed(self) -> None:
        """Background thread for depth feed using FullDepth SDK."""
        from dhanhq.fulldepth import FullDepth

        try:
            with self._lock:
                instruments = list(self._depth_subscriptions)
            if not instruments:
                return

            sdk_instruments = self._to_depth_sdk_instruments(instruments)
            context = _DhanContextShim(self._client_id, self._access_token)

            feed = FullDepth(
                dhan_context=context, instruments=sdk_instruments, depth_level=20,
            )
            self._depth_feed = feed
            ready = self._depth_feed_ready
            if ready is not None:
                ready.set()

            loop = feed.loop
            loop.run_until_complete(feed.connect())
            loop.run_until_complete(self._depth_recv_loop(feed))
        except BaseException:
            logger.exception("depth_feed_crashed")
            self._depth_feed = None
            raise
        finally:
            ready = self._depth_feed_ready
            if ready is not None and not ready.is_set():
                ready.set()
            try:
                if self._depth_feed is not None:
                    self._depth_feed.close_connection()
            except Exception:
                pass

    async def _depth_recv_loop(self, feed: Any) -> None:
        """Async receive loop: reads binary depth data and combines bid/ask."""
        self._process_depth_commands_sync(feed)

        buffer: dict[str, dict[str, list[dict]]] = {}

        while not self._depth_stop.is_set():
            try:
                raw = await asyncio.wait_for(
                    feed.ws.recv(), timeout=self._DEPTH_RECV_TIMEOUT,
                )
            except asyncio.TimeoutError:
                self._process_depth_commands_sync(feed)
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
        ex_seg = _EXCH_CODE_TO_SEGMENT.get(int(ex_code), str(ex_code))
        depth_type = update["type"]
        levels = update["depth"]

        key = f"{ex_seg}:{sec_id}"
        entry = buffer.setdefault(key, {})
        entry[depth_type.lower()] = levels

        if "bid" in entry and "ask" in entry:
            snapshot = self._combine_depth_snapshot(
                sec_id, ex_seg, entry["bid"], entry["ask"],
            )
            if self._on_depth_tick:
                try:
                    self._on_depth_tick(snapshot)
                except Exception as exc:
                    logger.warning("depth_cb_error: %s", exc)
            buffer.pop(key, None)

    def _process_depth_commands_sync(self, feed: Any) -> None:
        while not self._depth_cmd_queue.empty():
            try:
                cmd = self._depth_cmd_queue.get_nowait()
                if cmd["action"] == "subscribe":
                    feed.subscribe_symbols(cmd["ids"])
                elif cmd["action"] == "unsubscribe":
                    feed.unsubscribe_symbols(cmd["ids"])
            except queue.Empty:
                break

    # ── Depth data helpers ───────────────────────────────────────────

    @staticmethod
    def _to_depth_sdk_instruments(
        security_ids: list[tuple[str, str]],
    ) -> list[tuple[int, str]]:
        seen: set[tuple[int, str]] = set()
        result: list[tuple[int, str]] = []
        for sec_id, segment in security_ids:
            ex_code = _WIRE_SEGMENT_TO_EXCH_CODE.get(segment, 1)
            key = (ex_code, sec_id)
            if key not in seen:
                seen.add(key)
                result.append(key)
        return result

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
                bid_price=float(b["price"]),
                bid_qty=int(b["quantity"]),
                ask_price=float(a["price"]),
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

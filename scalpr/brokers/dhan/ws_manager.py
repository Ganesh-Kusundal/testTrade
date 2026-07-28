"""WebSocket connection manager for Dhan market data.

High-level manager that coordinates ws_client + ws_parser, manages subscription
lifecycle, monitors health, and distributes events to multiple subscribers.

This is the production-ready bridge between the raw WebSocket transport layer
and the SCALPR domain (Tick, IMarketDataFeed).

As Uncle Bob says: "Clean boundaries between strategy, signals, orders, and risk."
This manager enforces that boundary — strategies never touch WebSocket internals,
and WebSocket internals never leak into strategy logic.
"""

from __future__ import annotations

import asyncio
import contextlib
import enum
import logging
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from scalpr.domain.tick import Tick
from scalpr.market_data.feed_port import IMarketDataFeed

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Connection status enum — explicit state, no magic strings
# ---------------------------------------------------------------------------

class ConnectionStatus(enum.Enum):
    """Explicit connection lifecycle states."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    DISCONNECTING = "disconnecting"


# ---------------------------------------------------------------------------
# Health metrics dataclass
# ---------------------------------------------------------------------------

@dataclass(slots=True, frozen=True)
class HealthMetrics:
    """Immutable snapshot of connection health."""
    status: ConnectionStatus
    subscriber_count: int
    active_subscriptions: int
    messages_total: int
    messages_per_second: float
    last_message_at: datetime | None
    last_error: str | None
    reconnect_count: int
    uptime_seconds: float


@dataclass(slots=True)
class _MutableMetrics:
    """Mutable internal metrics — never exposed directly."""
    messages_total: int = 0
    message_timestamps: deque[float] = field(default_factory=lambda: deque(maxlen=1000))
    last_message_at: datetime | None = None
    last_error: str | None = None
    reconnect_count: int = 0
    connect_time: float | None = None


# ---------------------------------------------------------------------------
# DhanWebSocketManager
# ---------------------------------------------------------------------------

class DhanWebSocketManager(IMarketDataFeed):
    """Production-ready WebSocket manager for Dhan market data.

    Responsibilities:
    - Manages a single WebSocket connection (extendable to multiple)
    - Subscription lifecycle (add/remove/persist across reconnects)
    - Health monitoring with metrics
    - Graceful shutdown (drain messages, persist state)
    - Thread-safe subscriber management
    - Event distribution to multiple subscribers
    - Automatic health check loop

    This class implements IMarketDataFeed so it can be used anywhere the
    SCALPR platform expects a market data feed port.

    Architecture:
    - Delegates low-level WebSocket operations to DhanWebSocketClient
    - Delegates message parsing to DhanWebSocketParser
    - Manages fan-out to multiple subscribers
    - Tracks health metrics for observability
    """

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(
        self,
        access_token: str,
        client_id: str = "",
        health_check_interval: float = 30.0,
        reconnect_delay: float = 5.0,
        max_reconnect_attempts: int = 10,
        message_rate_window: float = 10.0,
        resolver: Any = None,  # NEW: SymbolResolver for security_id resolution
        token_refresh_fn: Callable[[], str] | None = None,
    ):
        self._access_token = access_token
        self._client_id = client_id
        self._health_check_interval = health_check_interval
        self._reconnect_delay = reconnect_delay
        self._max_reconnect_attempts = max_reconnect_attempts
        self._message_rate_window = message_rate_window
        self._resolver = resolver  # NEW: Store resolver
        # Threaded down to ws_client so reconnects pick up rotated tokens
        self._token_refresh_fn = token_refresh_fn

        # Mutable state protected by asyncio.Lock
        self._status = ConnectionStatus.DISCONNECTED
        self._subscribers: list[Callable[[Tick], None]] = []
        self._subscriptions: set[tuple[str, str]] = set()  # (symbol, exchange)
        self._metrics = _MutableMetrics()
        self._running = False
        self._lock = asyncio.Lock()

        # Async tasks
        self._message_loop_task: asyncio.Task[None] | None = None
        self._health_check_task: asyncio.Task[None] | None = None

        # Tick queue — bounded to prevent memory exhaustion under high tick rates
        self._tick_queue: asyncio.Queue[Tick] = asyncio.Queue(maxsize=50000)

        # Deferred callback for IMarketDataFeed compatibility
        self._on_tick_callback: Callable[[Tick], None] | None = None

        # Lazy imports — ws_client and ws_parser created on first start()
        self._ws_client: Any = None
        self._ws_parser: Any = None

    # ------------------------------------------------------------------
    # IMarketDataFeed interface implementation
    # ------------------------------------------------------------------

    def connect(self) -> bool:
        """Establish connection with the market data server.

        Synchronous wrapper — starts the async machinery on the running
        event loop. Returns True immediately; actual connection is async.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            logger.warning("No running event loop — connect() must be called from async context")
            return False

        # Fire-and-forget — caller should handle errors in their own task
        task = loop.create_task(self.start())
        task.add_done_callback(self._log_task_exception)
        return True

    def disconnect(self) -> bool:
        """Terminate connection with the market data server."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            logger.warning("No running event loop — disconnect() must be called from async context")
            return False

        task = loop.create_task(self.stop())
        task.add_done_callback(self._log_task_exception)
        return True

    def subscribe(self, symbols: list[str]) -> bool:
        """Subscribe to real-time tick feeds for the specified symbols.

        For IMarketDataFeed compatibility, symbols are simple strings.
        Internally they are stored as (symbol, "NSE") tuples.
        """
        subscriptions = [(s, "NSE") for s in symbols]
        try:
            loop = asyncio.get_running_loop()
            task = loop.create_task(self._subscribe_async(subscriptions))
            task.add_done_callback(self._log_task_exception)
        except RuntimeError:
            # Synchronous path — add to set, will be sent on next connect
            self._subscriptions.update(subscriptions)
        return True

    def unsubscribe(self, symbols: list[str]) -> bool:
        """Unsubscribe from tick feeds for the specified symbols."""
        subscriptions = {(s, "NSE") for s in symbols}
        try:
            loop = asyncio.get_running_loop()
            task = loop.create_task(self._unsubscribe_async(subscriptions))
            task.add_done_callback(self._log_task_exception)
        except RuntimeError:
            self._subscriptions -= subscriptions
        return True

    def is_connected(self) -> bool:
        """Check if WebSocket connection is active."""
        return self._status == ConnectionStatus.CONNECTED

    def on_tick(self, callback: Callable[[Tick], None]) -> None:
        """Register callback for incoming tick packets."""
        self.add_subscriber(callback)

    # ------------------------------------------------------------------
    # Public async API
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Connect WebSocket client and start message processing loop.

        This is the main entry point. It:
        1. Creates ws_client and ws_parser instances (lazy import)
        2. Connects the WebSocket
        3. Starts the message processing loop
        4. Starts the health check loop
        5. Re-sends any persisted subscriptions
        """
        if self._running:
            logger.warning("WebSocket manager already running — ignoring start()")
            return

        self._running = True
        self._set_status(ConnectionStatus.CONNECTING)

        try:
            # Lazy import — ws_client and ws_parser are created separately
            self._ensure_components()

            # Connect the underlying WebSocket client
            await self._ws_client.connect()
            self._set_status(ConnectionStatus.CONNECTED)
            self._metrics.connect_time = time.monotonic()
            logger.info("Dhan WebSocket connected")

            # Restore persisted subscriptions
            if self._subscriptions:
                # Modes are not persisted per-pair: restore uses the client
                # default, so an overridden mode (e.g. "full") is downgraded.
                logger.warning("Restoring %d subscriptions with client default mode", len(self._subscriptions))
                await self._ws_client.subscribe(list(self._subscriptions))
                logger.info("Restored %d subscriptions", len(self._subscriptions))

            # Start background tasks
            self._message_loop_task = asyncio.create_task(self._message_loop())
            self._health_check_task = asyncio.create_task(self._health_check_loop())

        except Exception as exc:
            logger.error("Failed to start WebSocket manager: %s", exc)
            self._set_status(ConnectionStatus.DISCONNECTED)
            self._running = False
            raise

    async def stop(self) -> None:
        """Disconnect gracefully — drain messages, persist subscriptions.

        Order matters:
        1. Stop accepting new messages
        2. Cancel background tasks
        3. Drain remaining messages from queue
        4. Disconnect WebSocket
        5. Persist state
        """
        if not self._running:
            logger.debug("WebSocket manager not running — ignoring stop()")
            return

        self._running = False
        self._set_status(ConnectionStatus.DISCONNECTING)
        logger.info("Shutting down Dhan WebSocket manager...")

        # Cancel background tasks
        if self._message_loop_task and not self._message_loop_task.done():
            self._message_loop_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._message_loop_task

        if self._health_check_task and not self._health_check_task.done():
            self._health_check_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._health_check_task

        # Drain remaining ticks from the queue
        drained = 0
        while not self._tick_queue.empty():
            try:
                tick = self._tick_queue.get_nowait()
                await self._distribute_tick(tick)
                drained += 1
            except asyncio.QueueEmpty:
                break
        if drained > 0:
            logger.info("Drained %d ticks during shutdown", drained)

        # Disconnect WebSocket client
        try:
            if self._ws_client is not None:
                await self._ws_client.disconnect()
        except Exception as exc:
            logger.error("Error during WebSocket disconnect: %s", exc)

        self._set_status(ConnectionStatus.DISCONNECTED)
        logger.info("Dhan WebSocket manager stopped")

    async def _subscribe_async(self, symbols: list[tuple[str, str]], mode: str | None = None) -> None:
        """Add to subscription list and send subscribe to client if running."""
        async with self._lock:
            self._subscriptions.update(symbols)

        if self._status == ConnectionStatus.CONNECTED and self._ws_client is not None:
            try:
                results = await self._ws_client.subscribe(symbols, mode=mode)
                failed = sorted(p for p, ok in results.items() if not ok)
                if failed:
                    # Failed pairs must not linger as phantom subscriptions —
                    # they would be replayed forever on every reconnect.
                    async with self._lock:
                        self._subscriptions -= set(failed)
                    self._metrics.last_error = f"subscribe dropped {len(failed)} pairs: {failed}"
                    logger.error("Subscribe dropped %d/%d pairs: %s", len(failed), len(symbols), failed)
                logger.info("Subscribed to %d/%d symbols", len(symbols) - len(failed), len(symbols))
            except Exception as exc:
                logger.error("Failed to subscribe: %s", exc)
                self._metrics.last_error = str(exc)

    async def subscribe_pairs(self, pairs: list[tuple[str, str]], mode: str | None = None) -> None:
        """Subscribe to (symbol, exchange) pairs, preserving the exchange.

        Unlike the IMarketDataFeed ``subscribe(list[str])`` (which hardcodes
        NSE), this is the exchange-aware entry point for callers that know
        the segment. ``mode`` overrides the client default ("ltp", "quote",
        "depth", "full"); reconnect resubscription uses the client default.
        """
        await self._subscribe_async(pairs, mode=mode)

    async def unsubscribe_pairs(self, pairs: list[tuple[str, str]]) -> None:
        """Unsubscribe (symbol, exchange) pairs, preserving exchange awareness."""
        await self._unsubscribe_async(set(pairs))

    async def _unsubscribe_async(self, symbols: set[tuple[str, str]]) -> None:
        """Remove from subscription list and send unsubscribe to client."""
        async with self._lock:
            self._subscriptions -= symbols

        if self._status == ConnectionStatus.CONNECTED and self._ws_client is not None:
            try:
                await self._ws_client.unsubscribe(list(symbols))
                logger.info("Unsubscribed from %d symbols", len(symbols))
            except Exception as exc:
                logger.error("Failed to unsubscribe: %s", exc)
                self._metrics.last_error = str(exc)

    # ------------------------------------------------------------------
    # Subscriber management (thread-safe via asyncio.Lock)
    # ------------------------------------------------------------------

    def add_subscriber(self, callback: Callable[[Tick], None]) -> None:
        """Register callback for tick delivery.

        Thread-safe: uses asyncio.Lock for mutation.
        Callbacks are never called under the lock.
        """
        if callback in self._subscribers:
            logger.debug("Subscriber already registered — ignoring duplicate")
            return

        # Use run_coroutine_threadsafe if called from non-async context
        try:
            loop = asyncio.get_running_loop()
            task = loop.create_task(self._add_subscriber_async(callback))
            task.add_done_callback(self._log_task_exception)
        except RuntimeError:
            # Synchronous fallback — direct mutation (acceptable for startup)
            self._subscribers.append(callback)
            logger.info("Subscriber added (sync path). Total: %d", len(self._subscribers))

    async def _add_subscriber_async(self, callback: Callable[[Tick], None]) -> None:
        async with self._lock:
            self._subscribers.append(callback)
        logger.info("Subscriber added. Total: %d", len(self._subscribers))

    def remove_subscriber(self, callback: Callable[[Tick], None]) -> None:
        """Unregister callback."""
        try:
            loop = asyncio.get_running_loop()
            task = loop.create_task(self._remove_subscriber_async(callback))
            task.add_done_callback(self._log_task_exception)
        except RuntimeError:
            if callback in self._subscribers:
                self._subscribers.remove(callback)
                logger.info("Subscriber removed (sync path). Total: %d", len(self._subscribers))

    async def _remove_subscriber_async(self, callback: Callable[[Tick], None]) -> None:
        async with self._lock:
            if callback in self._subscribers:
                self._subscribers.remove(callback)
        logger.info("Subscriber removed. Total: %d", len(self._subscribers))

    # ------------------------------------------------------------------
    # Message processing
    # ------------------------------------------------------------------

    async def _message_loop(self) -> None:
        """Core message processing loop.

        Registers a tick callback on the ws_client and waits for messages.
        The ws_client handles its own receive loop — we just fan out to
        our subscribers.

        This loop is resilient — subscriber errors never crash it.
        """
        logger.info("Message processing loop started")

        # Register our callback on the ws_client
        self._ws_client.on_tick(self._on_tick_received)

        try:
            while self._running:
                # The ws_client manages its own receive loop.
                # We just stay alive and monitor health here.
                await asyncio.sleep(1.0)
        except asyncio.CancelledError:
            logger.info("Message loop cancelled")
        except Exception as exc:
            logger.error("Error in message loop: %s", exc)
            self._metrics.last_error = str(exc)

        logger.info("Message processing loop exited")

    def _on_tick_received(self, tick: Tick) -> None:
        """Callback invoked by ws_client when a tick arrives.

        Records metrics and distributes to subscribers.
        This runs in the ws_client's async context, so we need to be
        careful about blocking operations.
        """
        # Record metrics
        now = time.monotonic()
        self._metrics.messages_total += 1
        self._metrics.message_timestamps.append(now)
        self._metrics.last_message_at = datetime.now(timezone.utc)

        # Distribute to subscribers synchronously (fast path)
        self._distribute_tick_sync(tick)

    async def _distribute_tick(self, tick: Tick) -> None:
        """Distribute tick to all registered subscribers (async version)."""
        self._distribute_tick_sync(tick)

    def _distribute_tick_sync(self, tick: Tick) -> None:
        """Distribute tick to all registered subscribers (sync version).

        Critical: subscriber errors are caught and logged — never crash
        the message loop. This is a single point of failure if not
        handled correctly.
        """
        if not self._subscribers:
            return

        for callback in self._subscribers:
            try:
                callback(tick)
            except Exception as exc:
                callback_name = callback.__name__ if hasattr(callback, "__name__") else "anonymous"
                logger.error("Subscriber callback error (%s): %s", callback_name, exc)

    # ------------------------------------------------------------------
    # Health monitoring
    # ------------------------------------------------------------------

    async def _health_check_loop(self) -> None:
        """Periodic health check — runs every _health_check_interval seconds.

        Responsibilities:
        - Monitor connection status
        - Detect stale connections (no messages for extended period)
        - Trigger reconnection if needed
        - Log health metrics
        """
        logger.info("Health check loop started (interval=%ss)", self._health_check_interval)

        while self._running:
            try:
                await asyncio.sleep(self._health_check_interval)

                health = self.get_health_status()

                # Log health metrics
                logger.debug(
                    "Health: status=%s, subs=%d, msgs=%d, mps=%.1f, reconnects=%d",
                    health.status.value,
                    health.subscriber_count,
                    health.messages_total,
                    health.messages_per_second,
                    health.reconnect_count,
                )

                # Stale connection detection — no messages for 2x health interval
                if (
                    health.status == ConnectionStatus.CONNECTED
                    and health.last_message_at is not None
                ):
                    stale_seconds = (
                        datetime.now(timezone.utc) - health.last_message_at
                    ).total_seconds()
                    if stale_seconds > self._health_check_interval * 2:
                        logger.warning("Stale connection detected — no messages for %.0fs", stale_seconds)
                        await self._reconnect()

            except asyncio.CancelledError:
                logger.info("Health check loop cancelled")
                break
            except Exception as exc:
                logger.error("Health check error: %s", exc)
                self._metrics.last_error = str(exc)

        logger.info("Health check loop exited")

    async def _reconnect(self) -> None:
        """Reconnection strategy — delegate to ws_client with backoff."""
        if self._status in (ConnectionStatus.DISCONNECTING, ConnectionStatus.RECONNECTING):
            return

        self._set_status(ConnectionStatus.RECONNECTING)
        logger.info("Attempting reconnection...")

        attempts = 0
        while self._running and attempts < self._max_reconnect_attempts:
            attempts += 1
            delay = self._reconnect_delay * (2 ** (attempts - 1))  # Exponential backoff
            logger.info(
                "Reconnect attempt %d/%d (delay=%.1fs)",
                attempts,
                self._max_reconnect_attempts,
                delay,
            )

            try:
                await asyncio.sleep(delay)

                # Reset client and reconnect
                if self._ws_client is not None:
                    try:
                        await self._ws_client.disconnect()
                    except Exception as exc:
                        logger.debug("Disconnect failed during reconnect: %s", exc)
                    await self._ws_client.connect()

                self._set_status(ConnectionStatus.CONNECTED)
                self._metrics.reconnect_count += 1
                self._metrics.connect_time = time.monotonic()

                # Restore subscriptions (client default mode — overridden
                # modes are not persisted per-pair and get downgraded)
                if self._subscriptions:
                    logger.warning("Re-subscribing %d pairs with client default mode", len(self._subscriptions))
                    await self._ws_client.subscribe(list(self._subscriptions))

                logger.info("Reconnection successful (attempt %d)", attempts)
                return

            except Exception as exc:
                logger.error("Reconnect attempt %d failed: %s", attempts, exc)
                self._metrics.last_error = str(exc)

        # Exhausted all attempts
        self._set_status(ConnectionStatus.DISCONNECTED)
        logger.error("Reconnection failed after %d attempts — giving up", attempts)

    def get_health_status(self) -> HealthMetrics:
        """Return immutable snapshot of connection health.

        Safe to call from any thread — returns a frozen dataclass.
        """
        now = time.monotonic()
        timestamps = list(self._metrics.message_timestamps)

        # Calculate messages per second using sliding window
        cutoff = now - self._message_rate_window
        recent_messages = sum(1 for ts in timestamps if ts > cutoff)
        mps = recent_messages / self._message_rate_window if self._message_rate_window > 0 else 0.0

        uptime = 0.0
        if self._metrics.connect_time is not None:
            uptime = now - self._metrics.connect_time

        return HealthMetrics(
            status=self._status,
            subscriber_count=len(self._subscribers),
            active_subscriptions=len(self._subscriptions),
            messages_total=self._metrics.messages_total,
            messages_per_second=round(mps, 2),
            last_message_at=self._metrics.last_message_at,
            last_error=self._metrics.last_error,
            reconnect_count=self._metrics.reconnect_count,
            uptime_seconds=round(uptime, 2),
        )

    # ------------------------------------------------------------------
    # Subscription persistence (for graceful shutdown / restart)
    # ------------------------------------------------------------------

    def get_active_subscriptions(self) -> list[tuple[str, str]]:
        """Return current subscriptions as a list of (symbol, exchange) tuples.

        Useful for persisting state before shutdown or checkpointing.
        """
        return list(self._subscriptions)

    def restore_subscriptions(self, subscriptions: list[tuple[str, str]]) -> None:
        """Restore subscriptions from persisted state.

        Call this before start() to pre-populate the subscription set.
        Subscriptions will be sent to the WebSocket on connect.
        """
        self._subscriptions.update(subscriptions)
        logger.info("Restored %d persisted subscriptions", len(subscriptions))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _set_status(self, status: ConnectionStatus) -> None:
        """Transition connection status with logging."""
        if self._status == status:
            return
        old = self._status
        self._status = status
        logger.info("Connection status: %s -> %s", old.value, status.value)

    def _ensure_components(self) -> None:
        """Lazy import and create ws_client instance.

        This allows ws_manager to be tested without ws_client
        existing, and allows dependency injection for testing.

        Note: ws_parser was removed (SDK handles parsing in ws_client).
        """
        if self._ws_client is not None:
            return

        # Try to import — if not available, raise error (production requirement)
        try:
            from scalpr.brokers.dhan.ws_client import DhanWebSocketClient
            self._ws_client = DhanWebSocketClient(
                access_token=self._access_token,
                client_id=self._client_id,
                resolver=self._resolver,
                token_refresh_fn=self._token_refresh_fn,
            )
            logger.debug("DhanWebSocketClient created via import")
        except ImportError as exc:
            raise ImportError(
                "scalpr.brokers.dhan.ws_client is required for production use"
            ) from exc

        # ws_parser removed: SDK handles all parsing in ws_client._parse_sdk_data()
        self._ws_parser = None

    @staticmethod
    def _log_task_exception(task: asyncio.Task[object]) -> None:
        """Log exceptions from fire-and-forget tasks."""
        if task.exception():
            logger.error("Background task failed: %s", task.exception())

    # ------------------------------------------------------------------
    # Context manager support
    # ------------------------------------------------------------------

    async def __aenter__(self) -> DhanWebSocketManager:
        await self.start()
        return self

    async def __aexit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: Any) -> None:
        await self.stop()

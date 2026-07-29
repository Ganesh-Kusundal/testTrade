"""Streaming mixin for Gateway.

Provides streaming operations: stream, stop_stream, is_streaming, subscribe_feed, unsubscribe.
"""
from __future__ import annotations

import asyncio
import logging
import threading
from collections.abc import Callable
from typing import Any

from scalpr.domain.instrument import MarketFeed, SimpleInstrumentId
from scalpr.domain.tick import Tick
from scalpr.domain.values import DEFAULT_EXCHANGE, DEFAULT_TIMEOUT_S, SHORT_TIMEOUT_S

logger = logging.getLogger(__name__)


class StreamingMixin:
    """Mixin providing streaming operations.

    Expects the composed Gateway class to provide these attributes.
    """

    # Attributes provided by the composed Gateway class
    _broker_name: str
    _gateway: Any
    _config: dict[str, Any]
    _ws_manager: Any
    _ws_loop: Any
    _ws_thread: Any
    _stream_callbacks: list[Callable[..., Any]]
    _ws_lock: Any

    def stream(
        self,
        symbols: str | list[str],
        exchange: str = DEFAULT_EXCHANGE,
        callback: Callable[[Tick], None] | None = None,
    ) -> None:
        """Subscribe to live market data stream for symbols.

        Args:
            symbols: Single symbol or list of symbols to stream
            exchange: Exchange code (default: "NSE")
            callback: Function to call with each Tick (optional)
        """
        if isinstance(symbols, str):
            symbols = [symbols]

        if callback:
            self._stream_callbacks.append(callback)

        # Initialize WebSocket manager if not already done (lock guards
        # concurrent init/teardown races)
        with self._ws_lock:
            if self._ws_manager is None:
                self._init_websocket_manager()
            manager, loop = self._ws_manager, self._ws_loop

        # Subscribe on the manager's event loop, preserving the exchange
        asyncio.run_coroutine_threadsafe(
            manager.subscribe_pairs([(s, exchange) for s in symbols]),
            loop,
        ).result(timeout=DEFAULT_TIMEOUT_S)

        logger.info("stream_subscribed: %s", symbols)

    def stop_stream(self) -> None:
        """Stop all streaming subscriptions and the background loop."""
        with self._ws_lock:
            manager, loop, thread = self._ws_manager, self._ws_loop, self._ws_thread
            self._ws_manager = None
            self._ws_loop = None
            self._ws_thread = None
            self._stream_callbacks.clear()
        if manager is None or loop is None:
            return
        try:
            asyncio.run_coroutine_threadsafe(
                manager.stop(), loop
            ).result(timeout=DEFAULT_TIMEOUT_S)
        except Exception as exc:
            logger.error("ws_manager_stop_failed: %s", exc)
        finally:
            try:
                loop.call_soon_threadsafe(loop.stop)
            except RuntimeError:
                pass  # loop already closed/dead
            if thread is not None:
                thread.join(timeout=SHORT_TIMEOUT_S)
            if thread is None or not thread.is_alive():
                loop.close()
                logger.info("stream_stopped")
            else:
                logger.warning("ws_thread_did_not_exit: leaving loop unclosed")

    def is_streaming(self) -> bool:
        """Check if streaming is active.

        Returns:
            True if streaming is active
        """
        return self._ws_manager is not None

    def subscribe_feed(
        self,
        mode: MarketFeed,
        instruments: str | list[str],
        on_event: Callable[[Any], None] | None = None,
    ) -> None:
        """Subscribe to live market data feed.

        Args:
            mode: Subscription depth (MarketFeed.LTP, QUOTE, or FULL)
            instruments: Qualified symbol(s), e.g. "TCS:NSE" or ["TCS:NSE", "RELIANCE:NSE"]
            on_event: Optional callback for market events

        Usage::

            gw.subscribe_feed(MarketFeed.FULL, ["TCS:NSE", "RELIANCE:NSE"], on_event=handle_tick)
        """
        mode = MarketFeed(mode)  # accept plain strings like "full"
        if isinstance(instruments, str):
            instruments = [instruments]

        pairs = []
        for inst_str in instruments:
            inst_id = SimpleInstrumentId.parse(inst_str)
            pairs.append((inst_id.symbol, inst_id.exchange.value))

        with self._ws_lock:
            if self._ws_manager is None:
                self._init_websocket_manager()
            manager, loop = self._ws_manager, self._ws_loop

        # Register the callback BEFORE subscribing so no early ticks are dropped
        if on_event:
            self._stream_callbacks.append(on_event)

        try:
            asyncio.run_coroutine_threadsafe(
                manager.subscribe_pairs(pairs, mode=mode.value),
                loop,
            ).result(timeout=DEFAULT_TIMEOUT_S)
        except Exception:
            # Unwind: a failed subscribe must not leave a live callback behind
            if on_event and on_event in self._stream_callbacks:
                self._stream_callbacks.remove(on_event)
            raise

        logger.info("feed_subscribed: %s mode=%s", instruments, mode.value)

    def unsubscribe(
        self,
        instruments: str | list[str],
    ) -> None:
        """Unsubscribe from live market data feed.

        Args:
            instruments: Qualified symbol(s), e.g. "TCS:NSE" or ["TCS:NSE", "RELIANCE:NSE"]
        """
        if isinstance(instruments, str):
            instruments = [instruments]

        with self._ws_lock:
            if self._ws_manager is None:
                return  # nothing to unsubscribe from
            manager, loop = self._ws_manager, self._ws_loop

        pairs = []
        for inst_str in instruments:
            inst_id = SimpleInstrumentId.parse(inst_str)
            pairs.append((inst_id.symbol, inst_id.exchange.value))

        try:
            asyncio.run_coroutine_threadsafe(
                manager.unsubscribe_pairs(pairs),
                loop,
            ).result(timeout=DEFAULT_TIMEOUT_S)
        except Exception:
            logger.warning(f"unsubscribe_failed: {instruments}", exc_info=True)
            raise

        logger.info("feed_unsubscribed: %s", instruments)

    def _dispatch_tick(self, tick: Tick) -> None:
        """Fan a tick out to every registered stream callback."""
        for cb in list(self._stream_callbacks):
            try:
                cb(tick)
            except Exception:
                logger.exception("stream_callback_error")

    def _init_websocket_manager(self) -> None:
        """Initialize WebSocket manager on a dedicated background event loop.

        Gateway is used from sync CLI/scripts, so it owns a daemon-thread
        loop that runs the async WebSocket manager machinery.
        """
        from scalpr.brokers.registry import BrokerRegistry

        DhanWebSocketManager = BrokerRegistry.get_adapter(
            self._broker_name, "ws_manager"
        )
        if DhanWebSocketManager is None:
            raise NotImplementedError(
                f"Streaming not available for {self._broker_name}"
            )

        if not hasattr(self._gateway, "connection"):
            raise ValueError(
                "Gateway does not expose connection for WebSocket initialization"
            )

        # Resolver is mandatory: without it ws_client only accepts
        # digit-only symbols and silently skips named ones.
        resolver = self._gateway.connection.resolver

        self._ws_loop = asyncio.new_event_loop()
        self._ws_thread = threading.Thread(
            target=self._ws_loop.run_forever, name="gateway-ws-loop", daemon=True
        )
        self._ws_thread.start()

        self._ws_manager = DhanWebSocketManager(
            access_token=self._config.get("access_token", ""),
            client_id=self._config.get("client_id", ""),
            resolver=resolver,
        )
        # Registered before start(): no loop running in this thread, so
        # add_subscriber takes its synchronous append path.
        self._ws_manager.add_subscriber(self._dispatch_tick)

        asyncio.run_coroutine_threadsafe(
            self._ws_manager.start(), self._ws_loop
        ).result(timeout=DEFAULT_TIMEOUT_S)
        logger.info("websocket_manager_initialized")

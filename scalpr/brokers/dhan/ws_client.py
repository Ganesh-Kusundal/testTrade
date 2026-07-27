"""WebSocket client for Dhan live market data streaming.

Production-ready WebSocket client using the official dhanhq SDK.

Uses the official dhanhq SDK (like Trade_XV2) which handles binary parsing internally.
This is the correct approach - raw WebSocket binary parsing is error-prone and
unnecessary when the SDK provides a clean Python interface.

Adapted from Trade_XV2 with SCALPR-specific architecture:
- Implements IMarketDataFeed contract from scalpr.market_data.feed_port
- Emits scalpr.domain.tick.Tick domain objects  
- Uses scalpr.brokers.dhan.* for broker-specific mappings
- Thread-safe with background SDK thread + async wrapper

As Dr. Venkat says: "A system that is fast and wrong is more dangerous than
a system that is slow and right." — use the tested SDK, don't reinvent parsing.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from collections.abc import Callable
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from scalpr.brokers.dhan.exceptions import AuthenticationError, MarketDataError
from scalpr.brokers.dhan.segments import EXCHANGE_TO_SEGMENT, NUMERIC_TO_SEGMENT
from scalpr.domain.tick import Tick

logger = logging.getLogger(__name__)


# ── Dhan WebSocket Constants ─────────────────────────────────────────

# Default subscription mode
_DEFAULT_MODE = "quote"

# Mode mapping for SDK
_SDK_MODES: dict[str, str] = {
    "ltp": "Ticker",
    "quote": "Quote",
    "depth": "Quote",  # SDK doesn't distinguish depth from quote in v2
    "full": "Full",
}


def _get_sdk_mode_int(mode_str: str) -> int:
    """Get SDK mode integer from mode string."""
    from dhanhq.marketfeed import MarketFeed
    
    mode_name = _SDK_MODES.get(mode_str, "Quote")
    return getattr(MarketFeed, mode_name, MarketFeed.Quote)


def _sdk_market_feed_class():
    """Lazy import so module does not require dhanhq at import time."""
    from dhanhq.marketfeed import MarketFeed
    return MarketFeed


class _DhanContextShim:
    """Shim to satisfy SDK's dhan_context interface."""
    
    def __init__(self, client_id: str, access_token: str):
        self._client_id = client_id
        self._access_token = access_token
    
    def get_client_id(self) -> str:
        return self._client_id
    
    def get_access_token(self) -> str:
        return self._access_token
    
    def get_dhan_http(self):
        return None
    
    def update_token(self, token: str) -> None:
        self._access_token = token


class _SubscriptionKey:
    """Immutable key for tracking a symbol+exchange subscription."""

    __slots__ = ("symbol", "exchange", "mode")

    def __init__(self, symbol: str, exchange: str, mode: str = _DEFAULT_MODE):
        self.symbol = symbol
        self.exchange = exchange
        self.mode = mode

    def __hash__(self) -> int:
        return hash((self.symbol, self.exchange, self.mode))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, _SubscriptionKey):
            return NotImplemented
        return (
            self.symbol == other.symbol
            and self.exchange == other.exchange
            and self.mode == other.mode
        )

    def __repr__(self) -> str:
        return f"SubKey({self.symbol!r}, {self.exchange!r}, {self.mode!r})"


def _exchange_to_segment_int(exchange: str) -> int:
    """Convert exchange string to SDK segment integer.
    
    Uses the numeric codes from segments.py:
    - NSE_EQ = 1
    - MCX_COMM = 5
    - NSE_FNO = 2
    """
    segment_str = EXCHANGE_TO_SEGMENT.get(exchange.upper(), "NSE_EQ")
    # Reverse lookup from segment string to numeric code
    SEGMENT_TO_NUMERIC = {v: k for k, v in NUMERIC_TO_SEGMENT.items()}
    return SEGMENT_TO_NUMERIC.get(segment_str, 1)  # Default to NSE_EQ=1


class DhanWebSocketClient:
    """Async WebSocket client for Dhan live market data streaming.
    
    Uses the official dhanhq SDK's MarketFeed which:
    - Handles binary protocol internally
    - Returns Python dicts via on_message callback
    - Manages heartbeats and reconnection
    
    Usage::
    
        client = DhanWebSocketClient(
            client_id="12345",
            access_token="..."
        )
        client.on_tick(lambda tick: print(tick))
        await client.connect()
        await client.subscribe([("RELIANCE", "NSE"), ("TCS", "NSE")])
        # ticks arrive via callback...
        await client.disconnect()
    """
    
    def __init__(
        self,
        access_token: str,
        client_id: str = "",
        mode: str = _DEFAULT_MODE,
        resolver: Any = None,  # NEW: SymbolResolver for security_id resolution
    ) -> None:
        """Initialise the WebSocket client.
        
        Args:
            access_token: Dhan API access token.
            client_id: Dhan API client ID.
            mode: Subscription mode — "ltp", "quote", "depth", or "full".
            resolver: Optional SymbolResolver for symbol-to-security_id resolution.
        """
        self._client_id = client_id
        self._token = access_token
        self._mode = mode
        self._resolver = resolver  # NEW: Store resolver
        
        # SDK instance (created on connect)
        self._feed: Any = None
        self._context: _DhanContextShim | None = None
        self._connected = False
        self._shutting_down = False
        
        # Background thread
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        
        # Subscription tracking (SDK pattern: maintain list for reconnection)
        self._instruments: list[tuple] = []  # SDK format: (exch_int, security_id_int, mode_int)
        self._subscribed_instruments: set[tuple] = set()  # For dedup
        self._sub_lock = threading.Lock()
        
        # Callbacks
        self._tick_callback: Callable[[Tick], None] | None = None
        
        # Volume tracking for delta computation
        self._cumulative_vols: dict[str, int] = {}
        self._vol_lock = threading.Lock()  # NEW: Thread safety for volume tracking
    
    # ── Public API ────────────────────────────────────────────────────────────
    
    async def connect(self) -> bool:
        """Establish WebSocket connection using SDK.
        
        Returns:
            True if connection established successfully.
        
        Raises:
            AuthenticationError: If token is rejected.
            MarketDataError: If connection fails.
        """
        if self._connected:
            logger.debug("already_connected: skipping connect")
            return True
        
        self._shutting_down = False
        self._stop_event.clear()
        
        try:
            # Create SDK MarketFeed instance with current instruments
            MarketFeed = _sdk_market_feed_class()
            self._context = _DhanContextShim(self._client_id, self._token)
            
            self._feed = MarketFeed(
                dhan_context=self._context,
                instruments=list(self._instruments),  # Pass instruments at construction
                on_connect=self._on_connect,
                on_message=self._on_message,
                on_close=self._on_close,
                on_error=self._on_error,
            )
            
            # Start SDK in background thread
            self._thread = threading.Thread(
                target=self._run_sdk,
                name="dhan-ws-client",
                daemon=True,
            )
            self._thread.start()
            
            # Wait for connection
            for _ in range(50):  # 5 seconds max
                if self._connected:
                    break
                await asyncio.sleep(0.1)
            else:
                raise MarketDataError("Connection timeout")
            
            logger.info("connected")
            return True
            
        except Exception as exc:
            logger.error("connect_failed", extra={"error": str(exc)})
            raise
    
    async def disconnect(self) -> bool:
        """Gracefully close the WebSocket connection.
        
        Returns:
            True if disconnected cleanly.
        """
        self._shutting_down = True
        self._connected = False
        self._stop_event.set()
        
        # Close SDK feed
        if self._feed:
            try:
                self._feed.close_connection()
            except Exception as exc:
                logger.warning("error_closing_feed", extra={"error": str(exc)})
        
        # Wait for thread to stop
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        
        self._feed = None
        self._instruments.clear()
        self._subscribed_instruments.clear()
        self._cumulative_vols.clear()
        
        logger.info("disconnected")
        return True
    
    async def subscribe(
        self,
        symbols: list[tuple[str, str]],
        mode: str | None = None,
    ) -> bool:
        """Subscribe to real-time tick feeds for symbol+exchange pairs.
        
        Args:
            symbols: List of (symbol, exchange) tuples.
                     e.g., [("RELIANCE", "NSE"), ("TCS", "NSE")]
            mode: Override subscription mode for this call.
        
        Returns:
            True if subscription successful.
        
        Raises:
            MarketDataError: If not connected.
        """
        sub_mode = mode or self._mode
        
        # Convert to SDK format: (exchange_int, security_id_int, mode_int)
        new_instruments = []
        for symbol, exchange in symbols:
            exch_int = _exchange_to_segment_int(exchange)
            mode_int = _get_sdk_mode_int(sub_mode)
            
            # Resolve security_id via resolver (preferred) or fallback to int(symbol)
            if self._resolver is not None:
                try:
                    inst = self._resolver.resolve(symbol, exchange)
                    security_id_int = int(inst.security_id)
                except Exception as exc:
                    logger.warning("security_id_resolution_failed", extra={
                        "symbol": symbol, "exchange": exchange, "error": str(exc)
                    })
                    continue
            else:
                # Fallback: try parsing symbol as int (backward compat for direct security_id usage)
                try:
                    security_id_int = int(symbol)
                except (ValueError, TypeError):
                    logger.warning("invalid_security_id_no_resolver", extra={"symbol": symbol})
                    continue
            
            sdk_instr = (exch_int, security_id_int, mode_int)
            
            # Dedup (Trade_XV2 pattern)
            with self._sub_lock:
                if sdk_instr not in self._subscribed_instruments:
                    self._instruments.append(sdk_instr)
                    self._subscribed_instruments.add(sdk_instr)
                    new_instruments.append(sdk_instr)
        
        if not new_instruments:
            logger.debug("all instruments already subscribed")
            return True
        
        # If already connected, use subscribe_symbols for dynamic add
        if self._feed is not None:
            try:
                self._feed.subscribe_symbols(new_instruments)
                logger.info("subscribed", extra={"symbols": [s[1] for s in new_instruments], "count": len(new_instruments)})
                return True
            except Exception as exc:
                raise MarketDataError(f"Subscription failed: {exc}") from exc
        else:
            # Not connected yet - instruments will be passed at connect()
            logger.info("instruments queued for subscription", extra={"count": len(new_instruments)})
            return True
    
    async def unsubscribe(
        self,
        symbols: list[tuple[str, str]],
        mode: str | None = None,
    ) -> bool:
        """Unsubscribe from tick feeds.
        
        Args:
            symbols: List of (symbol, exchange) tuples.
        
        Returns:
            True if unsubscribed successfully.
        """
        if not self._connected or self._feed is None:
            return False
        
        # SDK unsubscribe
        try:
            instruments = []
            for symbol, exchange in symbols:
                exch_int = _exchange_to_segment_int(exchange)
                instruments.append((exch_int, symbol))
            
            self._feed.unsubscribe_symbols(instruments)
            
            with self._sub_lock:
                for sym in symbols:
                    self._subscriptions.discard(sym)
            
            logger.info("unsubscribed", extra={"count": len(symbols)})
            return True
        except Exception as exc:
            logger.warning("unsubscribe_failed", extra={"error": str(exc)})
            return False
    
    def on_tick(self, callback: Callable[[Tick], None]) -> None:
        """Register callback for incoming tick packets.
        
        Args:
            callback: Function that accepts a Tick and returns None.
        """
        self._tick_callback = callback
        logger.debug("tick_callback_registered")
    
    def is_connected(self) -> bool:
        """Check if WebSocket connection is active."""
        return self._connected and self._feed is not None
    
    # ── SDK Callbacks ────────────────────────────────────────────────────────
    
    def _run_sdk(self) -> None:
        """Run SDK event loop in background thread."""
        try:
            if self._feed:
                logger.info("Starting SDK feed.run()...")
                self._feed.run()
        except Exception as exc:
            logger.error("sdk_run_failed", extra={"error": str(exc), "exc_type": type(exc).__name__})
            import traceback
            logger.error("sdk_traceback", extra={"traceback": traceback.format_exc()})
        finally:
            self._connected = False
            logger.info("SDK feed stopped")
    
    def _on_connect(self, feed) -> None:
        """SDK callback: connection established."""
        self._connected = True
        logger.info("sdk_connected")
    
    def _on_message(self, feed, data: dict) -> None:
        """SDK callback: market data received.
        
        The SDK already parsed the binary, so we get a clean Python dict.
        """
        if not data:
            return
        
        data_type = data.get("type", "")
        
        if data_type in ("Ticker Data", "Quote Data", "Full Data"):
            try:
                tick = self._parse_sdk_data(data)
                if tick and self._tick_callback:
                    self._tick_callback(tick)
            except Exception as exc:
                logger.error("tick_parse_failed", extra={"error": str(exc)})
    
    def _on_close(self, feed) -> None:
        """SDK callback: connection closed."""
        self._connected = False
        logger.info("sdk_closed")
    
    def _on_error(self, feed, error: Any) -> None:
        """SDK callback: error occurred."""
        logger.error(
            "sdk_error",
            extra={
                "error": str(error),
                "error_repr": repr(error),
                "error_type": type(error).__name__,
            },
        )
    
    # ── Tick Parsing ─────────────────────────────────────────────────────────
    
    def _parse_sdk_data(self, data: dict[str, Any]) -> Tick | None:
        """Parse SDK market data dict into Tick domain object.
        
        Args:
            data: Dict from SDK on_message callback.
        
        Returns:
            Tick object or None if parsing fails.
        """
        try:
            symbol = data.get("symbol", "") or data.get("tradingsymbol", "")
            if not symbol:
                return None
            
            ltp = Decimal(str(data.get("last_price", data.get("ltp", "0"))))
            bid = Decimal(str(data.get("best_bid_price", data.get("bid", "0"))))
            ask = Decimal(str(data.get("best_ask_price", data.get("ask", "0"))))
            
            # Volume handling with delta computation (thread-safe)
            raw_vol = data.get("total_traded_volume", data.get("volume", 0))
            cum_vol = int(raw_vol) if raw_vol is not None else 0
            
            with self._vol_lock:
                prev_vol = self._cumulative_vols.get(symbol, cum_vol)
                delta_vol = max(0, cum_vol - prev_vol)
                self._cumulative_vols[symbol] = cum_vol
            
            # Exchange timestamp
            ts = data.get("last_trade_time", data.get("exchange_timestamp"))
            if ts is not None:
                if isinstance(ts, (int, float)):
                    exchange_ts = datetime.fromtimestamp(ts, tz=timezone.utc)
                elif isinstance(ts, str):
                    exchange_ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                else:
                    exchange_ts = datetime.now(timezone.utc)
            else:
                exchange_ts = datetime.now(timezone.utc)
            
            return Tick(
                symbol=symbol,
                ltp=ltp,
                bid=bid,
                ask=ask,
                delta_volume=delta_vol,
                cumulative_volume=cum_vol,
                exchange_timestamp=exchange_ts,
            )
        except (ValueError, TypeError, KeyError) as exc:
            logger.debug("tick_parse_error", extra={"error": str(exc)})
            return None
    
    # ── Diagnostic / Introspection ────────────────────────────────────────────
    
    @property
    def subscriptions(self) -> set[tuple[str, str]]:
        """Return current subscriptions as (symbol, exchange) tuples."""
        with self._sub_lock:
            # Convert from SDK format (exch_int, symbol, mode) back to (symbol, exchange)
            # For now, return empty set since we don't store exchange in SDK format
            # Trade_XV2 maintains this mapping separately
            return set()
    
    async def close(self) -> None:
        """Alias for disconnect for resource cleanup contexts."""
        await self.disconnect()
    
    async def __aenter__(self) -> DhanWebSocketClient:
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.disconnect()
    
    def __repr__(self) -> str:
        state = "connected" if self._connected else "disconnected"
        return (
            f"DhanWebSocketClient(state={state!r}, "
            f"instruments={len(self._subscribed_instruments)})"
        )

"""High-level Gateway wrapper with intelligent defaults and simplified API.

This module provides a user-friendly, broker-agnostic Gateway that wraps
IBrokerGateway implementations with sensible defaults, automatic credential
loading, and simplified method signatures.
"""

from __future__ import annotations

import asyncio
import logging
import os
import threading
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Callable

import pandas as pd
from dotenv import load_dotenv

from scalpr.brokers.broker_port import IBrokerGateway
from scalpr.brokers.contracts import DepthLevel, Funds, Holding, MarketDepth, Quote, Trade
from scalpr.brokers.registry import BrokerRegistry
from scalpr.domain.tick import Tick

logger = logging.getLogger(__name__)


class Gateway:
    """High-level broker-agnostic gateway with intelligent defaults.

    Provides a simplified, user-friendly API for trading operations
    with automatic credential loading and sensible parameter defaults.

    Usage::

        # Auto-load from .env
        g = Gateway()

        # Or specify broker explicitly
        g = Gateway(broker="dhan")

        # Use with intelligent defaults
        ltp = g.ltp("TCS")  # Uses exchange="NSE"
        df = g.history("TCS")  # Uses exchange="NSE", timeframe="1m", lookback_days=90
        quote = g.quote("RELIANCE")
    """

    def __init__(
        self,
        broker: str = "dhan",
        config: dict[str, Any] | None = None,
        auto_connect: bool = True,
    ) -> None:
        """Initialize Gateway with broker and configuration.

        Args:
            broker: Broker name (default: "dhan")
            config: Broker-specific config dict (auto-loaded from .env if None)
            auto_connect: Automatically connect on initialization (default: True)
        """
        self._broker_name = broker
        self._config = config or self._load_config_from_env()
        self._gateway: IBrokerGateway = BrokerRegistry.get(
            broker, self._config
        )
        self._ws_manager: Any = None
        self._ws_loop: asyncio.AbstractEventLoop | None = None
        self._ws_thread: threading.Thread | None = None
        self._stream_callbacks: list[Callable] = []

        if auto_connect:
            self._gateway.connect()
            logger.info(f"gateway_connected: {broker}")

    def _load_config_from_env(self) -> dict[str, Any]:
        """Load broker configuration from environment variables.

        Returns:
            Configuration dict with client_id and access_token
        """
        # Auto-load .env file
        load_dotenv()

        if self._broker_name == "dhan":
            from scalpr.brokers.dhan.auth import ensure_fresh_token

            client_id = os.environ.get("DHAN_CLIENT_ID", "")
            if not client_id:
                raise ValueError(
                    "DHAN_CLIENT_ID must be set in .env or environment variables"
                )

            # Auto-refreshes via TOTP if the cached token is expired
            access_token = ensure_fresh_token()

            return {
                "client_id": client_id,
                "access_token": access_token,
                # W7b: on a broker 401 the http client calls this to force
                # TOTP regeneration (the cached token looks fresh locally)
                "token_refresh_fn": lambda: ensure_fresh_token(force=True),
            }

        raise ValueError(
            f"No environment config loader for broker '{self._broker_name}'"
        )

    # ------------------------------------------------------------------
    # Market Data
    # ------------------------------------------------------------------

    def ltp(self, symbol: str, exchange: str = "NSE") -> Decimal:
        """Get Last Traded Price for a symbol.

        Args:
            symbol: Trading symbol (e.g., "TCS", "RELIANCE")
            exchange: Exchange code (default: "NSE")

        Returns:
            LTP as Decimal
        """
        return self._gateway.get_ltp(symbol, exchange)

    def quote(self, symbol: str, exchange: str = "NSE") -> Quote:
        """Get full market quote for a symbol.

        Args:
            symbol: Trading symbol
            exchange: Exchange code (default: "NSE")

        Returns:
            Quote dataclass with ltp, open, high, low, close, volume
        """
        raw_quote = self._gateway.get_quote(symbol, exchange)

        return Quote(
            symbol=symbol,
            exchange=exchange,
            ltp=Decimal(str(raw_quote.get("ltp", 0))),
            open=Decimal(str(raw_quote.get("open", 0))),
            high=Decimal(str(raw_quote.get("high", 0))),
            low=Decimal(str(raw_quote.get("low", 0))),
            close=Decimal(str(raw_quote.get("close", 0))),
            volume=int(raw_quote.get("volume", 0)),
            change=Decimal(str(raw_quote.get("change", 0))),
            change_percent=Decimal(str(raw_quote.get("change_percent", 0))),
            timestamp=None,
        )

    def depth(
        self, symbol: str, exchange: str = "NSE"
    ) -> MarketDepth:
        """Get market depth (order book) for a symbol.

        Args:
            symbol: Trading symbol
            exchange: Exchange code (default: "NSE")

        Returns:
            MarketDepth dataclass with bid/ask levels
        """
        # Delegate to connection's market_data adapter
        if hasattr(self._gateway, "connection") and hasattr(
            self._gateway.connection, "market_data"
        ):
            raw_depth = self._gateway.connection.market_data.get_depth(
                symbol, exchange
            )

            bid_levels = [
                DepthLevel(
                    price=level["price"],
                    quantity=level["quantity"],
                    orders=level["orders"],
                )
                for level in raw_depth.get("bids", [])
            ]
            ask_levels = [
                DepthLevel(
                    price=level["price"],
                    quantity=level["quantity"],
                    orders=level["orders"],
                )
                for level in raw_depth.get("asks", [])
            ]

            return MarketDepth(
                symbol=symbol,
                exchange=exchange,
                bid_levels=bid_levels,
                ask_levels=ask_levels,
            )

        raise NotImplementedError(
            f"depth() not implemented for {self._broker_name}"
        )

    def history(
        self,
        symbol: str | list[str],
        exchange: str = "NSE",
        timeframe: str = "1m",
        lookback_days: int = 90,
    ) -> pd.DataFrame:
        """Fetch historical OHLCV candlestick data.

        Args:
            symbol: Single symbol or list of symbols
            exchange: Exchange code (default: "NSE")
            timeframe: Candle interval (default: "1m")
            lookback_days: Days of history (default: 90)

        Returns:
            DataFrame with columns:
            timestamp, open, high, low, close, volume, oi, symbol, exchange, timeframe
        """
        if isinstance(symbol, str):
            symbols = [symbol]
        else:
            symbols = symbol

        all_candles = []

        for sym in symbols:
            to_date = date.today()
            from_date = to_date - timedelta(days=lookback_days)

            candles = self._gateway.get_ohlcv(
                sym, exchange, timeframe, from_date, to_date
            )

            for candle in candles:
                all_candles.append(
                    {
                        "timestamp": candle.get("timestamp"),
                        "open": float(candle.get("open", 0)),
                        "high": float(candle.get("high", 0)),
                        "low": float(candle.get("low", 0)),
                        "close": float(candle.get("close", 0)),
                        "volume": float(candle.get("volume", 0)),
                        "oi": float(candle.get("oi", 0)),
                        "symbol": sym,
                        "exchange": exchange,
                        "timeframe": timeframe,
                    }
                )

        df = pd.DataFrame(all_candles)

        # Ensure correct column order
        columns = [
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "oi",
            "symbol",
            "exchange",
            "timeframe",
        ]

        # Reorder columns if DataFrame is not empty
        if not df.empty:
            df = df[columns]

        return df

    # ------------------------------------------------------------------
    # Portfolio
    # ------------------------------------------------------------------

    def positions(self) -> list[Any]:
        """Fetch current open positions.

        Returns:
            List of Position domain objects
        """
        return self._gateway.get_positions()

    def holdings(self) -> list[Holding]:
        """Fetch long-term delivery holdings.

        Returns:
            List of Holding dataclass objects
        """
        raw_holdings = self._gateway.get_holdings()

        # Map to canonical Holding model
        holdings = []
        for pos in raw_holdings:
            holdings.append(
                Holding(
                    symbol=pos.symbol,
                    exchange=pos.exchange.value
                    if hasattr(pos.exchange, "value")
                    else str(pos.exchange),
                    quantity=pos.quantity,
                    average_price=pos.avg_price,
                    current_price=pos.ltp,
                    pnl=pos.unrealised_pnl,
                )
            )

        return holdings

    def funds(self) -> Funds:
        """Fetch available margin limits and fund details.

        Returns:
            Funds dataclass with margin details
        """
        raw_funds = self._gateway.get_fund_limits()

        return Funds(
            available_margin=Decimal(str(raw_funds.get("available_margin", 0))),
            used_margin=Decimal(str(raw_funds.get("used_margin", 0))),
            total_balance=Decimal(str(raw_funds.get("total_balance", 0))),
            collateral=Decimal(str(raw_funds.get("collateral", 0))),
            realtime=raw_funds.get("realtime", True),
        )

    # ------------------------------------------------------------------
    # Orders & Trades
    # ------------------------------------------------------------------

    def orders(self) -> list[Any]:
        """Fetch the full orderbook.

        Returns:
            List of Order domain objects
        """
        return self._gateway.get_orders()

    def trades(self) -> list[Trade]:
        """Fetch the day's tradebook (execution fills).

        Returns:
            List of Trade dataclass objects
        """
        raw_trades = self._gateway.get_tradebook()

        # Map to canonical Trade model
        trades = []
        for fill in raw_trades:
            trades.append(
                Trade(
                    trade_id=fill.fill_id,
                    order_id=fill.order_id,
                    symbol=fill.symbol,
                    exchange=fill.exchange,
                    side=fill.side,
                    quantity=fill.quantity,
                    price=fill.price,
                    timestamp=fill.timestamp,
                )
            )

        return trades

    # ------------------------------------------------------------------
    # Streaming
    # ------------------------------------------------------------------

    def stream(
        self,
        symbols: str | list[str],
        exchange: str = "NSE",
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

        # Initialize WebSocket manager if not already done
        if self._ws_manager is None:
            self._init_websocket_manager()

        # Subscribe on the manager's event loop, preserving the exchange
        asyncio.run_coroutine_threadsafe(
            self._ws_manager.subscribe_pairs([(s, exchange) for s in symbols]),
            self._ws_loop,
        ).result(timeout=15)

        logger.info(f"stream_subscribed: {symbols}")

    def stop_stream(self) -> None:
        """Stop all streaming subscriptions and the background loop."""
        if not self._ws_manager:
            return
        try:
            asyncio.run_coroutine_threadsafe(
                self._ws_manager.stop(), self._ws_loop
            ).result(timeout=15)
        except Exception as exc:
            logger.error(f"ws_manager_stop_failed: {exc}")
        finally:
            self._ws_loop.call_soon_threadsafe(self._ws_loop.stop)
            self._ws_thread.join(timeout=5)
            self._ws_loop.close()
            self._ws_manager = None
            self._ws_loop = None
            self._ws_thread = None
            self._stream_callbacks.clear()
            logger.info("stream_stopped")

    def is_streaming(self) -> bool:
        """Check if streaming is active.

        Returns:
            True if streaming is active
        """
        return self._ws_manager is not None

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
        loop that runs the async DhanWebSocketManager machinery.
        """
        try:
            from scalpr.brokers.dhan.ws_manager import DhanWebSocketManager
        except ImportError:
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
        ).result(timeout=15)
        logger.info("websocket_manager_initialized")

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def connect(self) -> None:
        """Establish connection to broker API."""
        self._gateway.connect()

    def disconnect(self) -> None:
        """Close connection and release resources."""
        self._gateway.disconnect()

    def is_connected(self) -> bool:
        """Check if gateway is connected.

        Returns:
            True if connected
        """
        return self._gateway.is_connected()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def broker_name(self) -> str:
        """Get the broker name."""
        return self._broker_name

    @property
    def gateway(self) -> IBrokerGateway:
        """Access the underlying IBrokerGateway implementation.

        Use this for advanced operations not covered by the high-level API.
        """
        return self._gateway

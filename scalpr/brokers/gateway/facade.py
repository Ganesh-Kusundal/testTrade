"""High-level Gateway facade with intelligent defaults and simplified API.

This module provides a user-friendly, broker-agnostic Gateway that wraps
IBrokerGateway implementations with sensible defaults, automatic credential
loading, and simplified method signatures.

The Gateway class is composed from multiple mixins:
- MarketDataMixin: ltp, quote, depth, history
- PortfolioMixin: positions, holdings, funds, orders, trades
- StreamingMixin: stream, stop_stream, subscribe_feed, unsubscribe
"""
from __future__ import annotations

import logging
import os
from collections.abc import Callable
from datetime import date
from decimal import Decimal
from typing import Any

from dotenv import load_dotenv

from scalpr.brokers.broker_port import IAccountPort, IBrokerGateway, IMarketDataPort, ITradingPort
from scalpr.brokers.contracts import Funds
from scalpr.brokers.errors import (
    ConfigurationError,
    InstrumentNotFound,
    TokenRefreshThrottled,
    TradingError,
)
from scalpr.brokers.gateway._market_data import MarketDataMixin
from scalpr.brokers.gateway._portfolio import PortfolioMixin
from scalpr.brokers.gateway._streaming import StreamingMixin
from scalpr.brokers.instrument_handle import InstrumentHandle
from scalpr.brokers.registry import BrokerRegistry
from scalpr.domain.instrument import Exchange, Segment, SimpleInstrumentId
from scalpr.domain.position import Position
from scalpr.domain.values import DEFAULT_EXCHANGE, RECOVERY_TIMEOUT_S

logger = logging.getLogger(__name__)


class Gateway(MarketDataMixin, PortfolioMixin, StreamingMixin):
    """High-level broker-agnostic gateway with intelligent defaults.

    Provides a simplified, user-friendly API for trading operations
    with automatic credential loading and sensible parameter defaults.

    Usage::

        # Auto-load from .env
        g = Gateway()

        # Or specify broker explicitly
        g = Gateway(broker="dhan")

        # Use with intelligent defaults
        ltp = g.ltp("TCS")  # Uses exchange=DEFAULT_EXCHANGE
        df = g.history("TCS")  # Uses exchange=DEFAULT_EXCHANGE, timeframe="1m", lookback_days=90
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

        Raises:
            TradingError: If initialization fails (with correlation_id for tracing)
        """
        self._broker_name = broker
        try:
            self._config = config or self._load_config_from_env()
        except TradingError:
            raise  # Already a TradingError — pass through with correlation_id
        except Exception as exc:
            # Wrap unexpected errors in TradingError for user-friendly output
            raise TradingError(
                f"Gateway initialization failed: {exc}",
                context={"original_error": type(exc).__name__, "broker": broker},
            ) from exc

        self._gateway: IBrokerGateway = BrokerRegistry.get(
            broker, self._config
        )
        self._ws_manager: Any = None
        self._ws_loop: Any = None
        self._ws_thread: Any = None
        self._stream_callbacks: list[Callable[..., Any]] = []
        self._ws_lock = __import__("threading").Lock()

        if auto_connect:
            try:
                self._gateway.connect()
                logger.info("gateway_connected: %s", broker)
            except TokenRefreshThrottled as exc:
                # Cooldown is actionable — re-raise with wait guidance.
                raise TradingError(
                    f"TOTP cooldown active — wait {exc.remaining_seconds:.0f}s "
                    f"before retrying. Original error: {exc}",
                    context={
                        "broker": broker,
                        "reason": "totp_cooldown",
                        "remaining_seconds": exc.remaining_seconds,
                    },
                ) from exc
            except TradingError:
                raise  # Already a TradingError — pass through
            except Exception as exc:
                raise TradingError(
                    f"Broker connection failed: {exc}",
                    context={"broker": broker},
                ) from exc

    def _load_config_from_env(self) -> dict[str, Any]:
        """Load broker configuration from environment variables.

        Returns:
            Configuration dict with client_id and access_token
        """
        # Auto-load .env file
        load_dotenv()

        if self._broker_name == "dhan":
            ensure_fresh_token = BrokerRegistry.get_adapter("dhan", "auth")
            if ensure_fresh_token is None:
                raise ConfigurationError(
                    "Dhan auth adapter not available in registry"
                )

            client_id = os.environ.get("DHAN_CLIENT_ID", "")
            if not client_id:
                raise ConfigurationError(
                    "DHAN_CLIENT_ID must be set in .env or environment variables"
                )

            # Auto-refreshes via TOTP if the cached token is expired.
            # Interactive startup path — waits out a TOTP cooldown once
            # rather than failing (auth.py owns the single sleep point).
            access_token = ensure_fresh_token(wait_for_cooldown=True)

            return {
                "client_id": client_id,
                "access_token": access_token,
            }

        raise ConfigurationError(
            f"No environment config loader for broker '{self._broker_name}'"
        )

    def instrument(
        self,
        identifier: str | SimpleInstrumentId | None = None,
        exchange: str | Exchange | None = None,
        segment: str | Segment | None = None,
    ) -> InstrumentHandle:
        """Resolve instrument and return handle with scoped operations.

        Supports two calling conventions:
        1. ``gw.instrument("TCS:NSE")`` — qualified string
        2. ``gw.instrument("TCS", Exchange.NSE)`` — separate args
        3. ``gw.instrument("TCS", "NSE")`` — string args

        Args:
            identifier: Qualified symbol ("TCS:NSE"), SimpleInstrumentId, or plain symbol
            exchange: Exchange enum or string (e.g., Exchange.NSE, "NSE", "MCX")
            segment: Segment enum or string (e.g., Segment.INDEX, "INDEX")

        Returns:
            InstrumentHandle with .historical(), .quote(), .ltp(), .depth()

        Usage::

            tcs = gw.instrument("TCS:NSE")
            tcs = gw.instrument("TCS", Exchange.NSE)
            nifty = gw.instrument("NIFTY", Exchange.NSE, Segment.INDEX)
            candles = tcs.historical(interval="1D", start="2025-01-01")
            quote = tcs.quote()
        """
        conn = self._gateway.connection
        if conn is None:
            raise NotImplementedError(
                "instrument() requires a broker that provides adapters"
            )

        # Resolve symbol and exchange from the calling convention
        symbol: str
        exch_str: str

        if isinstance(identifier, SimpleInstrumentId):
            symbol = identifier.symbol
            exch_str = identifier.exchange.value
        elif isinstance(identifier, str) and ":" in identifier and exchange is None:
            # Qualified string "TCS:NSE"
            inst_id = SimpleInstrumentId.parse(identifier)
            symbol = inst_id.symbol
            exch_str = inst_id.exchange.value
        elif isinstance(identifier, str):
            symbol = identifier
            if exchange is None:
                exch_str = "NSE"
            elif isinstance(exchange, Exchange):
                exch_str = exchange.value
            else:
                exch_str = str(exchange)
        else:
            raise ValueError(
                f"identifier must be a string or SimpleInstrumentId, got {type(identifier).__name__}"
            )

        try:
            resolved = conn.resolver.resolve_full(symbol, exch_str)
        except InstrumentNotFound as exc:
            raise InstrumentNotFound(str(exc)) from exc

        # Build option chain adapter via shared helper
        oc_adapter = self._get_option_chain_adapter()

        # WS manager/loop may not be initialised yet (first subscribe
        # triggers _init_websocket_manager). Pass what we have.
        ws_mgr = None
        ws_loop = None
        if self._ws_manager is not None:
            ws_mgr, ws_loop = self._ws_manager, self._ws_loop

        return InstrumentHandle(
            resolved=resolved,
            market_data_adapter=conn.market_data,
            historical_adapter=conn.historical,
            option_chain_adapter=oc_adapter,
            ws_manager=ws_mgr,
            ws_loop=ws_loop,
        )

    def option_chain(
        self,
        underlying: str,
        exchange: str = DEFAULT_EXCHANGE,
        expiry: date | None = None,
        as_df: bool = True,
    ) -> Any:
        """Fetch the option chain for an underlying.

        Args:
            underlying: Underlying symbol (e.g. "NIFTY", "SENSEX").
            exchange: Exchange code (default: "NSE").
            expiry: Specific expiry date. If *None*, the next available
                    expiry is resolved automatically.
            as_df: If True (default), return Tradehull-compatible
                ``(atm_strike, DataFrame)`` tuple with 27 columns.
                If False, return flat ``list[dict]``.

        Returns:
            When as_df=True: ``(atm_strike, pd.DataFrame)``
            When as_df=False: flat list of dicts.

        Raises:
            InstrumentNotFound: if the underlying cannot be resolved.
        """
        adapter = self._get_option_chain_adapter()
        try:
            chain = adapter.get_option_chain(underlying, exchange, expiry=expiry)
        except InstrumentNotFound as exc:
            raise InstrumentNotFound(str(exc)) from exc

        if not as_df:
            return chain

        # Pivot to Tradehull-compatible DataFrame via adapter
        return adapter.pivot_to_dataframe(chain, underlying, exchange)

    def future_script(
        self,
        underlying: str,
        exchange: str = DEFAULT_EXCHANGE,
        expiry_idx: int = 0,
    ) -> str:
        """Get the future trading symbol for an underlying.

        Args:
            underlying: Underlying symbol (e.g. "NIFTY", "RELIANCE").
            exchange: Exchange code (default: "NSE").
            expiry_idx: 0=nearest, 1=next, etc.

        Returns:
            Trading symbol string (e.g. "NIFTY 25 JUL 26 FUT").
        """
        adapter = self._get_option_chain_adapter()
        return adapter.get_future_symbol(underlying, exchange, expiry_idx)  # type: ignore[no-any-return]

    def strike_selection(
        self,
        underlying: str,
        exchange: str = DEFAULT_EXCHANGE,
        expiry: date | None = None,
        mode: str = "ATM",
        count: int = 10,
    ) -> list[Any]:
        """Select option strikes by moneyness (ATM/ITM/OTM).

        Args:
            underlying: Underlying symbol (e.g. "NIFTY").
            exchange: Exchange code (default: "NSE").
            expiry: Specific expiry date (None = next expiry).
            mode: "ATM", "ITM", "OTM", or combined ("ITM,OTM").
            count: Strikes per mode direction.

        Returns:
            Sorted list of Decimal strike prices.
        """
        conn = self._gateway.connection
        adapter = self._get_option_chain_adapter()

        # Get spot price from connection's market_data adapter
        spot = Decimal("0")
        if conn is not None and hasattr(conn, "market_data"):
            try:
                resolved = conn.resolver.resolve_full(underlying, exchange)
                spot = Decimal(str(
                    conn.market_data.get_ltp_by_id(
                        resolved.security_id,
                        conn.resolver.wire_segment_of(underlying, exchange),
                        symbol=underlying,
                    )
                ))
            except Exception:
                logger.debug("strike_selection_spot_fetch_failed", exc_info=True)

        return adapter.select_strikes(  # type: ignore[no-any-return]
            underlying, exchange, expiry=expiry,
            mode=mode, count=count,
            spot_price=spot if spot > 0 else None,
        )

    def option_greeks(
        self,
        underlying: str,
        strike: Decimal,
        expiry: date,
        option_type: str,
        exchange: str = DEFAULT_EXCHANGE,
    ) -> dict[str, Any] | None:
        """Get greeks for a specific option.

        Args:
            underlying: Underlying symbol (e.g. "NIFTY").
            strike: Strike price.
            expiry: Expiry date.
            option_type: "CE" or "PE".
            exchange: Exchange code (default: "NSE").

        Returns:
            Dict with greeks or None.
        """
        adapter = self._get_option_chain_adapter()
        return adapter.get_option_greeks(  # type: ignore[no-any-return]
            underlying, exchange, strike, expiry, option_type
        )

    def _get_option_chain_adapter(self) -> Any:
        """Create an OptionChainAdapter via registry (no direct Dhan import)."""
        conn = self._gateway.connection
        if conn is None:
            raise NotImplementedError(
                "This operation requires a broker that provides adapters"
            )
        OptionChainAdapter = BrokerRegistry.get_adapter(
            self._broker_name, "option_chain"
        )
        if OptionChainAdapter is None:
            raise NotImplementedError(
                f"option_chain adapter not available for {self._broker_name}"
            )
        return OptionChainAdapter(conn.http_client, conn.resolver)

    def close(self) -> None:
        """Shut down WebSocket connections and release resources."""
        with self._ws_lock:
            if self._ws_manager is not None:
                manager = self._ws_manager
                loop = self._ws_loop
                try:
                    if loop is not None and loop.is_running():
                        __import__("asyncio").run_coroutine_threadsafe(
                            manager.stop(), loop,
                        ).result(timeout=RECOVERY_TIMEOUT_S)
                except Exception:
                    logger.warning("ws_close_failed", exc_info=True)
                self._ws_manager = None
                self._ws_loop = None

        self._stream_callbacks.clear()
        logger.info("gateway_closed")

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
    # Account delegation — LoD-compliant wrappers
    # ------------------------------------------------------------------

    def get_positions(self) -> list[Position]:
        """Fetch current open positions.

        Delegates to the underlying broker gateway's portfolio adapter.
        """
        return self._gateway.get_positions()

    def get_margins(self) -> Funds:
        """Fetch available margin limits and fund details.

        Returns a Funds dataclass with available_margin, total_balance, etc.
        """
        return self.funds()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Typed port accessors — use these instead of adapters() dict
    # ------------------------------------------------------------------

    @property
    def trading(self) -> ITradingPort:
        """Access the trading port (order lifecycle).

        Provides typed access to order operations without coupling
        callers to the full IBrokerGateway interface.
        """
        return self._gateway

    @property
    def market_data(self) -> IMarketDataPort:
        """Access the market data port (quotes, LTP, history).

        Provides typed access to market data operations.
        """
        return self._gateway

    @property
    def account(self) -> IAccountPort:
        """Access the account port (positions, holdings, margins).

        Provides typed access to account/portfolio operations.
        """
        return self._gateway

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

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
from datetime import date
from typing import Any

from dotenv import load_dotenv

from scalpr.brokers.broker_port import IBrokerGateway
from scalpr.brokers.errors import InstrumentNotFound
from scalpr.brokers.gateway._market_data import MarketDataMixin
from scalpr.brokers.gateway._portfolio import PortfolioMixin
from scalpr.brokers.gateway._streaming import StreamingMixin
from scalpr.brokers.instrument_handle import InstrumentHandle
from scalpr.brokers.registry import BrokerRegistry
from scalpr.domain.instrument import Exchange, Segment, SimpleInstrumentId
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
        """
        self._broker_name = broker
        self._config = config or self._load_config_from_env()
        self._gateway: IBrokerGateway = BrokerRegistry.get(
            broker, self._config
        )
        self._ws_manager: Any = None
        self._ws_loop: Any = None
        self._ws_thread: Any = None
        self._stream_callbacks: list[Any] = []
        self._ws_lock = __import__("threading").Lock()

        if auto_connect:
            self._gateway.connect()
            logger.info("gateway_connected: %s", broker)

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
                raise ValueError(
                    "Dhan auth adapter not available in registry"
                )

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
        adapters = self._gateway.adapters()
        if not adapters:
            raise NotImplementedError(
                "instrument() requires a broker that provides adapters"
            )
        conn = adapters["connection"]

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

        # Build option chain adapter (shared connection, lazy per-call)
        # Build option chain adapter via registry (no direct Dhan import)
        OptionChainAdapter = BrokerRegistry.get_adapter(
            self._broker_name, "option_chain"
        )
        if OptionChainAdapter is None:
            raise NotImplementedError(
                f"option_chain adapter not available for {self._broker_name}"
            )
        oc_adapter = OptionChainAdapter(conn.http_client, conn.resolver)

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
        adapters = self._gateway.adapters()
        if not adapters:
            raise NotImplementedError(
                "option_chain() requires a broker that provides adapters"
            )
        # Get OptionChainAdapter via registry (no direct Dhan import)
        OptionChainAdapter = BrokerRegistry.get_adapter(
            self._broker_name, "option_chain"
        )
        if OptionChainAdapter is None:
            raise NotImplementedError(
                f"option_chain adapter not available for {self._broker_name}"
            )
        adapter = OptionChainAdapter(adapters["http_client"], adapters["resolver"])
        try:
            chain = adapter.get_option_chain(underlying, exchange, expiry=expiry)
        except InstrumentNotFound as exc:
            raise InstrumentNotFound(str(exc)) from exc

        if not as_df:
            return chain

        # Pivot to Tradehull-compatible DataFrame
        return self._pivot_option_chain(chain, adapters, underlying, exchange)

    def _pivot_option_chain(
        self,
        chain: list[dict],
        adapters: dict,
        underlying: str,
        exchange: str,
    ) -> tuple[Any, Any]:
        """Pivot flat option chain into Tradehull-compatible DataFrame."""
        from decimal import Decimal

        import pandas as pd

        if not chain:
            return Decimal("0"), pd.DataFrame()

        # Get spot price for ATM calculation
        market_data = adapters.get("market_data")
        resolver = adapters["resolver"]
        spot = Decimal("0")
        if market_data is not None:
            try:
                resolved = resolver.resolve(underlying, exchange)
                spot = Decimal(str(
                    market_data.get_ltp_by_id(
                        resolved.security_id,
                        resolver.wire_segment_of(underlying, exchange),
                        symbol=underlying,
                    )
                ))
            except Exception:
                logger.debug("option_chain_spot_fetch_failed", exc_info=True)

        strikes = sorted({Decimal(str(leg["strike"])) for leg in chain})
        if spot > 0 and strikes:
            atm_strike = min(strikes, key=lambda s: abs(s - spot))
        else:
            atm_strike = strikes[len(strikes) // 2] if strikes else Decimal("0")

        # Default 10 strikes around ATM (matches Tradehull)
        if strikes and atm_strike:
            atm_idx = strikes.index(atm_strike) if atm_strike in strikes else len(strikes) // 2
            lo = max(0, atm_idx - 10)
            hi = min(len(strikes), atm_idx + 11)
            selected = set(strikes[lo:hi])
            chain = [leg for leg in chain if Decimal(str(leg["strike"])) in selected]

        by_strike: dict = {}
        for leg in chain:
            strike = Decimal(str(leg["strike"]))
            opt_type = leg.get("option_type", "")
            by_strike.setdefault(strike, {})[opt_type] = leg

        rows = []
        for strike in sorted(by_strike):
            ce = by_strike[strike].get("CE", {})
            pe = by_strike[strike].get("PE", {})
            rows.append({
                "CE OI": ce.get("oi"), "CE Chg in OI": (ce.get("oi", 0) or 0) - (ce.get("previous_oi", 0) or 0),
                "CE Volume": ce.get("volume"), "CE IV": ce.get("iv"), "CE LTP": ce.get("ltp"),
                "CE Bid Qty": ce.get("bid_qty"), "CE Bid": ce.get("bid"),
                "CE Ask": ce.get("ask"), "CE Ask Qty": ce.get("ask_qty"),
                "CE Delta": ce.get("delta"), "CE Theta": ce.get("theta"),
                "CE Gamma": ce.get("gamma"), "CE Vega": ce.get("vega"),
                "Strike Price": strike,
                "PE Bid Qty": pe.get("bid_qty"), "PE Bid": pe.get("bid"),
                "PE Ask": pe.get("ask"), "PE Ask Qty": pe.get("ask_qty"),
                "PE LTP": pe.get("ltp"), "PE IV": pe.get("iv"),
                "PE Volume": pe.get("volume"),
                "PE Chg in OI": (pe.get("oi", 0) or 0) - (pe.get("previous_oi", 0) or 0),
                "PE OI": pe.get("oi"),
                "PE Delta": pe.get("delta"), "PE Theta": pe.get("theta"),
                "PE Gamma": pe.get("gamma"), "PE Vega": pe.get("vega"),
            })

        return atm_strike, pd.DataFrame(rows)

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

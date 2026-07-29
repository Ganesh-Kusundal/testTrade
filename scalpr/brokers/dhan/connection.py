"""Dhan connection orchestrator — lifecycle management and adapter coordination.

Creates and owns the shared DhanHttpClient, SymbolResolver, and all domain
adapters (market_data, orders, portfolio, historical). Manages connection
lifecycle with thread-safe initialisation and authentication.

As Uncle Bob says: "Clean boundaries between strategy, signals, orders, and risk."
The connection owns the broker boundary — nothing more, nothing less.
"""

from __future__ import annotations

import logging
import threading
from typing import Any

from config.endpoints import Dhan
from scalpr.brokers.dhan._token_lifecycle import TokenRefreshScheduler
from scalpr.brokers.dhan._totp_cooldown import TotpRateLimitError
from scalpr.brokers.dhan.auth import ensure_fresh_token, get_broadcast
from scalpr.brokers.dhan.exceptions import AuthenticationError, BrokerError, ConfigurationError
from scalpr.brokers.dhan.historical import HistoricalDataAdapter
from scalpr.brokers.dhan.http_client import CircuitBreaker, DhanHttpClient
from scalpr.brokers.dhan.loader import InstrumentLoader
from scalpr.brokers.dhan.market_data import MarketDataAdapter
from scalpr.brokers.dhan.orders import OrdersAdapter
from scalpr.brokers.dhan.portfolio import PortfolioAdapter
from scalpr.brokers.dhan.resolution import SymbolResolver
from scalpr.domain.values import RECOVERY_TIMEOUT_S

logger = logging.getLogger(__name__)


class DhanConnection:
    """Orchestrates all Dhan broker adapters behind a single connection.

    Responsibilities:
    - Manage HTTP client lifecycle (connect / disconnect)
    - Initialise and coordinate all adapters with shared dependencies
    - Handle authentication failures with token refresh
    - Provide thread-safe access to adapters
    - Track connection state

    Usage::

        connection = DhanConnection({
            "client_id": "...",
            "access_token": "...",
        })
        connection.connect()
        ltp = connection.market_data.get_ltp("RELIANCE", "NSE")
        positions = connection.portfolio.get_positions()
        connection.disconnect()
    """

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialise DhanConnection with configuration.

        Args:
            config: Dictionary with required keys:
                - client_id (str): Dhan client ID
                - access_token (str): Dhan access token
                Optional keys:
                - base_url (str): Override REST base URL (default: Dhan.REST_BASE)
                - timeout (float): HTTP timeout in seconds (default: 15.0)
                - token_refresh_fn (callable): Function to refresh expired tokens
                - enable_retry (bool): Enable automatic retry (default: True)
                - instruments_force_refresh (bool): Force re-download instrument CSV

        Raises:
            ConfigurationError: If required config keys are missing.
        """
        self._config = config
        self._validate_config()

        self._client: DhanHttpClient | None = None
        self._resolver: SymbolResolver | None = None
        self._market_data: MarketDataAdapter | None = None
        self._orders: OrdersAdapter | None = None
        self._portfolio: PortfolioAdapter | None = None
        self._historical: HistoricalDataAdapter | None = None

        self._connected = False
        self._lock = threading.RLock()
        self._scheduler: TokenRefreshScheduler | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def connect(self) -> None:
        """Establish connection to Dhan API and initialise all adapters.

        Steps:
        1. Create DhanHttpClient with auth headers
        2. Load instrument master and build SymbolResolver
        3. Initialise all domain adapters with shared client + resolver
        4. Test connection via /profile endpoint
        5. Mark connection as active

        Raises:
            BrokerError: If any step fails.
            AuthenticationError: If token is invalid.
        """
        with self._lock:
            if self._connected:
                logger.debug("dhan_connection_already_connected")
                return

            logger.info("dhan_connection_connecting")

            try:
                # Step 1: Create HTTP client
                self._client = self._create_http_client()

                # Step 2: Load instruments and build resolver
                self._resolver = self._create_resolver()

                # Step 3: Initialise adapters
                self._market_data = MarketDataAdapter(self._client, self._resolver)
                self._orders = OrdersAdapter(self._client, self._resolver)
                self._portfolio = PortfolioAdapter(self._client, self._resolver)
                self._historical = HistoricalDataAdapter(self._client, self._resolver)

                # Step 4: Test connection
                self._verify_connection()

                # Step 5: Mark active
                self._connected = True

                # Step 6: Start background token refresh scheduler
                import os
                self._scheduler = TokenRefreshScheduler(
                    broker_id="dhan",
                    ensure_token_fn=lambda: ensure_fresh_token(),
                    current_token_fn=lambda: os.environ.get("DHAN_ACCESS_TOKEN", ""),
                    broadcast=get_broadcast(),
                    interval_seconds=300.0,
                )
                self._scheduler.start()

                logger.info("dhan_connection_connected")

            except (AuthenticationError, TotpRateLimitError):
                raise
            except Exception as exc:
                # Clean up partial initialisation
                self._cleanup()
                raise BrokerError(f"Dhan connection failed: {exc}") from exc

    def disconnect(self) -> None:
        """Close connection and release resources.

        Safe to call multiple times. Closes the HTTP session and clears
        adapter references. After disconnect, call connect() to re-establish.
        """
        with self._lock:
            if not self._connected:
                logger.debug("dhan_connection_already_disconnected")
                return

            logger.info("dhan_connection_disconnecting")
            if self._scheduler is not None:
                self._scheduler.stop()
                self._scheduler = None
            self._cleanup()
            self._connected = False
            logger.info("dhan_connection_disconnected")

    def is_connected(self) -> bool:
        """Check if the connection is active.

        Returns:
            True if connected and ready, False otherwise.
        """
        return self._connected

    # ------------------------------------------------------------------
    # Adapter access
    # ------------------------------------------------------------------

    @property
    def market_data(self) -> MarketDataAdapter:
        """Access market data adapter.

        Raises:
            BrokerError: If not connected.
        """
        if self._market_data is None:
            raise BrokerError("Market data adapter not initialised — call connect() first")
        return self._market_data

    @property
    def orders(self) -> OrdersAdapter:
        """Access orders adapter.

        Raises:
            BrokerError: If not connected.
        """
        if self._orders is None:
            raise BrokerError("Orders adapter not initialised — call connect() first")
        return self._orders

    @property
    def portfolio(self) -> PortfolioAdapter:
        """Access portfolio adapter.

        Raises:
            BrokerError: If not connected.
        """
        if self._portfolio is None:
            raise BrokerError("Portfolio adapter not initialised — call connect() first")
        return self._portfolio

    @property
    def historical(self) -> HistoricalDataAdapter:
        """Access historical data adapter.

        Raises:
            BrokerError: If not connected.
        """
        if self._historical is None:
            raise BrokerError("Historical data adapter not initialised — call connect() first")
        return self._historical

    @property
    def resolver(self) -> SymbolResolver:
        """Access symbol resolver.

        Raises:
            BrokerError: If not connected.
        """
        if self._resolver is None:
            raise BrokerError("Symbol resolver not initialised — call connect() first")
        return self._resolver

    @property
    def http_client(self) -> DhanHttpClient:
        """Access the underlying HTTP client.

        Raises:
            BrokerError: If not connected.
        """
        if self._client is None:
            raise BrokerError("HTTP client not initialised — call connect() first")
        return self._client

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _validate_config(self) -> None:
        """Validate required configuration keys."""
        required = ("client_id", "access_token")
        missing = [key for key in required if not self._config.get(key)]
        if missing:
            raise ConfigurationError(
                f"Missing required config keys: {', '.join(missing)}"
            )

    def _create_http_client(self) -> DhanHttpClient:
        """Create and configure the shared HTTP client."""
        client_id: str = self._config["client_id"]
        access_token: str = self._config["access_token"]
        base_url: str = self._config.get("base_url", Dhan.REST_BASE)
        timeout: float = float(self._config.get("timeout", 15.0))
        token_refresh_fn = self._config.get("token_refresh_fn")
        enable_retry: bool = self._config.get("enable_retry", True)

        circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=RECOVERY_TIMEOUT_S,
        )

        client = DhanHttpClient(
            client_id=client_id,
            access_token=access_token,
            base_url=base_url,
            timeout=timeout,
            token_refresh_fn=token_refresh_fn,
            enable_retry=enable_retry,
            circuit_breaker=circuit_breaker,
        )

        logger.info(
            "dhan_http_client_created",
            extra={"client_id": client_id, "base_url": base_url},
        )
        return client

    def _create_resolver(self) -> SymbolResolver:
        """Load instrument master and build the symbol resolver."""
        force_refresh: bool = self._config.get("instruments_force_refresh", False)

        logger.info("dhan_loading_instruments")
        rows = InstrumentLoader.load_cached(force_refresh=force_refresh)

        resolver = SymbolResolver()
        stats = resolver.load_from_rows(rows)

        logger.info(
            "dhan_resolver_loaded",
            extra={"total": stats["total"], "skipped": stats["skipped"]},
        )
        return resolver

    def _verify_connection(self) -> None:
        """Verify the connection and validate account setup.

        Checks:
        - /profile endpoint is reachable
        - dataPlan status (warns if inactive)
        - token validity
        - active segments

        On 401 (token rejected), force-regenerates via TOTP and retries.
        If TOTP cooldown is active, sleeps for the remaining cooldown
        duration before retrying — this avoids the death spiral where
        rapid retries burn through the 120s TOTP lockout.

        Raises:
            AuthenticationError: If token is rejected after all retries.
            BrokerError: If the profile call fails.
        """
        if self._client is None:
            raise BrokerError("HTTP client not available for verification")

        import time

        max_attempts = 3
        last_exc: Exception | None = None

        for attempt in range(1, max_attempts + 1):
            try:
                profile = self._client.get("/profile")

                # Validate data plan
                data_plan = profile.get("dataPlan", "")
                if data_plan.lower() != "active":
                    logger.warning(
                        "dhan_data_plan_inactive",
                        extra={"dataPlan": data_plan},
                    )
                    # Don't raise - user might only need order APIs

                # Validate token validity
                token_validity = profile.get("dataValidity", "")
                if not token_validity:
                    logger.warning("dhan_token_validity_missing")

                # Log active segments
                active_segments = profile.get("activeSegment", [])

                logger.info(
                    "dhan_connection_verified",
                    extra={
                        "profile": profile.get("name", ""),
                        "dataPlan": data_plan,
                        "activeSegments": active_segments,
                        "tokenValidity": token_validity,
                    },
                )
                return  # Success

            except TotpRateLimitError as exc:
                # TOTP cooldown active — sleep for the remaining cooldown
                # then retry. This is the key fix: instead of burning
                # through retries in <5s, we wait for the cooldown.
                last_exc = exc
                if attempt < max_attempts:
                    wait = exc.remaining_seconds + 1.0  # +1s buffer
                    logger.warning(
                        "dhan_verify_totp_cooldown",
                        extra={
                            "attempt": attempt,
                            "wait_seconds": round(wait, 1),
                        },
                    )
                    time.sleep(wait)
                    new_token = ensure_fresh_token(force=True)
                    self._client.update_token(new_token)
                    continue
                raise

            except AuthenticationError as exc:
                last_exc = exc
                if attempt < max_attempts:
                    logger.warning(
                        "dhan_verify_retry",
                        extra={"attempt": attempt, "error": str(exc)},
                    )
                    time.sleep(2)
                    # 401 = token rejected by broker. Force regeneration
                    # regardless of JWT expiry — a broker rejection means
                    # the token is invalid even if it hasn't expired locally.
                    # The HTTP client already attempted a forced refresh on
                    # its own 401, but if we're still here the token is
                    # persistently rejected — force another regeneration.
                    new_token = ensure_fresh_token(force=True)
                    self._client.update_token(new_token)
                    continue
                raise

        if last_exc:
            raise last_exc

    def _cleanup(self) -> None:
        """Release all resources."""
        if self._client is not None:
            try:
                self._client.close()
            except Exception as exc:
                logger.warning("dhan_client_close_failed", extra={"error": str(exc)})

        self._client = None
        self._resolver = None
        self._market_data = None
        # Clear idempotency cache on disconnect (EOD cleanup)
        if self._orders is not None:
            self._orders.clear_idempotency_cache()
        self._orders = None
        self._portfolio = None
        self._historical = None

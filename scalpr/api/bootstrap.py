"""Composition root — wires all dependencies and creates the FastAPI app.

No side effects at import time. All initialization happens in create_app().
Trading wiring (strategies, feed, OMS) is gated behind SCALPR_TRADING_ENABLED=1
+ SCALPR_WATCHLIST so plain API boots remain unchanged.
"""
from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from scalpr.execution.order_router import OrderRouter
    from scalpr.strategy.executor import StrategyExecutor

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.secrets_manager import SecretsManager

logger = logging.getLogger(__name__)


def _load_dotenv() -> None:
    """Load environment variables. Called inside create_app, not at import."""
    from dotenv import load_dotenv
    load_dotenv()


def _create_gateway() -> tuple[Any, str | None]:
    """Create and configure the DhanClient.

    Returns (client, error) — a DhanClient. Falls back gracefully: the
    API still boots without broker credentials, returning 503 on broker
    endpoints.
    """
    from scalpr.adapters.dhan.client import DhanClient
    from scalpr.engine.clock import LiveClock
    from scalpr.engine.message_bus import MessageBus

    sm = SecretsManager()
    client_id = sm.get_dhan_client_id()
    access_token = sm.get_dhan_access_token()
    if not client_id or not access_token:
        logger.info("Dhan credentials missing — API will start without broker")
        return None, "Dhan credentials not configured"

    try:
        clock = LiveClock()
        bus = MessageBus()
        client = DhanClient(bus, clock, {
            "client_id": client_id,
            "access_token": access_token,
            "totp_secret": sm.get_dhan_totp_secret() or "",
            "pin": sm.get_dhan_pin() or "1111",
            "csv_path": "instrument.csv",
        })
        return client, None
    except Exception as e:
        logger.error("DhanClient creation failed: %s", e)
        return None, str(e)


def _create_event_system(existing_client: Any = None) -> dict | None:
    """Create the new event-driven system: MessageBus + ExecutionEngine + DhanClient.

    When *existing_client* is provided (from _create_gateway), it is reused
    to avoid duplicating the connection. Returns None when no DhanClient is
    available (e.g. credentials missing).
    """
    from scalpr.engine.execution_engine import ExecutionEngine

    if existing_client is not None:
        clock = existing_client._clock
        bus = existing_client._bus
        engine = ExecutionEngine(bus=bus, clock=clock)
        engine.start()
        logger.info("event_system_reused_from_gateway: bus=%s engine=%s client=%s",
                    id(bus), id(engine), id(existing_client))
        return {"clock": clock, "bus": bus, "engine": engine, "client": existing_client}


    sm = SecretsManager()
    client_id = sm.get_dhan_client_id()
    access_token = sm.get_dhan_access_token()

    if not client_id or not access_token:
        logger.info("Dhan credentials missing — event system disabled")
        return None

    from scalpr.adapters.dhan.client import DhanClient
    from scalpr.engine.clock import LiveClock
    from scalpr.engine.message_bus import MessageBus

    clock = LiveClock()
    bus = MessageBus()
    engine = ExecutionEngine(bus=bus, clock=clock)
    engine.start()

    dhan_pin = sm.get_dhan_pin() or "1111"
    client = DhanClient(bus, clock, {
        "client_id": client_id,
        "access_token": access_token,
        "totp_secret": sm.get_dhan_totp_secret() or "",
        "pin": dhan_pin,
        "csv_path": "instrument.csv",
    })
    client.start()

    logger.info("event_system_ready: bus=%s engine=%s client=%s",
                id(bus), id(engine), id(client))
    return {"clock": clock, "bus": bus, "engine": engine, "client": client}


@dataclass
class AppContext:
    """The wired trading object graph."""
    order_router: OrderRouter | None
    executor: StrategyExecutor | None


@dataclass
class Dependencies:
    """Optional pre-built dependency overrides for the trading object graph.

    Each field defaults to None, which means ``wire()`` constructs the default
    implementation.  Pass a pre-built instance (or MagicMock) to swap in
    alternatives — useful in tests or when wiring a different broker backend.
    """
    risk_gate: Any = None
    circuit_breaker: Any = None
    oms_repository: Any = None
    event_store: Any = None
    order_manager: Any = None
    order_router: Any = None
    strategy_executor: Any = None


def wire(
    gateway: Any,
    watchlist: list[str],
    db_path: str = "data/oms.db",
    events_db_path: str = "data/events.db",
    deps: Dependencies | None = None,
) -> AppContext:
    """Build the trading object graph: risk gates, OMS, router, strategies.

    Args:
        gateway: IBrokerGateway port (has get_positions/get_margins/place_order).
        watchlist: Symbols to run one ScalprAmtStrategy each.
        db_path: SQLite path for OMS persistence.
        events_db_path: SQLite path for the domain event audit log.
        deps: Optional dependency overrides. Each field, if not None, replaces
              the default construction for that component.
    """
    from datetime import datetime

    from scalpr.execution.order_router import OrderRouter
    from scalpr.observability.event_store import EventStore
    from scalpr.oms.order_manager import OrderManager
    from scalpr.oms.persistence import OmsRepository
    from scalpr.risk.circuit_breaker import CircuitBreaker
    from scalpr.risk.pre_trade import PreTradeRiskGate
    from scalpr.strategy.executor import StrategyExecutor
    from scalpr.strategy.scalpr_amt import ScalprAmtStrategy

    deps = deps or Dependencies()

    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    session_id = datetime.now(timezone.utc).strftime("live-%Y%m%d")

    # Kill switch: live order placement is HALTED by default.
    # Set SCALPR_LIVE_ORDERS=1 to explicitly enable. This is the safety-critical
    # default — without it, the only way to stop live trading is to kill the process.
    live_orders_enabled = os.environ.get("SCALPR_LIVE_ORDERS") == "1"
    risk_gate = deps.risk_gate if deps.risk_gate is not None else PreTradeRiskGate(halted=not live_orders_enabled)
    if not live_orders_enabled:
        logger.warning(
            "SCALPR_LIVE_ORDERS is not set to '1' — risk gate HALTED, "
            "all orders will be rejected. Set SCALPR_LIVE_ORDERS=1 to enable."
        )

    circuit_breaker = deps.circuit_breaker if deps.circuit_breaker is not None else CircuitBreaker()
    oms_repository = deps.oms_repository if deps.oms_repository is not None else OmsRepository(db_path)
    event_store = deps.event_store if deps.event_store is not None else EventStore(db_path=events_db_path)
    order_manager = deps.order_manager if deps.order_manager is not None else OrderManager(
        oms_repository,
        event_store=event_store,
        session_id=session_id,
    )
    order_router = deps.order_router if deps.order_router is not None else OrderRouter(
        gateway=gateway,
        risk_gate=risk_gate,
        circuit_breaker=circuit_breaker,
        order_manager=order_manager,
    )
    executor = deps.strategy_executor if deps.strategy_executor is not None else StrategyExecutor()
    for symbol in watchlist:
        executor.register_strategy(ScalprAmtStrategy(order_router, symbol))
    return AppContext(order_router=order_router, executor=executor)


def _watchlist_from_env() -> list[str]:
    return [s.strip() for s in os.environ.get("SCALPR_WATCHLIST", "").split(",") if s.strip()]


async def _start_trading(app: FastAPI) -> None:
    """Wire strategies and start the live tick feed (lifespan startup).

    Uses the new event-driven system (DhanClient WS) when available,
    falls back to the old DhanWebSocketManager for backward compat.
    """
    watchlist = _watchlist_from_env()
    gateway = app.state.gateway
    event_system = app.state.event_system

    if not watchlist:
        logger.error("trading_enabled_but_no_watchlist")
        return
    if gateway is None and event_system is None:
        logger.error("trading_enabled_but_no_broker")
        return

    if event_system is not None:
        client = event_system["client"]

        # Subscribe all watchlist symbols via the high-level API
        specs = [(s, "NSE", "quote", None) for s in watchlist]
        specs += [(s, "NSE", "depth", 20) for s in watchlist[:5]]
        client.subscribe_batch(specs)

        # Bridge WS ticks to strategy executor
        if gateway is not None:
            ctx = wire(gateway, watchlist)
            loop = asyncio.get_running_loop()
            event_system["bus"].subscribe(
                "market.quote.dhan",
                lambda t: asyncio.run_coroutine_threadsafe(ctx.executor.on_tick(t), loop),
            )
            app.state.executor = ctx.executor
            app.state.order_router = ctx.order_router

        # Log subscription status
        status = client.subscription_status()
        logger.info("subscription_status: %s", status)
        logger.info("trading_wired_event_system: %s watchlist=%s", watchlist)
        return

    # Fallback path (no event system)
    if gateway is not None:
        client = gateway
        for symbol in watchlist:
            client.subscribe(symbol, "NSE", type="quote")
        if hasattr(client, 'subscribe_batch'):
            specs = [(s, "NSE", "depth", 20) for s in watchlist[:5]]
            client.subscribe_batch(specs)
        ctx = wire(gateway, watchlist)
        loop = asyncio.get_running_loop()
        client._bus.subscribe(
            "market.quote.dhan",
            lambda t: asyncio.run_coroutine_threadsafe(ctx.executor.on_tick(t), loop),
        )
        app.state.executor = ctx.executor
        app.state.order_router = ctx.order_router
        logger.info("trading_wired_legacy: %s", watchlist)


def _create_candle_provider(gateway: Any) -> Any:
    """Create a candle provider from the gateway.

    Uses DhanClient._historical when available; falls back to
    gateway.connection.historical for backward compat with tests / mocks.
    Returns None if unavailable (fail-closed — replay returns 503).
    """
    if gateway is None:
        return None

    from scalpr.adapters.dhan.client import DhanClient

    if isinstance(gateway, DhanClient):
        hist = gateway._historical
    else:
        conn = getattr(gateway, 'connection', None)
        if conn is None:
            return None
        hist = getattr(conn, 'historical', None)
    if hist is None:
        return None

    try:
        from scalpr.api.models import Candle
    except Exception as e:
        logger.warning("replay candle provider unavailable: %s", e)
        return None

    def provider(symbol: str, exchange: str, timeframe: str, date_str: str) -> list[Candle]:
        try:
            d = datetime.fromisoformat(date_str).date()
        except ValueError:
            logger.error("replay_provider_invalid_date: %s", date_str)
            return []

        candles = hist.get_ohlcv(
            symbol=symbol,
            exchange=exchange,
            timeframe=timeframe,
            from_date=d,
            to_date=d,
        )
        return [
            Candle(
                t=int(c["timestamp"].timestamp() * 1000),
                o=float(c["open"]),
                h=float(c["high"]),
                l=float(c["low"]),
                c=float(c["close"]),
                v=int(c["volume"]),
            )
            for c in candles
        ]

    return provider


@asynccontextmanager
async def _lifespan(app: FastAPI) -> Any:
    logger.info("SCALPR API starting...")
    if os.environ.get("SCALPR_TRADING_ENABLED") == "1":
        try:
            await _start_trading(app)
        except Exception as e:
            # API still boots; /health reports the truth
            logger.error("trading_startup_failed: %s", e)
            app.state.feed = None
            app.state.broker_error = str(e)

    yield

    logger.info("SCALPR API shutting down...")

    # New event-driven system
    if getattr(app.state, "event_system", None):
        es = app.state.event_system
        with suppress(Exception):
            es["client"].stop()
        with suppress(Exception):
            es["engine"].stop()

    # Legacy system
    if getattr(app.state, "feed", None):
        with suppress(Exception):
            await app.state.feed.stop()
    if getattr(app.state, "gateway", None):
        with suppress(Exception):
            app.state.gateway.stop()
    if getattr(app.state, "replay_manager", None):
        with suppress(Exception):
            app.state.replay_manager.shutdown()


def create_app() -> FastAPI:
    """Create and wire the FastAPI application.

    This is the ONLY entry point. No side effects at module import.
    """
    _load_dotenv()

    app = FastAPI(title="SCALPR Trading API", version="0.1.0", lifespan=_lifespan)

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],  # Vite dev server only
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    from scalpr.api.routers import health, market_data, orders, portfolio, replay
    app.include_router(health.router)
    app.include_router(market_data.router)
    app.include_router(orders.router)
    app.include_router(portfolio.router)
    app.include_router(replay.router)

    # Register exception handlers for structured error responses
    from scalpr.api.error_handler import register_exception_handlers
    register_exception_handlers(app)

    # JWT auth middleware — only when SCALPR_JWT_SECRET is set (Bloomberg plan Module 10).
    # Health probes stay exempt via EXEMPT_PATHS in scalpr.api.auth.
    jwt_secret = os.environ.get("SCALPR_JWT_SECRET")
    if jwt_secret:
        from scalpr.api.auth import JwtAuthMiddleware
        app.add_middleware(JwtAuthMiddleware, secret=jwt_secret)

    # Store dependencies on app.state for router access
    gateway, broker_error = _create_gateway()
    app.state.gateway = gateway
    app.state.broker_error = broker_error
    # Event system shares the DhanClient from gateway when available
    app.state.event_system = _create_event_system(
        existing_client=gateway if gateway else None
    )
    app.state.feed = None
    app.state.executor = None
    app.state.order_router = None

    # Replay session manager (with candle provider if gateway available)
    from scalpr.api.replay_manager import ReplaySessionManager
    candle_provider = _create_candle_provider(gateway)
    app.state.replay_manager = ReplaySessionManager(candle_provider=candle_provider)

    return app

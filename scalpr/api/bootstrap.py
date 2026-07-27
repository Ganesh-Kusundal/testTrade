"""Composition root — wires all dependencies and creates the FastAPI app.

No side effects at import time. All initialization happens in create_app().
Trading wiring (strategies, feed, OMS) is gated behind SCALPR_TRADING_ENABLED=1
+ SCALPR_WATCHLIST so plain API boots remain unchanged.
"""
import asyncio
import logging
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)


def _load_dotenv() -> None:
    """Load environment variables. Called inside create_app, not at import."""
    from dotenv import load_dotenv
    load_dotenv()


def _create_gateway():
    """Create and configure the broker gateway port.

    Returns (port, error) — the IBrokerGateway port, because routers and
    wire() speak the port vocabulary (get_positions/get_margins/get_ltp).
    None if it cannot connect (e.g. missing credentials): API still boots,
    routers answer 503 and /health reports the error truthfully.
    """
    try:
        from scalpr.brokers.gateway import Gateway
        return Gateway().gateway, None
    except Exception as e:
        logger.error("Gateway creation failed — API will start without broker: %s", e)
        return None, str(e)


@dataclass
class AppContext:
    """The wired trading object graph."""
    order_router: object
    executor: object


def wire(
    gateway,
    watchlist: list[str],
    db_path: str = "data/oms.db",
    events_db_path: str = "data/events.db",
) -> AppContext:
    """Build the trading object graph: risk gates, OMS, router, strategies.

    Args:
        gateway: IBrokerGateway port (has get_positions/get_margins/place_order).
        watchlist: Symbols to run one ScalprAmtStrategy each.
        db_path: SQLite path for OMS persistence.
        events_db_path: SQLite path for the domain event audit log.
    """
    from datetime import datetime, timezone

    from scalpr.execution.order_router import OrderRouter
    from scalpr.observability.event_store import EventStore
    from scalpr.oms.order_manager import OrderManager
    from scalpr.oms.persistence import OmsRepository
    from scalpr.risk.circuit_breaker import CircuitBreaker
    from scalpr.risk.pre_trade import PreTradeRiskGate
    from scalpr.strategy.executor import StrategyExecutor
    from scalpr.strategy.scalpr_amt import ScalprAmtStrategy

    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    session_id = datetime.now(timezone.utc).strftime("live-%Y%m%d")
    order_router = OrderRouter(
        gateway=gateway,
        risk_gate=PreTradeRiskGate(),
        circuit_breaker=CircuitBreaker(),
        order_manager=OrderManager(
            OmsRepository(db_path),
            event_store=EventStore(db_path=events_db_path),
            session_id=session_id,
        ),
    )
    executor = StrategyExecutor()
    for symbol in watchlist:
        executor.register_strategy(ScalprAmtStrategy(order_router, symbol))
    return AppContext(order_router=order_router, executor=executor)


def _watchlist_from_env() -> list[str]:
    return [s.strip() for s in os.environ.get("SCALPR_WATCHLIST", "").split(",") if s.strip()]


async def _start_trading(app: FastAPI) -> None:
    """Wire strategies and start the live tick feed (lifespan startup)."""
    from scalpr.brokers.dhan.ws_manager import DhanWebSocketManager

    watchlist = _watchlist_from_env()
    gateway = app.state.gateway
    if not watchlist or gateway is None:
        logger.error("trading_enabled_but_unwirable: watchlist=%s gateway=%s",
                     watchlist, gateway is not None)
        return

    ctx = wire(gateway, watchlist)

    feed = DhanWebSocketManager(
        access_token=os.environ.get("DHAN_ACCESS_TOKEN", ""),
        client_id=os.environ.get("DHAN_CLIENT_ID", ""),
        resolver=gateway.connection.resolver,
    )
    await feed.start()
    await feed.subscribe_pairs([(s, "NSE") for s in watchlist])

    # Ticks arrive on the SDK thread — bridge them onto the app loop
    loop = asyncio.get_running_loop()
    feed.add_subscriber(
        lambda t: asyncio.run_coroutine_threadsafe(ctx.executor.on_tick(t), loop)
    )

    app.state.feed = feed
    app.state.executor = ctx.executor
    app.state.order_router = ctx.order_router
    logger.info("trading_wired: %s", watchlist)


@asynccontextmanager
async def _lifespan(app: FastAPI):
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
    if getattr(app.state, "feed", None):
        try:
            await app.state.feed.stop()
        except Exception:
            pass
    if getattr(app.state, "gateway", None):
        try:
            app.state.gateway.disconnect()
        except Exception:
            pass


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

    # Store dependencies on app.state for router access
    gateway, broker_error = _create_gateway()
    app.state.gateway = gateway
    app.state.broker_error = broker_error
    app.state.feed = None
    app.state.executor = None
    app.state.order_router = None

    return app

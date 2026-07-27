"""Composition root — wires all dependencies and creates the FastAPI app.

No side effects at import time. All initialization happens in create_app().
"""
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)


def _load_dotenv() -> None:
    """Load environment variables. Called inside create_app, not at import."""
    from dotenv import load_dotenv
    load_dotenv()


def _create_gateway():
    """Create and configure the broker gateway.

    Returns None if gateway cannot connect (e.g. missing credentials).
    Routers handle a None gateway gracefully.
    """
    try:
        from scalpr.brokers.gateway import Gateway
        return Gateway()
    except Exception as e:
        logger.warning("Gateway creation failed — API will start without broker: %s", e)
        return None


def _create_feed(gateway):
    """Create market data feed from gateway."""
    return None  # Will be wired from gateway connection


def create_app() -> FastAPI:
    """Create and wire the FastAPI application.

    This is the ONLY entry point. No side effects at module import.
    """
    _load_dotenv()

    app = FastAPI(title="SCALPR Trading API", version="0.1.0")

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],  # Vite dev server only
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    from scalpr.api.routers import market_data, orders, portfolio, replay
    app.include_router(market_data.router)
    app.include_router(orders.router)
    app.include_router(portfolio.router)
    app.include_router(replay.router)

    # Store dependencies on app.state for router access
    gateway = _create_gateway()
    app.state.gateway = gateway
    app.state.feed = _create_feed(gateway)

    @app.on_event("startup")
    async def startup():
        logger.info("SCALPR API starting...")

    @app.on_event("shutdown")
    async def shutdown():
        logger.info("SCALPR API shutting down...")
        if hasattr(app.state, "gateway") and app.state.gateway:
            try:
                app.state.gateway.disconnect()
            except Exception:
                pass

    return app

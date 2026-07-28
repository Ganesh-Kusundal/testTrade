"""Market data REST routes — wired to real dependencies.

C3 fail-closed: broker unavailable → 503, adapter failure → 502.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/market", tags=["market-data"])


def _require_gateway(request: Request) -> Any:
    gateway = request.app.state.gateway
    if not gateway or not gateway.is_connected():
        raise HTTPException(status_code=503, detail="broker unavailable")
    return gateway


@router.get("/ltp/{symbol}")  # type: ignore[untyped-decorator]
async def get_ltp(symbol: str, request: Request, exchange: str = "NSE") -> Any:
    """Get last traded price from broker.

    Args:
        symbol: Trading symbol (e.g., "RELIANCE", "CRUDEOIL")
        exchange: Exchange code (default: "NSE"). Supported: NSE, BSE, MCX, NFO, INDEX.
    """
    gateway = _require_gateway(request)
    try:
        ltp = gateway.get_ltp(symbol, exchange)
    except Exception as exc:
        logger.error("ltp_fetch_failed for %s on %s: %s", symbol, exchange, exc)
        raise HTTPException(status_code=502, detail=f"broker error: {exc}") from exc
    return {"symbol": symbol, "exchange": exchange, "ltp": str(ltp)}


@router.get("/candles/{symbol}")  # type: ignore[untyped-decorator]
async def get_candles(symbol: str, request: Request, exchange: str = "NSE", timeframe: str = "5m", count: int = 100) -> Any:
    """Get OHLCV candles.

    Args:
        symbol: Trading symbol
        exchange: Exchange code (default: "NSE"). Supported: NSE, BSE, MCX, NFO, INDEX.
        timeframe: Candle interval (default: "5m")
        count: Number of candles (default: 100)
    """
    gateway = _require_gateway(request)
    try:
        connection = gateway.connection
        return connection.historical.get_ohlcv_latest(symbol, exchange, timeframe, count)
    except Exception as exc:
        logger.error("candles_fetch_failed for %s on %s: %s", symbol, exchange, exc)
        raise HTTPException(status_code=502, detail=f"broker error: {exc}") from exc

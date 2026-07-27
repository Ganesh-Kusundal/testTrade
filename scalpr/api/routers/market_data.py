"""Market data REST routes — wired to real dependencies.

C3 fail-closed: broker unavailable → 503, adapter failure → 502.
"""
import logging

from fastapi import APIRouter, HTTPException, Request

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/market", tags=["market-data"])


def _require_gateway(request: Request):
    gateway = request.app.state.gateway
    if not gateway or not gateway.is_connected():
        raise HTTPException(status_code=503, detail="broker unavailable")
    return gateway


@router.get("/ltp/{symbol}")
async def get_ltp(symbol: str, request: Request):
    """Get last traded price from broker."""
    gateway = _require_gateway(request)
    try:
        ltp = gateway.get_ltp(symbol, "NSE")
    except Exception as exc:
        logger.error("ltp_fetch_failed for %s: %s", symbol, exc)
        raise HTTPException(status_code=502, detail=f"broker error: {exc}") from exc
    return {"symbol": symbol, "ltp": str(ltp)}


@router.get("/candles/{symbol}")
async def get_candles(symbol: str, request: Request, timeframe: str = "5m", count: int = 100):
    """Get OHLCV candles."""
    gateway = _require_gateway(request)
    try:
        connection = gateway.connection
        return connection.historical.get_ohlcv_latest(symbol, "NSE", timeframe, count)
    except Exception as exc:
        logger.error("candles_fetch_failed for %s: %s", symbol, exc)
        raise HTTPException(status_code=502, detail=f"broker error: {exc}") from exc

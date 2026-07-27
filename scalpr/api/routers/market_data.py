"""Market data REST routes — wired to real dependencies."""
from fastapi import APIRouter, Request

router = APIRouter(prefix="/market", tags=["market-data"])


@router.get("/ltp/{symbol}")
async def get_ltp(symbol: str, request: Request):
    """Get last traded price from broker."""
    gateway = request.app.state.gateway
    if not gateway or not gateway.is_connected():
        return {"symbol": symbol, "ltp": None, "error": "Gateway not connected"}
    try:
        ltp = gateway.get_ltp(symbol, "NSE")
        return {"symbol": symbol, "ltp": str(ltp)}
    except Exception as e:
        return {"symbol": symbol, "ltp": None, "error": str(e)}


@router.get("/candles/{symbol}")
async def get_candles(symbol: str, request: Request, timeframe: str = "5", count: int = 100):
    """Get OHLCV candles."""
    gateway = request.app.state.gateway
    if not gateway or not gateway.is_connected():
        return {"error": "Gateway not connected"}
    try:
        connection = gateway.connection
        candles = connection.historical.get_ohlcv(symbol, "NSE", timeframe)
        return candles[-count:] if candles else []
    except Exception as e:
        return {"error": str(e)}

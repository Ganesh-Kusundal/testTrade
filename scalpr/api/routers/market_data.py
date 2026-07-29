"""Market data REST routes — wired to real dependencies.

C3 fail-closed: broker unavailable → 503, adapter failure → 502.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from scalpr.domain.instrument import SimpleInstrumentId

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/market", tags=["market-data"])


def _require_preferred(request: Request) -> tuple[Any, str]:
    event_system = getattr(request.app.state, "event_system", None)
    if event_system:
        return event_system["client"], "event_system"
    gateway = request.app.state.gateway
    if gateway and gateway.is_connected():
        return gateway, "gateway"
    raise HTTPException(status_code=503, detail="broker unavailable")


TIMEFRAME_MAP = {
    "1m": ("MINUTE", 1),
    "3m": ("MINUTE", 3),
    "5m": ("MINUTE", 5),
    "15m": ("MINUTE", 15),
    "30m": ("MINUTE", 30),
    "1h": ("MINUTE", 60),
    "4h": ("MINUTE", 240),
    "1d": ("DAY", 1),
    "1w": ("WEEK", 1),
}


@router.get("/ltp/{symbol}")
async def get_ltp(symbol: str, request: Request, exchange: str = "NSE") -> Any:
    client, source = _require_preferred(request)
    try:
        if source == "event_system":
            instrument_id = SimpleInstrumentId.parse(f"{symbol}:{exchange}")
            quote = client.get_quote(instrument_id)
            return {"symbol": symbol, "exchange": exchange, "ltp": str(quote.ltp)}
        ltp = client.get_ltp(symbol, exchange)
        return {"symbol": symbol, "exchange": exchange, "ltp": str(ltp)}
    except Exception as exc:
        logger.error("ltp_fetch_failed for %s on %s: %s", symbol, exchange, exc)
        raise HTTPException(status_code=502, detail=f"broker error: {exc}") from exc


@router.get("/candles/{symbol}")
async def get_candles(symbol: str, request: Request, exchange: str = "NSE", timeframe: str = "5m", count: int = 100) -> Any:
    client, source = _require_preferred(request)
    try:
        if source == "event_system":
            tf_info = TIMEFRAME_MAP.get(timeframe)
            if tf_info is None:
                raise HTTPException(status_code=422, detail=f"unsupported timeframe: {timeframe}")
            tf_type, interval = tf_info
            to_date = datetime.now().strftime("%Y-%m-%d")
            from_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            candles = client.get_historical(
                symbol=symbol,
                exchange=exchange,
                timeframe=tf_type,
                interval=interval,
                from_date=from_date,
                to_date=to_date,
            )
            return candles[-count:] if len(candles) > count else candles
        connection = client.connection
        return connection.historical.get_ohlcv_latest(symbol, exchange, timeframe, count)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("candles_fetch_failed for %s on %s: %s", symbol, exchange, exc)
        raise HTTPException(status_code=502, detail=f"broker error: {exc}") from exc

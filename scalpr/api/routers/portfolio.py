"""Portfolio routes — wired to real dependencies.

C3 fail-closed: broker unavailable → 503, adapter failure → 502.
Never fabricate an empty book.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


def _require_preferred(request: Request) -> tuple[Any, str]:
    event_system = getattr(request.app.state, "event_system", None)
    if event_system:
        return event_system["client"], "event_system"
    gateway = request.app.state.gateway
    if gateway and gateway.is_connected():
        return gateway, "gateway"
    raise HTTPException(status_code=503, detail="broker unavailable")


@router.get("/positions")
async def get_positions(request: Request) -> Any:
    client, _source = _require_preferred(request)
    try:
        positions = client.get_positions()
    except Exception as exc:
        logger.error("positions_fetch_failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"broker error: {exc}") from exc
    return [
        {
            "symbol": p.symbol, "exchange": p.exchange.value,
            "quantity": p.quantity, "avg_price": str(p.avg_price),
            "ltp": str(p.ltp), "unrealised_pnl": str(p.unrealised_pnl),
            "realised_pnl": str(p.realised_pnl),
            "position_side": p.position_side.value, "state": p.state.value,
        }
        for p in positions
    ]


@router.get("/margins")
async def get_margins(request: Request) -> Any:
    client, source = _require_preferred(request)
    try:
        if source == "event_system":
            return client.get_funds()
        return client.get_margins()
    except Exception as exc:
        logger.error("margins_fetch_failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"broker error: {exc}") from exc


@router.get("/holdings")
async def get_holdings(request: Request) -> Any:
    client, source = _require_preferred(request)
    if source != "event_system":
        raise HTTPException(status_code=501, detail="holdings only available via event system")
    try:
        return client.get_holdings()
    except Exception as exc:
        logger.error("holdings_fetch_failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"broker error: {exc}") from exc


@router.post("/square-off")
async def square_off(request: Request) -> Any:
    gateway = getattr(request.app.state, "gateway", None)
    if not gateway or not gateway.is_connected():
        raise HTTPException(status_code=503, detail="broker unavailable")
    try:
        fills = gateway.square_off_all()
    except Exception as exc:
        logger.error("square_off_failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"broker error: {exc}") from exc
    return {"squared_off": len(fills)}

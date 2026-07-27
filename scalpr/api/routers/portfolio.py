"""Portfolio routes — wired to real dependencies.

C3 fail-closed: broker unavailable → 503, adapter failure → 502.
Never fabricate an empty book.
"""
import logging

from fastapi import APIRouter, HTTPException, Request

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


def _require_gateway(request: Request):
    gateway = request.app.state.gateway
    if not gateway or not gateway.is_connected():
        raise HTTPException(status_code=503, detail="broker unavailable")
    return gateway


@router.get("/positions")
async def get_positions(request: Request):
    """Get current positions from broker."""
    gateway = _require_gateway(request)
    try:
        positions = gateway.get_positions()
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
async def get_margins(request: Request):
    """Get available margins."""
    gateway = _require_gateway(request)
    try:
        return gateway.get_margins()
    except Exception as exc:
        logger.error("margins_fetch_failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"broker error: {exc}") from exc


@router.post("/square-off")
async def square_off(request: Request):
    """Square off all positions."""
    gateway = _require_gateway(request)
    try:
        fills = gateway.square_off_all()
    except Exception as exc:
        logger.error("square_off_failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"broker error: {exc}") from exc
    return {"squared_off": len(fills)}

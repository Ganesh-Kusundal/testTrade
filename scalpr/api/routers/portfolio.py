"""Portfolio routes — wired to real dependencies."""
from fastapi import APIRouter, Request

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("/positions")
async def get_positions(request: Request):
    """Get current positions from broker."""
    gateway = request.app.state.gateway
    if not gateway or not gateway.is_connected():
        return []
    try:
        positions = gateway.get_positions()
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
    except Exception:
        return []


@router.get("/margins")
async def get_margins(request: Request):
    """Get available margins."""
    gateway = request.app.state.gateway
    if not gateway or not gateway.is_connected():
        return {}
    try:
        return gateway.get_margins()
    except Exception:
        return {}


@router.post("/square-off")
async def square_off(request: Request):
    """Square off all positions."""
    gateway = request.app.state.gateway
    if not gateway or not gateway.is_connected():
        return {"error": "Gateway not connected"}
    try:
        fills = gateway.square_off_all()
        return {"squared_off": len(fills)}
    except Exception as e:
        return {"error": str(e)}

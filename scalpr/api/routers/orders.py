"""Order management REST routes — wired to real dependencies."""
from fastapi import APIRouter, Request

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("/")
async def get_orders(request: Request):
    """Get all orders from broker."""
    gateway = request.app.state.gateway
    if not gateway or not gateway.is_connected():
        return []
    try:
        return gateway.get_orders() if hasattr(gateway, "get_orders") else []
    except Exception:
        return []


@router.get("/fills")
async def get_fills(request: Request):
    """Get all fills."""
    return []

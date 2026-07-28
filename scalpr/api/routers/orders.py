"""Order management REST routes — wired to real dependencies.

C3 fail-closed: broker unavailable → 503, adapter failure → 502.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("/")  # type: ignore[untyped-decorator]
async def get_orders(request: Request) -> Any:
    """Get all orders from broker."""
    gateway = request.app.state.gateway
    if not gateway or not gateway.is_connected():
        raise HTTPException(status_code=503, detail="broker unavailable")
    try:
        return gateway.get_orders() if hasattr(gateway, "get_orders") else []
    except Exception as exc:
        logger.error("orders_fetch_failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"broker error: {exc}") from exc


@router.get("/fills")  # type: ignore[untyped-decorator]
async def get_fills(request: Request) -> Any:
    """Fills endpoint — not implemented yet; 501 is honest, [] is not."""
    raise HTTPException(status_code=501, detail="fills endpoint not implemented")

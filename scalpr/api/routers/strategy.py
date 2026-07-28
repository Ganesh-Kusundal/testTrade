"""Strategy status routes — gate FSM observability for the frontend.

Fail-closed: trading not wired (no executor) → 503. The gates panel
renders REAL last-evaluation state or an honest "trading disabled".
"""
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/strategy", tags=["strategy"])


@router.get("/status")  # type: ignore[untyped-decorator]
async def get_strategy_status(request: Request) -> list[dict[str, Any]]:
    """Per-strategy status: trade counts + last gate FSM evaluation."""
    executor = getattr(request.app.state, "executor", None)
    if executor is None:
        raise HTTPException(status_code=503, detail="trading not enabled")
    return [
        {"symbol": s.symbol, **s.get_status()}
        for s in executor.strategies
    ]

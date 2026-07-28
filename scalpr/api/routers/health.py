"""Truthful health endpoint — always 200, payload never lies (C3)."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(tags=["health"])


@router.get("/health")  # type: ignore[untyped-decorator]
async def health(request: Request) -> dict[str, Any]:
    gateway = getattr(request.app.state, "gateway", None)
    return {
        "gateway": bool(gateway and gateway.is_connected()),
        "feed": getattr(request.app.state, "feed", None) is not None,
        "broker_error": getattr(request.app.state, "broker_error", None),
    }


@router.get("/health/live")  # type: ignore[untyped-decorator]
async def health_live() -> dict[str, str]:
    """Liveness probe — the process is up; never checks dependencies."""
    return {"status": "ok", "check": "live"}


@router.get("/health/ready")  # type: ignore[untyped-decorator]
async def health_ready(request: Request) -> Any:
    """Readiness probe — 200 only when the broker gateway is connected.

    503 keeps the same JSON shape (status/check) so probers can parse it.
    """
    gateway = getattr(request.app.state, "gateway", None)
    if gateway and gateway.is_connected():
        return {"status": "ok", "check": "ready"}
    return JSONResponse(status_code=503, content={"status": "unavailable", "check": "ready"})

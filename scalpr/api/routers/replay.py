"""Replay session REST routes — wire to ReplaySessionManager."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from scalpr.api.models import (
    CreateReplayBody,
    ReplayControlBody,
    ReplaySession,
    ReplaySessionsResponse,
)
from scalpr.domain.values import DEFAULT_EXCHANGE

router = APIRouter(prefix="/replay", tags=["replay"])


def _get_manager(request: Request) -> Any:
    manager = request.app.state.replay_manager
    if manager is None:
        raise HTTPException(status_code=503, detail="replay manager not initialized")
    return manager


@router.post("/sessions", response_model=ReplaySession)  # type: ignore[untyped-decorator]
async def create_replay_session(
    body: CreateReplayBody,
    request: Request,
    manager: Any = Depends(_get_manager),
) -> Any:
    """Create a new replay session for the given symbol/date/timeframe."""
    try:
        session = manager.create(
            symbol=body.symbol,
            date=body.date,
            timeframe=body.timeframe,
            exchange=DEFAULT_EXCHANGE,
            from_t=body.from_t,
            to_t=body.to_t,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return session


@router.get("/sessions", response_model=ReplaySessionsResponse)  # type: ignore[untyped-decorator]
async def list_replay_sessions(
    request: Request,
    symbol: str | None = None,
    date: str | None = None,
    manager: Any = Depends(_get_manager),
) -> Any:
    """List replay sessions, optionally filtered by symbol/date."""
    sessions = manager.list_sessions(symbol=symbol, date=date)
    return ReplaySessionsResponse(sessions=sessions)


@router.get("/sessions/{session_id}", response_model=ReplaySession)  # type: ignore[untyped-decorator]
async def get_replay_session(
    session_id: str,
    request: Request,
    manager: Any = Depends(_get_manager),
) -> Any:
    """Get a replay session by ID."""
    runtime = manager.get(session_id)
    if runtime is None:
        raise HTTPException(status_code=404, detail=f"session not found: {session_id}")
    return runtime.snapshot()


@router.post("/sessions/{session_id}/control", response_model=ReplaySession)  # type: ignore[untyped-decorator]
async def control_replay_session(
    session_id: str,
    body: ReplayControlBody,
    request: Request,
    manager: Any = Depends(_get_manager),
) -> Any:
    """Control a replay session: play, pause, step, seek, set_speed."""
    action = body.action
    try:
        if action == "play":
            session = manager.control(session_id, "play")
        elif action == "pause":
            session = manager.control(session_id, "pause")
        elif action == "step":
            session = manager.control(session_id, "step", n=body.n)
        elif action == "seek":
            session = manager.control(session_id, "seek", to_t=body.to_t)
        elif action == "set_speed":
            session = manager.control(session_id, "set_speed", speed=body.speed)
        else:
            raise ValueError(f"unknown action: {action}")
    except KeyError as e:
        raise HTTPException(status_code=404, detail=f"session not found: {session_id}") from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return session

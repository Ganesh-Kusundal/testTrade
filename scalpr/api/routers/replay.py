"""Replay session REST routes."""
from fastapi import APIRouter

router = APIRouter(prefix="/replay", tags=["replay"])


@router.post("/start")
async def start_replay(session_data: dict):
    """Start a replay session."""
    return {"status": "not_implemented"}


@router.get("/status")
async def get_replay_status():
    """Get current replay session status."""
    return {"active": False}


@router.post("/stop")
async def stop_replay():
    """Stop the current replay session."""
    return {"status": "not_implemented"}

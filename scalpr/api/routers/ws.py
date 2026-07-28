"""WebSocket endpoints — /ws/market, /ws/replay/{id}, and /ws/portfolio.

Message shapes are FIXED by the frontend:
- market: useMarketStream.ts — client sends {action:'subscribe'|'unsubscribe',
  symbols:[]}; server sends {type:'quote'|'tick'|...}, {type:'subscribed'|
  'unsubscribed', symbols:[]}, {type:'error', reason?, message?}
- replay: types/index.ts ReplayEvent frames, emitted by ReplaySessionManager.
- portfolio: pushes PortfolioPosition updates when positions change.

Both use the same fan-out/serializer (ws_manager) — replay ≡ live streaming.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from scalpr.api.ws_manager import ClientChannel, WsFanout, serialize

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


async def _pump(websocket: WebSocket, channel: ClientChannel) -> None:
    """Writer loop: bounded queue → socket."""
    while True:
        frame = await channel.next_frame()
        await websocket.send_text(frame)


@router.websocket("/ws/market")  # type: ignore[untyped-decorator]
async def ws_market(websocket: WebSocket) -> Any:
    fanout: WsFanout = websocket.app.state.market_fanout
    await websocket.accept()
    channel = fanout.register()
    writer = asyncio.create_task(_pump(websocket, channel))
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                channel.publish({"type": "error", "reason": "bad_json",
                                 "message": "invalid JSON frame"})
                continue
            action = msg.get("action")
            symbols = [s for s in msg.get("symbols", []) if isinstance(s, str)]
            if action == "subscribe":
                channel.subscriptions.update(symbols)
                channel.publish({"type": "subscribed", "symbols": symbols})
            elif action == "unsubscribe":
                channel.subscriptions.difference_update(symbols)
                channel.publish({"type": "unsubscribed", "symbols": symbols})
            else:
                channel.publish({"type": "error", "reason": "bad_action",
                                 "message": f"unknown action: {action}"})
    except WebSocketDisconnect:
        pass
    finally:
        writer.cancel()
        fanout.unregister(channel)


@router.websocket("/ws/portfolio")  # type: ignore[untyped-decorator]
async def ws_portfolio(websocket: WebSocket) -> Any:
    """Push portfolio position updates to the frontend.

    Sends initial snapshot on connect, then pushes deltas when positions change.
    Frontend can still poll REST /portfolio/positions as fallback.
    """
    await websocket.accept()
    gateway = getattr(websocket.app.state, "gateway", None)
    getattr(websocket.app.state, "portfolio_manager", None)

    if gateway is None or not gateway.is_connected():
        await websocket.send_text(serialize({
            "type": "error", "code": "BROKER_UNAVAILABLE",
            "message": "broker gateway not connected",
        }))
        await websocket.close()
        return

    # Send initial snapshot
    try:
        positions = gateway.get_positions()
        await websocket.send_text(serialize({
            "type": "portfolio_snapshot",
            "positions": [
                {
                    "symbol": p.symbol,
                    "exchange": p.exchange.value,
                    "quantity": p.quantity,
                    "avg_price": str(p.avg_price),
                    "ltp": str(p.ltp),
                    "unrealised_pnl": str(p.unrealised_pnl),
                    "realised_pnl": str(p.realised_pnl),
                    "total_pnl": str(p.total_pnl()),
                    "position_side": p.position_side.value,
                    "state": p.state.value,
                }
                for p in positions
            ],
        }))
    except Exception as e:
        logger.error("portfolio_ws_snapshot_failed: %s", e)
        await websocket.send_text(serialize({
            "type": "error", "code": "SNAPSHOT_FAILED",
            "message": str(e),
        }))

    # Keep connection alive — frontend will poll REST for now
    # Future: subscribe to domain events and push deltas
    try:
        while True:
            # Drain any client messages (pings, etc.)
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass


@router.websocket("/ws/replay/{session_id}")  # type: ignore[untyped-decorator]
async def ws_replay(websocket: WebSocket, session_id: str) -> Any:
    manager = getattr(websocket.app.state, "replay_manager", None)
    await websocket.accept()
    runtime = manager.get(session_id) if manager else None
    if runtime is None:
        await websocket.send_text(serialize({
            "type": "error", "session_id": session_id,
            "code": "UNKNOWN_SESSION", "message": f"unknown session: {session_id}",
        }))
        await websocket.close()
        return

    channel = runtime.fanout.register()
    # Snapshot so a late joiner immediately knows the cursor/state.
    channel.publish({
        "type": "replay_state", "session_id": runtime.id,
        "state": runtime.state, "speed": runtime.speed, "cursor_t": runtime.cursor_t,
    })
    writer = asyncio.create_task(_pump(websocket, channel))
    try:
        while True:  # replay is control-free over WS (REST drives it); drain pings
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        writer.cancel()
        runtime.fanout.unregister(channel)

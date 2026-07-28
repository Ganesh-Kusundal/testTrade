"""API contract models — Pydantic v2 mirrors of frontend/src/types/index.ts.

This module is the SOURCE OF TRUTH for the /api/v1 JSON contract
(plan Task 7). Field names and shapes MUST match the frontend types
exactly — the frontend is a pure consumer and never adapts.

Serialization note: the domain speaks Decimal everywhere; converting to
JSON numbers (float) and epoch-ms ints happens HERE, at the boundary,
and nowhere else (plan Task 2: "epoch-ms is a serialization concern").
"""
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field

Exchange = Literal["NSE", "BSE", "MCX"]
Segment = Literal["EQ", "FO", "CD", "COM"]
Timeframe = Literal["1m", "3m", "5m", "15m", "30m", "1h", "4h", "1d", "1w"]
ReplayState = Literal["IDLE", "PLAYING", "PAUSED", "ENDED"]


class SymbolInfo(BaseModel):
    """Mirror of frontend Symbol."""
    symbol: str
    name: str
    exchange: Exchange
    segment: Segment
    isin: str = ""
    lotSize: int = 1
    tickSize: float = 0.05
    sector: str | None = None


class SymbolSearchResponse(BaseModel):
    results: list[SymbolInfo]


class Quote(BaseModel):
    """Mirror of frontend Quote. ts is epoch ms."""
    symbol: str
    exchange: Exchange
    ltp: float
    open: float
    high: float
    low: float
    prevClose: float
    change: float
    changePct: float
    volume: int
    bid: float = 0
    ask: float = 0
    bidQty: int = 0
    askQty: int = 0
    ts: int


class Candle(BaseModel):
    """Mirror of frontend Candle. t is open-time, epoch ms."""
    t: int
    o: float
    h: float
    l: float  # noqa: E741 — OHLC wire field name, mirrors frontend contract
    c: float
    v: int


class IndicatorSeries(BaseModel):
    """Backend-computed indicator overlays, index-aligned with candles.

    The frontend renders these values and NEVER computes indicators
    (plan Task 5.3 — EMA comes from the backend, the sole authority).
    """
    ema9: list[float]
    ema20: list[float]
    ema50: list[float]


class CandlesResponse(BaseModel):
    symbol: str
    exchange: Exchange
    timeframe: Timeframe
    candles: list[Candle]
    indicators: IndicatorSeries | None = None


class ReplaySession(BaseModel):
    """Mirror of frontend ReplaySession. All *_t fields are epoch ms."""
    id: str
    symbol: str
    exchange: Exchange
    timeframe: Timeframe
    from_t: int
    to_t: int
    cursor_t: int
    state: ReplayState
    speed: float


class ReplaySessionsResponse(BaseModel):
    sessions: list[ReplaySession]


class CreateReplayBody(BaseModel):
    """Mirror of client.ts CreateReplayBody."""
    symbol: str
    date: str  # YYYY-MM-DD
    timeframe: Timeframe = "1m"
    from_t: int | None = None
    to_t: int | None = None


# ── Replay control (client.ts ReplayAction discriminated union) ────────────

class PlayAction(BaseModel):
    action: Literal["play"]


class PauseAction(BaseModel):
    action: Literal["pause"]


class StepAction(BaseModel):
    action: Literal["step"]
    n: int = Field(default=1, ge=1)


class SeekAction(BaseModel):
    action: Literal["seek"]
    to_t: int


class SetSpeedAction(BaseModel):
    action: Literal["set_speed"]
    speed: float = Field(gt=0)


ReplayControlBody = Annotated[
    PlayAction | PauseAction | StepAction | SeekAction | SetSpeedAction,
    Field(discriminator="action"),
]


class ReplayEvent(BaseModel):
    """Mirror of frontend ReplayEvent — WS message schema for /ws/replay/{id}."""
    type: Literal["replay_candle", "replay_quote", "replay_state", "replay_end", "error"]
    session_id: str | None = None
    candle: Candle | None = None
    ltp: float | None = None
    ts: int | None = None
    state: ReplayState | None = None
    speed: float | None = None
    cursor_t: int | None = None
    code: str | None = None
    message: str | None = None

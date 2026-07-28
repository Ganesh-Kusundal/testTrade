"""Replay session manager — application service behind /replay/* + /ws/replay/{id}.

Owns replay session lifecycle and cursor state; streams ReplayEvent frames
through a per-session WsFanout. Controls are TIME ONLY (pause/step/seek/
speed) — mirroring ReplayEngine semantics; no strategy logic lives here.

Candle data comes from an injected provider (broker historical adapter or
EventStore-derived candles). No provider → fail-closed 503, never mocks.
"""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass, field

from scalpr.api.models import Candle, ReplaySession
from scalpr.api.ws_manager import WsFanout

logger = logging.getLogger(__name__)

# Replay state constants (match ReplayEngine semantics)
IDLE = "IDLE"
PLAYING = "PLAYING"
PAUSED = "PAUSED"
ENDED = "ENDED"

# UI pacing: ~1 candle per 200ms at 1x speed (matches the retired FE mock).
_BASE_MS_PER_CANDLE = 200.0
_MIN_MS_PER_CANDLE = 20.0

# provider(symbol, exchange, timeframe, date) -> list[Candle] (epoch-ms, ascending)
CandleProvider = Callable[[str, str, str, str], "list[Candle]"]


@dataclass
class _SessionRuntime:
    """One replay session: metadata + cursor + its WS fan-out."""
    id: str
    symbol: str
    exchange: str
    timeframe: str
    date: str
    candles: list[Candle]
    from_t: int
    to_t: int
    cursor: int = 0
    state: str = IDLE
    speed: float = 1.0
    fanout: WsFanout = field(default_factory=WsFanout)
    _task: asyncio.Task[None] | None = None

    @property
    def cursor_t(self) -> int:
        if not self.candles:
            return self.from_t
        idx = min(max(self.cursor - 1, 0), len(self.candles) - 1)
        return self.candles[idx].t if self.cursor > 0 else self.from_t

    def snapshot(self) -> ReplaySession:
        return ReplaySession(
            id=self.id, symbol=self.symbol, exchange=self.exchange,
            timeframe=self.timeframe, from_t=self.from_t, to_t=self.to_t,
            cursor_t=self.cursor_t, state=self.state, speed=self.speed,
        )

    # ── event emission (one schema, plan Task 7) ────────────────────────────

    def _emit_candle(self, candle: Candle) -> None:
        self.fanout.broadcast({
            "type": "replay_candle", "session_id": self.id,
            "candle": candle.model_dump(),
        })

    def _emit_state(self) -> None:
        self.fanout.broadcast({
            "type": "replay_state", "session_id": self.id,
            "state": self.state, "speed": self.speed, "cursor_t": self.cursor_t,
        })

    def _emit_end(self) -> None:
        self.fanout.broadcast({
            "type": "replay_end", "session_id": self.id, "cursor_t": self.cursor_t,
        })

    # ── cursor controls ─────────────────────────────────────────────────────

    def _dispatch_next(self) -> bool:
        """Emit the candle at the cursor; returns False when exhausted."""
        if self.cursor >= len(self.candles):
            return False
        self._emit_candle(self.candles[self.cursor])
        self.cursor += 1
        return True

    async def _play_loop(self) -> None:
        try:
            while self.state == PLAYING:
                if not self._dispatch_next():
                    self.state = ENDED
                    self._emit_state()
                    self._emit_end()
                    return
                self._emit_state()
                delay_ms = max(_MIN_MS_PER_CANDLE, _BASE_MS_PER_CANDLE / self.speed)
                await asyncio.sleep(delay_ms / 1000.0)
        except asyncio.CancelledError:  # pause/stop — state already set
            raise

    def play(self) -> None:
        if self.state in (PLAYING, ENDED):
            return
        self.state = PLAYING
        self._emit_state()
        self._task = asyncio.get_running_loop().create_task(self._play_loop())

    def pause(self) -> None:
        if self.state != PLAYING:
            return
        self.state = PAUSED
        if self._task:
            self._task.cancel()
            self._task = None
        self._emit_state()

    def step(self, n: int = 1) -> None:
        if self.state == PLAYING:
            self.pause()
        for _ in range(n):
            if not self._dispatch_next():
                self.state = ENDED
                self._emit_state()
                self._emit_end()
                return
        self.state = PAUSED
        self._emit_state()

    def seek(self, to_t: int) -> None:
        if self.state == PLAYING:
            self.pause()
        self.cursor = next(
            (i for i, c in enumerate(self.candles) if c.t >= to_t),
            len(self.candles),
        )
        self.state = PAUSED
        # Re-emit the candle now under the cursor so the chart snaps to it.
        if self.cursor > 0:
            self._emit_candle(self.candles[self.cursor - 1])
        self._emit_state()

    def set_speed(self, speed: float) -> None:
        self.speed = max(0.25, min(128.0, speed))
        self._emit_state()

    def close(self) -> None:
        if self._task:
            self._task.cancel()
            self._task = None


class ReplaySessionManager:
    """Registry + factory for replay sessions (composition-root singleton)."""

    def __init__(self, candle_provider: CandleProvider | None = None) -> None:
        self._provider = candle_provider
        self._sessions: dict[str, _SessionRuntime] = {}

    def list_sessions(self, symbol: str | None = None,
                      date: str | None = None) -> list[ReplaySession]:
        return [
            s.snapshot() for s in self._sessions.values()
            if (symbol is None or s.symbol == symbol)
            and (date is None or s.date == date)
        ]

    def get(self, session_id: str) -> _SessionRuntime | None:
        return self._sessions.get(session_id)

    def create(self, symbol: str, date: str, timeframe: str = "1m",
               exchange: str = "NSE",
               from_t: int | None = None, to_t: int | None = None) -> ReplaySession:
        """Create (or return the existing) session for symbol+date+timeframe.

        Raises:
            RuntimeError: no candle provider wired (fail-closed — never mocks).
            LookupError: provider returned no data for the requested day.
        """
        session_id = f"rs-{symbol}-{date}-{timeframe}"
        existing = self._sessions.get(session_id)
        if existing is not None:
            return existing.snapshot()

        if self._provider is None:
            raise RuntimeError("replay data source unavailable")
        candles = self._provider(symbol, exchange, timeframe, date)
        if not candles:
            raise LookupError(f"no replay data for {symbol} on {date}")

        runtime = _SessionRuntime(
            id=session_id, symbol=symbol, exchange=exchange,
            timeframe=timeframe, date=date, candles=candles,
            from_t=from_t if from_t is not None else candles[0].t,
            to_t=to_t if to_t is not None else candles[-1].t,
        )
        self._sessions[session_id] = runtime
        return runtime.snapshot()

    def control(self, session_id: str, action: str, *,
                n: int = 1, to_t: int | None = None,
                speed: float | None = None) -> ReplaySession:
        """Apply a cursor control; raises KeyError for unknown sessions."""
        runtime = self._sessions[session_id]
        if action == "play":
            runtime.play()
        elif action == "pause":
            runtime.pause()
        elif action == "step":
            runtime.step(n)
        elif action == "seek":
            runtime.seek(to_t if to_t is not None else runtime.from_t)
        elif action == "set_speed":
            runtime.set_speed(speed if speed is not None else 1.0)
        else:  # unreachable via Pydantic-validated bodies
            raise ValueError(f"unknown replay action: {action}")
        return runtime.snapshot()

    def shutdown(self) -> None:
        for runtime in self._sessions.values():
            runtime.close()
        self._sessions.clear()

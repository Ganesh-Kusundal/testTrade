"""TradingSession — identifies one run of the pipeline (live/replay/backtest).

Replaces the ad-hoc `live-%Y%m%d` string in bootstrap with an explicit,
typed session whose clock drives every timestamp in the run.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Literal

from scalpr.domain.clock import IClock, WallClock

SessionMode = Literal["live", "replay", "backtest"]


@dataclass(slots=True, frozen=True)
class TradingSession:
    """One trading run: id, date, mode, and the clock that times it."""
    session_id: str
    trading_date: date
    mode: SessionMode
    clock: IClock = field(default_factory=WallClock)

    def __post_init__(self) -> None:
        if not self.session_id:
            raise ValueError("session_id must be non-empty")
        if self.mode not in ("live", "replay", "backtest"):
            raise ValueError(f"mode must be live/replay/backtest, got {self.mode!r}")

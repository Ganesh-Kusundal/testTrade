"""Clock port — every timestamp in the trading pipeline comes from an IClock.

Live trading injects WallClock; replay/backtest inject SimulatedClock so the
same pipeline objects produce deterministic, reproducible event streams.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Protocol, runtime_checkable


@runtime_checkable
class IClock(Protocol):
    """Time source port. Implementations must return timezone-aware UTC."""

    def now(self) -> datetime:
        ...


class WallClock:
    """Real wall-clock time (live trading)."""

    def now(self) -> datetime:
        return datetime.now(timezone.utc)


class SimulatedClock:
    """Deterministic clock for replay/backtest — time moves only when told to."""

    def __init__(self, start: datetime) -> None:
        if start.tzinfo is None:
            raise ValueError("SimulatedClock start must be timezone-aware")
        self._current = start

    def now(self) -> datetime:
        return self._current

    def set(self, moment: datetime) -> None:
        """Jump to an absolute moment (e.g. an event's recorded timestamp)."""
        if moment.tzinfo is None:
            raise ValueError("moment must be timezone-aware")
        self._current = moment

    def advance(self, delta: timedelta) -> None:
        """Move time forward by delta. Negative deltas are rejected."""
        if delta < timedelta(0):
            raise ValueError("SimulatedClock cannot move backwards")
        self._current = self._current + delta


__all__ = ["IClock", "SimulatedClock", "WallClock"]

from __future__ import annotations

import abc
from datetime import datetime, timezone


class Clock(abc.ABC):
    @abc.abstractmethod
    def timestamp(self) -> datetime:
        ...

    @abc.abstractmethod
    def utc_now(self) -> datetime:
        ...


class LiveClock(Clock):
    def timestamp(self) -> datetime:
        return datetime.now()

    def utc_now(self) -> datetime:
        return datetime.now(timezone.utc)


class StaticClock(Clock):
    def __init__(self, start_time: datetime | None = None) -> None:
        if start_time is None:
            start_time = datetime(2024, 1, 1)
        self._time = start_time

    def advance(self, seconds: float) -> None:
        from datetime import timedelta
        self._time += timedelta(seconds=seconds)

    def set_time(self, dt: datetime) -> None:
        self._time = dt

    def timestamp(self) -> datetime:
        return self._time

    def utc_now(self) -> datetime:
        return self._time

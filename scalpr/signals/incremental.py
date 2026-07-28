"""Incremental (O(1)-per-bar) indicators — plan Task 2 / Phase 5.

Each class holds streaming state and matches its batch oracle in
``scalpr.signals.indicators.TechnicalIndicators`` exactly (property-tested
in tests/unit/signals/test_incremental.py). ``snapshot()``/``restore()``
produce JSON-safe dicts so replay checkpoints (ReplayEngine.save_checkpoint)
can persist indicator state without recomputation.

All money/price state is Decimal; snapshots encode Decimals as str.
"""
from __future__ import annotations

from collections import deque
from decimal import Decimal
from typing import Any

from scalpr.domain.tick import OHLCV

_ZERO = Decimal("0")


class IncrementalEMA:
    """Streaming EMA — k = 2/(period+1), seeded at the first close.

    Matches TechnicalIndicators.calculate_ema_series element-for-element.
    """

    def __init__(self, period: int) -> None:
        if period < 1:
            raise ValueError("period must be >= 1")
        self.period = period
        self._k = Decimal(2) / Decimal(period + 1)
        self._value: Decimal | None = None

    @property
    def value(self) -> Decimal | None:
        return self._value

    def update(self, bar: OHLCV) -> Decimal:
        return self.update_close(bar.close)

    def update_close(self, close: Decimal) -> Decimal:
        if self._value is None:
            self._value = close
        else:
            self._value = close * self._k + self._value * (1 - self._k)
        return self._value

    def snapshot(self) -> dict[str, Any]:
        return {
            "period": self.period,
            "value": str(self._value) if self._value is not None else None,
        }

    def restore(self, state: dict[str, Any]) -> None:
        if state["period"] != self.period:
            raise ValueError("snapshot period mismatch")
        self._value = Decimal(state["value"]) if state["value"] is not None else None


class IncrementalATR:
    """Streaming ATR — simple average of the last ``period`` true ranges.

    Matches TechnicalIndicators.calculate_atr fed the same bar prefix.
    """

    def __init__(self, period: int = 14) -> None:
        if period < 1:
            raise ValueError("period must be >= 1")
        self.period = period
        self._prev_close: Decimal | None = None
        self._true_ranges: deque[Decimal] = deque(maxlen=period)

    @property
    def value(self) -> Decimal:
        if not self._true_ranges:
            return _ZERO
        return sum(self._true_ranges, _ZERO) / Decimal(len(self._true_ranges))

    def update(self, bar: OHLCV) -> Decimal:
        if self._prev_close is not None:
            tr = max(
                bar.high - bar.low,
                abs(bar.high - self._prev_close),
                abs(bar.low - self._prev_close),
            )
            self._true_ranges.append(tr)
        self._prev_close = bar.close
        return self.value

    def snapshot(self) -> dict[str, Any]:
        return {
            "period": self.period,
            "prev_close": str(self._prev_close) if self._prev_close is not None else None,
            "true_ranges": [str(tr) for tr in self._true_ranges],
        }

    def restore(self, state: dict[str, Any]) -> None:
        if state["period"] != self.period:
            raise ValueError("snapshot period mismatch")
        self._prev_close = (
            Decimal(state["prev_close"]) if state["prev_close"] is not None else None
        )
        self._true_ranges = deque(
            (Decimal(tr) for tr in state["true_ranges"]), maxlen=self.period
        )


class IncrementalMomentum:
    """Streaming rate-of-change momentum: (close - close[-period]) / close[-period].

    Matches TechnicalIndicators.calculate_momentum fed the same close prefix.
    """

    def __init__(self, period: int = 10) -> None:
        if period < 1:
            raise ValueError("period must be >= 1")
        self.period = period
        self._closes: deque[Decimal] = deque(maxlen=period + 1)

    @property
    def value(self) -> Decimal:
        if len(self._closes) < self.period + 1:
            return _ZERO
        past = self._closes[0]
        if past == 0:
            return _ZERO
        return (self._closes[-1] - past) / past

    def update(self, bar: OHLCV) -> Decimal:
        return self.update_close(bar.close)

    def update_close(self, close: Decimal) -> Decimal:
        self._closes.append(close)
        return self.value

    def snapshot(self) -> dict[str, Any]:
        return {"period": self.period, "closes": [str(c) for c in self._closes]}

    def restore(self, state: dict[str, Any]) -> None:
        if state["period"] != self.period:
            raise ValueError("snapshot period mismatch")
        self._closes = deque(
            (Decimal(c) for c in state["closes"]), maxlen=self.period + 1
        )


def ema_series(closes: list[Decimal], *periods: int) -> dict[int, list[Decimal]]:
    """One-pass EMA series for several periods over the same closes.

    Production path for /market/candles indicators: single loop instead of
    one full batch pass per period; output is oracle-identical to
    calculate_ema_series (pinned by tests).
    """
    emas = {p: IncrementalEMA(p) for p in periods}
    out: dict[int, list[Decimal]] = {p: [] for p in periods}
    for close in closes:
        for p, ema in emas.items():
            out[p].append(ema.update_close(close))
    return out


__all__ = [
    "IncrementalATR",
    "IncrementalEMA",
    "IncrementalMomentum",
    "ema_series",
]

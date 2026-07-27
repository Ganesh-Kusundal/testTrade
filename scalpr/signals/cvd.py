from __future__ import annotations

from decimal import Decimal

from scalpr.domain.tick import Tick


class CvdTracker:
    """Tracks Cumulative Volume Delta (CVD) and divergence from price action."""

    def __init__(self) -> None:
        self.cvd: int = 0
        self.history: list[tuple[int, Decimal]] = []  # (cvd, price) history

    def reset(self) -> None:
        self.cvd = 0
        self.history.clear()

    def process_tick(self, tick: Tick, ask_qty: int, bid_qty: int) -> int:
        """Update CVD: ask_qty - bid_qty delta addition."""
        delta = ask_qty - bid_qty
        self.cvd += delta
        self.history.append((self.cvd, tick.ltp))
        if len(self.history) > 100:
            self.history.pop(0)
        return self.cvd

    def is_diverged(self, lookback: int = 5) -> bool:
        """Detect divergence between CVD slope and price slope over lookback window."""
        if len(self.history) < lookback:
            return False

        recent = self.history[-lookback:]
        cvd_start, price_start = recent[0]
        cvd_end, price_end = recent[-1]

        cvd_diff = cvd_end - cvd_start
        price_diff = price_end - price_start

        # Divergence exists if CVD goes up but price goes down, or vice versa
        if (cvd_diff > 0 and price_diff < 0) or (cvd_diff < 0 and price_diff > 0):
            return True
        return False

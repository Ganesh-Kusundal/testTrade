from __future__ import annotations

import threading
from decimal import Decimal

from scalpr.domain.tick import OHLCV


class VolumeProfile:
    """Calculates POC, VAH, VAL, and LVN/HVN zones from aggregated bars."""

    def __init__(self, price_step: Decimal = Decimal("0.50"), value_area_pct: float = 70.0) -> None:
        self.price_step = price_step
        self.value_area_pct = value_area_pct
        self.volume_by_price: dict[Decimal, int] = {}
        self.poc: Decimal = Decimal("0")
        self.vah: Decimal = Decimal("0")
        self.val: Decimal = Decimal("0")
        self._lock = threading.RLock()

    def reset(self) -> None:
        """Anchor reset for session open or structure breaks."""
        with self._lock:
            self.volume_by_price.clear()
            self.poc = Decimal("0")
            self.vah = Decimal("0")
            self.val = Decimal("0")

    def update(self, bar: OHLCV) -> None:
        """Incorporate a closed OHLCV bar into the profile."""
        with self._lock:
            # Simple volume distribution between low and high
            steps = int((bar.high - bar.low) / self.price_step) + 1
            allocated_vol = bar.volume // steps if steps > 0 else bar.volume

            p = bar.low
            while p <= bar.high:
                rounded_p = (p // self.price_step) * self.price_step
                self.volume_by_price[rounded_p] = self.volume_by_price.get(rounded_p, 0) + allocated_vol
                p += self.price_step

            self._recalculate()

    def is_lvn(self, price: Decimal) -> bool:
        """Returns True if price is in a Low Volume Node area."""
        with self._lock:
            if not self.volume_by_price:
                return False
            rounded_p = (price // self.price_step) * self.price_step
            vol = self.volume_by_price.get(rounded_p, 0)

            # Simple check: less than 25% of average volume is LVN
            avg_vol = sum(self.volume_by_price.values()) / len(self.volume_by_price)
            return vol < avg_vol * 0.25

    def _recalculate(self) -> None:
        if not self.volume_by_price:
            return

        # POC (Point of Control) is price with max volume
        self.poc = max(self.volume_by_price, key=lambda k: self.volume_by_price[k])

        # Simple Value Area calculation (VAH, VAL)
        sorted_prices = sorted(self.volume_by_price.keys())
        total_vol = sum(self.volume_by_price.values())
        target_vol = total_vol * (self.value_area_pct / 100.0)

        # Expand from POC
        poc_idx = sorted_prices.index(self.poc)
        left = poc_idx
        right = poc_idx
        accumulated_vol = self.volume_by_price[self.poc]

        while accumulated_vol < target_vol and (left > 0 or right < len(sorted_prices) - 1):
            left_vol = self.volume_by_price[sorted_prices[left - 1]] if left > 0 else 0
            right_vol = self.volume_by_price[sorted_prices[right + 1]] if right < len(sorted_prices) - 1 else 0

            if left_vol >= right_vol and left > 0:
                left -= 1
                accumulated_vol += left_vol
            elif right < len(sorted_prices) - 1:
                right += 1
                accumulated_vol += right_vol
            else:
                break

        self.val = sorted_prices[left]
        self.vah = sorted_prices[right]

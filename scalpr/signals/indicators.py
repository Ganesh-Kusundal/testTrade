from __future__ import annotations

from decimal import Decimal

from scalpr.domain.values import ZERO


class TechnicalIndicators:
    """Helper class containing indicators like ATR and Momentum."""

    @staticmethod
    def calculate_atr(highs: list[Decimal], lows: list[Decimal], closes: list[Decimal], period: int = 14) -> Decimal:
        """Calculate Average True Range (ATR) over a given period."""
        if len(closes) < 2:
            return ZERO

        true_ranges = []
        for i in range(1, len(closes)):
            h = highs[i]
            low_val = lows[i]
            prev_c = closes[i - 1]

            tr = max(
                h - low_val,
                abs(h - prev_c),
                abs(low_val - prev_c)
            )
            true_ranges.append(tr)

        if not true_ranges:
            return ZERO

        # Simple average of TR
        period_tr = true_ranges[-period:]
        return sum(period_tr) / Decimal(len(period_tr))

    @staticmethod
    def calculate_momentum(closes: list[Decimal], period: int = 10) -> Decimal:
        """Calculate rate of change momentum over a given period."""
        if len(closes) < period + 1:
            return ZERO

        current = closes[-1]
        past = closes[-(period + 1)]
        if past == 0:
            return ZERO
        return (current - past) / past

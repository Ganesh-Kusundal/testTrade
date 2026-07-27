from __future__ import annotations

import math
from decimal import Decimal


class TradeAnalytics:
    """Computes attribution, Sharpe ratio, win rate, and drawdown series for portfolio performance."""

    @staticmethod
    def calculate_sharpe_ratio(returns: list[Decimal], risk_free_rate: float = 0.05) -> float:
        """Calculate Sharpe Ratio for portfolio returns."""
        if len(returns) < 2:
            return 0.0

        float_returns = [float(r) for r in returns]
        avg_return = sum(float_returns) / len(float_returns)

        variance = sum((r - avg_return) ** 2 for r in float_returns) / (len(float_returns) - 1)
        std_dev = math.sqrt(variance)

        if std_dev == 0:
            return 0.0

        # Annualized Sharpe ratio assuming daily returns
        sharpe = (avg_return - risk_free_rate / 252.0) / std_dev * math.sqrt(252.0)
        return float(sharpe)

    @staticmethod
    def calculate_win_rate(pnls: list[Decimal]) -> float:
        """Calculate win rate as percentage of winning trades."""
        if not pnls:
            return 0.0
        winners = sum(1 for p in pnls if p > 0)
        return float(winners) / len(pnls)

    @staticmethod
    def calculate_max_drawdown(equity_curve: list[Decimal]) -> Decimal:
        """Compute the maximum peak-to-trough drawdown from an equity curve series."""
        if not equity_curve:
            return Decimal("0")

        peak = Decimal("-Infinity")
        max_dd = Decimal("0")

        for val in equity_curve:
            if val > peak:
                peak = val
            if peak > 0:
                dd = (peak - val) / peak
                if dd > max_dd:
                    max_dd = dd

        return max_dd

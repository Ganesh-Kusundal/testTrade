"""Explicit trading risk parameters — no hidden defaults, fail-closed policy.

Every field is mandatory: risk limits must be stated by the composition root,
never guessed by the risk layer. Broker rate-limit tables are adapter config
and live in scalpr/brokers/rate_limit.py, NOT here.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(slots=True, frozen=True)
class RiskParameters:
    """Single source of trading risk policy (replaces scattered magic numbers)."""
    max_daily_loss: Decimal
    max_position_notional: Decimal
    margin_rate: Decimal
    max_trades_per_day: int
    circuit_breaker_threshold: Decimal  # e.g. 0.03 = trip at 3% drawdown

    def __post_init__(self) -> None:
        for name in (
            "max_daily_loss",
            "max_position_notional",
            "margin_rate",
            "circuit_breaker_threshold",
        ):
            value = getattr(self, name)
            if not isinstance(value, Decimal):
                raise TypeError(f"{name} must be a Decimal (money/risk is never float)")
            if value <= 0:
                raise ValueError(f"{name} must be positive, got {value}")
        if not isinstance(self.max_trades_per_day, int) or self.max_trades_per_day <= 0:
            raise ValueError("max_trades_per_day must be a positive integer")

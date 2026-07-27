from __future__ import annotations

import logging
from decimal import Decimal

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """System-level Circuit Breakers for Daily Loss, Drawdown limits, and manual Halt switch."""

    def __init__(
        self,
        daily_loss_limit_pct: float = 0.03,  # 3% max daily loss
        drawdown_limit_pct: float = 0.05,    # 5% max drawdown
    ) -> None:
        self.daily_loss_limit_pct = Decimal(str(daily_loss_limit_pct))
        self.drawdown_limit_pct = Decimal(str(drawdown_limit_pct))
        self._halted = False
        self._daily_loss_tripped = False
        self._drawdown_tripped = False

    def check_limits(self, portfolio_value: Decimal, daily_loss: Decimal, drawdown: Decimal) -> bool:
        """Evaluate if any circuit breaker is tripped. Returns True if execution is allowed."""
        if self._halted:
            logger.error("CircuitBreaker: System is manually HALTED.")
            return False

        if self._daily_loss_tripped or self._drawdown_tripped:
            logger.error("CircuitBreaker: System already tripped. Manual reset required.")
            return False

        # 1. Daily Loss Limit
        if daily_loss > portfolio_value * self.daily_loss_limit_pct:
            self._daily_loss_tripped = True
            logger.critical(f"CircuitBreaker TRIP: Daily loss ({daily_loss}) exceeded limit ({portfolio_value * self.daily_loss_limit_pct}).")
            return False

        # 2. Drawdown Limit
        if drawdown > self.drawdown_limit_pct:
            self._drawdown_tripped = True
            logger.critical(f"CircuitBreaker TRIP: Drawdown ({drawdown:.2%}) exceeded limit ({self.drawdown_limit_pct:.2%}).")
            return False

        return True

    def halt_all(self) -> None:
        """Trigger instant manual halt of all trading actions."""
        self._halted = True
        logger.warning("CircuitBreaker: Manual KILL SWITCH triggered. All new orders blocked.")

    def reset(self) -> None:
        """Reset all tripped circuit states to normal operations (requires manual intervention)."""
        self._halted = False
        self._daily_loss_tripped = False
        self._drawdown_tripped = False
        logger.info("CircuitBreaker: Reset complete. Trading operations resumed.")

    @property
    def is_tripped(self) -> bool:
        return self._halted or self._daily_loss_tripped or self._drawdown_tripped

    @property
    def state(self) -> dict:
        """Return a serializable snapshot of circuit breaker state."""
        reason = None
        if self._halted:
            reason = "manual_halt"
        elif self._daily_loss_tripped:
            reason = "daily_loss_limit"
        elif self._drawdown_tripped:
            reason = "drawdown_limit"
        
        return {
            "halted": self._halted,
            "daily_loss_tripped": self._daily_loss_tripped,
            "drawdown_tripped": self._drawdown_tripped,
            "is_tripped": self.is_tripped,
            "daily_loss_limit_pct": float(self.daily_loss_limit_pct),
            "drawdown_limit_pct": float(self.drawdown_limit_pct),
            "tripped_reason": reason,
        }

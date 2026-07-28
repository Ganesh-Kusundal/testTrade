"""Thread safety tests for CircuitBreaker."""
import threading
from decimal import Decimal

from scalpr.risk.circuit_breaker import CircuitBreaker


def test_concurrent_check_limits_should_not_corrupt_state():
    """Multiple threads checking limits simultaneously must not corrupt breaker state."""
    cb = CircuitBreaker(daily_loss_limit_pct=0.03, drawdown_limit_pct=0.05)
    results = []
    errors = []

    def check():
        try:
            ok = cb.check_limits(
                portfolio_value=Decimal("100000"),
                daily_loss=Decimal("3500"),  # exceeds 3%
                drawdown=Decimal("0.02"),
            )
            results.append(ok)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=check) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0, f"Thread safety violation: {errors}"
    assert cb.is_tripped  # All checks should have tripped it
    assert all(r is False for r in results)  # All should be blocked


def test_concurrent_reset_should_not_corrupt_state():
    """Multiple threads resetting simultaneously must not corrupt state."""
    cb = CircuitBreaker(daily_loss_limit_pct=0.03, drawdown_limit_pct=0.05)
    cb._halted = True  # Force tripped state
    cb._daily_loss_tripped = True
    errors = []

    def reset():
        try:
            cb.reset()
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=reset) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0
    assert not cb.is_tripped

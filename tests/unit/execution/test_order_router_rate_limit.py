"""K-019: OrderRouter rate limiting tests."""
import time
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from scalpr.domain.instrument import Exchange
from scalpr.domain.order import Order, OrderSide, OrderType
from scalpr.execution.order_router import OrderRateLimitExceeded, OrderRouter
from scalpr.risk.circuit_breaker import CircuitBreaker
from scalpr.risk.order_rate_limiter import OrderRateLimitConfig, OrderRateLimiter
from scalpr.risk.pre_trade import PreTradeRiskGate
from scalpr.simulation.simulated_gateway import SimulatedGateway


def _make_order(order_id="ord_1"):
    return Order(
        order_id=order_id, symbol="RELIANCE", exchange=Exchange.NSE,
        side=OrderSide.BUY, order_type=OrderType.LIMIT,
        quantity=10, price=Decimal("2500"),
    )


def _make_router(rate_limiter=None):
    gateway = SimulatedGateway(starting_capital=Decimal("1000000"))
    risk_gate = PreTradeRiskGate(max_capital_risk_pct=0.03)
    cb = CircuitBreaker()

    return OrderRouter(
        gateway=gateway,
        risk_gate=risk_gate,
        circuit_breaker=cb,
        rate_limiter=rate_limiter,
    )


class TestOrderRateLimiter:
    """K-019: Rate limiter blocks excessive order submissions."""

    def test_rate_limiter_allows_burst_up_to_capacity(self):
        """Rate limiter allows burst_capacity orders in quick succession."""
        config = OrderRateLimitConfig(max_orders_per_second=10.0, burst_capacity=5)
        limiter = OrderRateLimiter(config)

        # Should allow 5 orders (burst capacity)
        for i in range(5):
            assert limiter.acquire(), f"Order {i+1} should be allowed"

    def test_rate_limiter_blocks_excessive_orders(self):
        """Rate limiter blocks orders beyond burst capacity."""
        config = OrderRateLimitConfig(max_orders_per_second=10.0, burst_capacity=3)
        limiter = OrderRateLimiter(config)

        # Exhaust burst
        for _ in range(3):
            assert limiter.acquire()

        # Next should be blocked
        assert not limiter.acquire(), "Order beyond burst capacity should be blocked"

    def test_rate_limiter_refills_over_time(self):
        """Rate limiter refills tokens over time."""
        config = OrderRateLimitConfig(max_orders_per_second=100.0, burst_capacity=2)
        limiter = OrderRateLimiter(config)

        # Exhaust burst
        assert limiter.acquire()
        assert limiter.acquire()
        assert not limiter.acquire()

        # Wait for refill (100/s = 1 token per 10ms)
        time.sleep(0.02)  # 20ms should give ~2 tokens

        # Should be able to acquire again
        assert limiter.acquire(), "Token should have refilled after wait"


class TestOrderRouterRateLimiting:
    """K-019: OrderRouter enforces rate limiting."""

    def test_router_rejects_order_when_rate_limited(self):
        """OrderRouter raises OrderRateLimitExceeded when rate limit hit."""
        config = OrderRateLimitConfig(max_orders_per_second=10.0, burst_capacity=1)
        limiter = OrderRateLimiter(config)
        router = _make_router(rate_limiter=limiter)

        # First order should pass
        router.submit_order(
            order=_make_order("ord_1"),
            positions=[],
            available_margin=Decimal("100000"),
            daily_loss=Decimal("0"),
            portfolio_value=Decimal("1000000"),
        )

        # Second order immediately should be rate limited
        with pytest.raises(OrderRateLimitExceeded):
            router.submit_order(
                order=_make_order("ord_2"),
                positions=[],
                available_margin=Decimal("100000"),
                daily_loss=Decimal("0"),
                portfolio_value=Decimal("1000000"),
            )

    def test_router_allows_orders_without_rate_limiter(self):
        """OrderRouter works without rate limiter (backward compatible)."""
        router = _make_router(rate_limiter=None)

        # Should not raise
        router.submit_order(
            order=_make_order("ord_1"),
            positions=[],
            available_margin=Decimal("100000"),
            daily_loss=Decimal("0"),
            portfolio_value=Decimal("1000000"),
        )

    def test_rate_limit_checked_before_risk_checks(self):
        """Rate limit is checked before risk checks (fail fast)."""
        call_order = []

        mock_gateway = MagicMock(spec=SimulatedGateway)
        mock_risk_gate = MagicMock(spec=PreTradeRiskGate)
        mock_risk_gate.check_order.side_effect = lambda **kw: call_order.append("risk") or (True, "ok")
        mock_cb = MagicMock(spec=CircuitBreaker)
        mock_cb.check_limits.side_effect = lambda **kw: call_order.append("cb") or True

        config = OrderRateLimitConfig(max_orders_per_second=10.0, burst_capacity=1)
        limiter = OrderRateLimiter(config)

        # Override limiter to track calls
        original_acquire = limiter.acquire
        def tracked_acquire():
            call_order.append("rate_limit")
            return original_acquire()
        limiter.acquire = tracked_acquire

        router = OrderRouter(
            gateway=mock_gateway,
            risk_gate=mock_risk_gate,
            circuit_breaker=mock_cb,
            rate_limiter=limiter,
        )

        router.submit_order(
            order=_make_order(),
            positions=[],
            available_margin=Decimal("100000"),
            daily_loss=Decimal("0"),
            portfolio_value=Decimal("1000000"),
        )

        # Rate limit should be checked first
        assert call_order[0] == "rate_limit", f"Rate limit should be checked first, got: {call_order}"

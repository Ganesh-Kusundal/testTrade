"""Tests for PreTradeRiskGate — K-017: reducing orders must not bypass all checks."""
from decimal import Decimal

from scalpr.domain.instrument import Exchange
from scalpr.domain.order import Order, OrderSide, OrderType
from scalpr.domain.position import Position, PositionSide
from scalpr.risk.pre_trade import PreTradeRiskGate


def _make_order(symbol="RELIANCE", side=OrderSide.BUY, quantity=10, price=Decimal("2500")):
    return Order(
        order_id=f"test_{symbol}_{side.value}",
        symbol=symbol,
        exchange=Exchange.NSE,
        side=side,
        order_type=OrderType.LIMIT,
        quantity=quantity,
        price=price,
    )


def _make_position(symbol="RELIANCE", side=PositionSide.LONG, quantity=50, avg_price=Decimal("2400")):
    return Position(
        symbol=symbol,
        position_side=side,
        quantity=quantity,
        avg_price=avg_price,
        exchange=Exchange.NSE,
    )


class TestReducingOrderChecks:
    """K-017: Reducing orders must still validate daily-loss, margin, and quantity."""

    def test_reducing_order_still_checks_daily_loss(self):
        """A reducing order must be rejected if daily loss limit is breached."""
        gate = PreTradeRiskGate(portfolio_value=Decimal("1000000"))
        position = _make_position(side=PositionSide.LONG, quantity=50)
        order = _make_order(side=OrderSide.SELL, quantity=10)  # reducing

        # Daily loss exceeds 3% of portfolio (30000)
        daily_loss = Decimal("50000")
        allowed, reason = gate.check_order(
            order=order,
            positions=[position],
            available_margin=Decimal("500000"),
            required_margin=Decimal("5000"),
            daily_loss=daily_loss,
        )
        assert not allowed, "Reducing order must be rejected when daily loss limit breached"
        assert "daily loss" in reason.lower()

    def test_reducing_order_still_checks_margin(self):
        """A reducing order must be rejected if insufficient margin."""
        gate = PreTradeRiskGate(portfolio_value=Decimal("1000000"))
        position = _make_position(side=PositionSide.LONG, quantity=50)
        order = _make_order(side=OrderSide.SELL, quantity=10)  # reducing

        allowed, reason = gate.check_order(
            order=order,
            positions=[position],
            available_margin=Decimal("100"),  # Very low margin
            required_margin=Decimal("50000"),
            daily_loss=Decimal("0"),
        )
        assert not allowed, "Reducing order must be rejected when margin insufficient"
        assert "margin" in reason.lower()

    def test_reducing_order_rejects_quantity_exceeding_position(self):
        """A reducing order must not exceed the existing position size (prevents reversal)."""
        gate = PreTradeRiskGate(portfolio_value=Decimal("1000000"))
        position = _make_position(side=PositionSide.LONG, quantity=50)
        order = _make_order(side=OrderSide.SELL, quantity=100)  # exceeds position → reversal

        allowed, reason = gate.check_order(
            order=order,
            positions=[position],
            available_margin=Decimal("500000"),
            required_margin=Decimal("5000"),
            daily_loss=Decimal("0"),
        )
        assert not allowed, "Order exceeding position must be rejected (position reversal)"
        assert "reversal" in reason.lower() or "exceed" in reason.lower() or "quantity" in reason.lower()

    def test_reducing_order_within_position_is_allowed(self):
        """A reducing order within position bounds, with OK margin/loss, must pass."""
        gate = PreTradeRiskGate(portfolio_value=Decimal("1000000"))
        position = _make_position(side=PositionSide.LONG, quantity=50)
        order = _make_order(side=OrderSide.SELL, quantity=30)  # within position

        allowed, reason = gate.check_order(
            order=order,
            positions=[position],
            available_margin=Decimal("500000"),
            required_margin=Decimal("5000"),
            daily_loss=Decimal("0"),
        )
        assert allowed, f"Valid reducing order should pass: {reason}"

    def test_reducing_order_bypasses_concentration_check(self):
        """Reducing orders should bypass concentration limit (reducing exposure is good)."""
        gate = PreTradeRiskGate(
            portfolio_value=Decimal("100000"),
            max_concentration_pct=0.20,  # 20% = 20000
        )
        # Position already at 90% concentration
        position = _make_position(side=PositionSide.LONG, quantity=50, avg_price=Decimal("2400"))
        # Reducing sell — should pass even though concentration is high
        order = _make_order(side=OrderSide.SELL, quantity=10)

        allowed, reason = gate.check_order(
            order=order,
            positions=[position],
            available_margin=Decimal("500000"),
            required_margin=Decimal("5000"),
            daily_loss=Decimal("0"),
        )
        assert allowed, f"Reducing order should bypass concentration check: {reason}"


class TestNotionalPricing:
    """K-020: MARKET orders use LTP for notional, no magic numbers."""

    def test_market_order_uses_ltp_for_notional(self):
        """MARKET orders with price=0 must use LTP parameter for notional calculation."""
        gate = PreTradeRiskGate(
            portfolio_value=Decimal("100000"),
            max_capital_risk_pct=0.01,  # 1% = 1000
        )
        order = Order(
            order_id="test_mkt", symbol="RELIANCE", exchange=Exchange.NSE,
            side=OrderSide.BUY, order_type=OrderType.MARKET,
            quantity=10, price=Decimal("0"),  # MARKET order has no price
        )
        # LTP=500 → notional = 10*500 = 5000 > 1000 limit → rejected
        allowed, reason = gate.check_order(
            order=order,
            positions=[],
            available_margin=Decimal("500000"),
            required_margin=Decimal("1000"),
            daily_loss=Decimal("0"),
            ltp=Decimal("500"),
        )
        assert not allowed
        assert "notional" in reason.lower()

    def test_market_order_without_ltp_rejected(self):
        """MARKET orders without LTP must be rejected (no fallback to magic number)."""
        gate = PreTradeRiskGate(portfolio_value=Decimal("100000"))
        order = Order(
            order_id="test_mkt2", symbol="RELIANCE", exchange=Exchange.NSE,
            side=OrderSide.BUY, order_type=OrderType.MARKET,
            quantity=10, price=Decimal("0"),
        )
        allowed, reason = gate.check_order(
            order=order,
            positions=[],
            available_margin=Decimal("500000"),
            required_margin=Decimal("1000"),
            daily_loss=Decimal("0"),
            # No ltp provided
        )
        assert not allowed
        assert "ltp" in reason.lower() or "price" in reason.lower()

    def test_limit_order_uses_own_price(self):
        """LIMIT orders use their own price for notional, LTP is optional."""
        gate = PreTradeRiskGate(
            portfolio_value=Decimal("100000"),
            max_capital_risk_pct=0.50,  # 50% = 50000
            max_concentration_pct=0.50,  # 50% = 50000
        )
        order = _make_order(quantity=10, price=Decimal("2500"))  # notional = 25000
        allowed, reason = gate.check_order(
            order=order,
            positions=[],
            available_margin=Decimal("500000"),
            required_margin=Decimal("5000"),
            daily_loss=Decimal("0"),
        )
        assert allowed, f"LIMIT order with own price should pass: {reason}"

    def test_error_message_says_notional_not_capital_risk(self):
        """Error message must say 'notional' not 'capital risk'."""
        gate = PreTradeRiskGate(
            portfolio_value=Decimal("100000"),
            max_capital_risk_pct=0.01,  # 1% = 1000
        )
        order = _make_order(quantity=10, price=Decimal("2500"))  # notional = 25000 > 1000
        allowed, reason = gate.check_order(
            order=order,
            positions=[],
            available_margin=Decimal("500000"),
            required_margin=Decimal("1000"),
            daily_loss=Decimal("0"),
        )
        assert not allowed
        assert "notional" in reason.lower()
        assert "capital risk" not in reason.lower()

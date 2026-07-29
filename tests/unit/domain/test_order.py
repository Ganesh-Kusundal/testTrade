"""Tests for Order domain entity validation."""
from decimal import Decimal

import pytest

from scalpr.domain.instrument import Exchange
from scalpr.domain.order import Order, OrderSide, OrderType


def _make_order(**overrides):
    defaults = {
        "order_id": "test_order",
        "symbol": "RELIANCE",
        "exchange": Exchange.NSE,
        "side": OrderSide.BUY,
        "order_type": OrderType.LIMIT,
        "quantity": 10,
        "price": Decimal("2500"),
    }
    defaults.update(overrides)
    return Order(**defaults)


class TestOrderQuantityValidation:
    """K-018: Order must reject zero and negative quantities."""

    def test_order_rejects_zero_quantity(self):
        """quantity=0 must raise ValueError — zero-quantity orders are invalid."""
        with pytest.raises(ValueError, match="quantity must be positive"):
            _make_order(quantity=0)

    def test_order_rejects_negative_quantity(self):
        """Negative quantity must raise ValueError."""
        with pytest.raises(ValueError, match="quantity must be positive"):
            _make_order(quantity=-5)

    def test_order_accepts_positive_quantity(self):
        """Positive quantity must be accepted."""
        order = _make_order(quantity=1)
        assert order.quantity == 1

    def test_order_accepts_large_quantity(self):
        """Large positive quantity must be accepted."""
        order = _make_order(quantity=10000)
        assert order.quantity == 10000

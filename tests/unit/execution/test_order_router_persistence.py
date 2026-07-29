"""K-016: OrderRouter must persist BEFORE submitting to broker."""
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from scalpr.domain.fill import Fill
from scalpr.domain.instrument import Exchange
from scalpr.domain.order import Order, OrderSide, OrderState, OrderType
from scalpr.execution.order_router import OrderRouter


def _make_order():
    return Order(
        order_id="ord_1", symbol="RELIANCE", exchange=Exchange.NSE,
        side=OrderSide.BUY, order_type=OrderType.LIMIT,
        quantity=10, price=Decimal("2500"), state=OrderState.PENDING,
    )


def _make_router(mock_gateway, mock_oms, mock_risk_gate=None, mock_cb=None):
    if mock_risk_gate is None:
        mock_risk_gate = MagicMock()
        mock_risk_gate.check_order.return_value = (True, "ok")
    if mock_cb is None:
        mock_cb = MagicMock()
        mock_cb.check_limits.return_value = True
    return OrderRouter(
        gateway=mock_gateway,
        risk_gate=mock_risk_gate,
        circuit_breaker=mock_cb,
        order_manager=mock_oms,
    )


class TestPersistenceBeforeBrokerSubmission:
    """K-016: OMS must record order BEFORE broker receives it."""

    def test_persistence_happens_before_broker_submission(self):
        """add_order must be called BEFORE place_order — prevents orphaned broker orders."""
        call_order = []

        mock_gateway = MagicMock()
        mock_gateway.place_order.side_effect = lambda o: call_order.append("broker")
        fill = Fill("f1", "ord_1", "RELIANCE", OrderSide.BUY, 10, Decimal("2500"))
        mock_gateway.place_order.return_value = fill

        mock_oms = MagicMock()
        mock_oms.add_order.side_effect = lambda o: call_order.append("oms")

        router = _make_router(mock_gateway, mock_oms)
        order = _make_order()

        router.submit_order(
            order=order, positions=[],
            available_margin=Decimal("100000"),
            daily_loss=Decimal("0"),
            portfolio_value=Decimal("1000000"),
        )

        assert call_order == ["oms", "broker"], (
            f"OMS persist must happen before broker submission, got: {call_order}"
        )

    def test_broker_not_called_if_persistence_fails(self):
        """If OMS persistence fails, broker must NEVER receive the order."""
        mock_gateway = MagicMock()
        fill = Fill("f1", "ord_1", "RELIANCE", OrderSide.BUY, 10, Decimal("2500"))
        mock_gateway.place_order.return_value = fill

        mock_oms = MagicMock()
        mock_oms.add_order.side_effect = Exception("DB write failed")

        router = _make_router(mock_gateway, mock_oms)
        order = _make_order()

        with pytest.raises(Exception, match="DB write failed"):
            router.submit_order(
                order=order, positions=[],
                available_margin=Decimal("100000"),
                daily_loss=Decimal("0"),
                portfolio_value=Decimal("1000000"),
            )

        # Broker must NOT have been called
        mock_gateway.place_order.assert_not_called()

    def test_fill_processed_after_persistence(self):
        """Fill processing happens after both OMS persist and broker submission."""
        call_order = []
        fill = Fill("f1", "ord_1", "RELIANCE", OrderSide.BUY, 10, Decimal("2500"))

        mock_gateway = MagicMock()

        def place_order_side_effect(o):
            call_order.append("broker")
            return fill

        mock_gateway.place_order.side_effect = place_order_side_effect

        mock_oms = MagicMock()
        mock_oms.add_order.side_effect = lambda o: call_order.append("oms_add")
        mock_oms.process_fill.side_effect = lambda f: call_order.append("oms_fill")

        router = _make_router(mock_gateway, mock_oms)
        order = _make_order()

        router.submit_order(
            order=order, positions=[],
            available_margin=Decimal("100000"),
            daily_loss=Decimal("0"),
            portfolio_value=Decimal("1000000"),
        )

        assert call_order == ["oms_add", "broker", "oms_fill"], (
            f"Expected [oms_add, broker, oms_fill], got: {call_order}"
        )

"""K-016: OrderRouter must persist BEFORE submitting to broker."""
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from scalpr.domain.instrument import Exchange
from scalpr.domain.order import Order, OrderSide, OrderState, OrderType
from scalpr.execution.order_router import OrderRouter
from scalpr.simulation.simulated_gateway import SimulatedGateway


class _GatewaySpy(SimulatedGateway):
    """SimulatedGateway with call tracking for test assertions."""
    def __init__(self, call_list=None):
        super().__init__(starting_capital=Decimal("1000000"))
        self._track = call_list if call_list is not None else []
        self.place_order_called = False

    def place_order(self, order):
        self.place_order_called = True
        self._track.append("broker")
        return super().place_order(order)


def _make_order():
    return Order(
        order_id="ord_1", symbol="RELIANCE", exchange=Exchange.NSE,
        side=OrderSide.BUY, order_type=OrderType.LIMIT,
        quantity=10, price=Decimal("2500"), state=OrderState.PENDING,
    )


def _make_router(gateway, mock_oms, mock_risk_gate=None, mock_cb=None):
    if mock_risk_gate is None:
        mock_risk_gate = MagicMock()
        mock_risk_gate.check_order.return_value = (True, "ok")
    if mock_cb is None:
        mock_cb = MagicMock()
        mock_cb.check_limits.return_value = True
    return OrderRouter(
        gateway=gateway,
        risk_gate=mock_risk_gate,
        circuit_breaker=mock_cb,
        order_manager=mock_oms,
    )


class TestPersistenceBeforeBrokerSubmission:
    """K-016: OMS must record order BEFORE broker receives it."""

    def test_persistence_happens_before_broker_submission(self):
        """add_order must be called BEFORE place_order — prevents orphaned broker orders."""
        call_order = []

        gateway = _GatewaySpy(call_order)

        mock_oms = MagicMock()
        mock_oms.add_order.side_effect = lambda o: call_order.append("oms")

        router = _make_router(gateway, mock_oms)
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
        gateway = _GatewaySpy()

        mock_oms = MagicMock()
        mock_oms.add_order.side_effect = Exception("DB write failed")

        router = _make_router(gateway, mock_oms)
        order = _make_order()

        with pytest.raises(Exception, match="DB write failed"):
            router.submit_order(
                order=order, positions=[],
                available_margin=Decimal("100000"),
                daily_loss=Decimal("0"),
                portfolio_value=Decimal("1000000"),
            )

        # Broker must NOT have been called
        assert not gateway.place_order_called, \
            "Broker must NOT have been called when persistence fails"

    def test_fill_processed_after_persistence(self):
        """Fill processing happens after both OMS persist and broker submission."""
        call_order = []

        gateway = _GatewaySpy(call_order)

        mock_oms = MagicMock()
        mock_oms.add_order.side_effect = lambda o: call_order.append("oms_add")
        mock_oms.process_fill.side_effect = lambda f: call_order.append("oms_fill")

        router = _make_router(gateway, mock_oms)
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

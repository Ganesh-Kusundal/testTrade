"""OrderRouter must raise on persistence failure after order placed."""
from decimal import Decimal
from unittest.mock import MagicMock

from scalpr.domain.fill import Fill
from scalpr.domain.instrument import Exchange
from scalpr.domain.order import Order, OrderSide, OrderState, OrderType
from scalpr.execution.order_router import OrderRouter, PersistenceError


def _make_order():
    return Order(
        order_id="ord_1", symbol="RELIANCE", exchange=Exchange.NSE,
        side=OrderSide.BUY, order_type=OrderType.LIMIT,
        quantity=10, price=Decimal("2500"), state=OrderState.PENDING,
    )


def test_submit_order_should_raise_on_persistence_failure():
    """If OMS persistence fails after broker order placed, must raise PersistenceError."""
    mock_gateway = MagicMock()
    fill = Fill("f1", "ord_1", "RELIANCE", OrderSide.BUY, 10, Decimal("2500"))
    mock_gateway.place_order.return_value = fill

    mock_risk_gate = MagicMock()
    mock_risk_gate.check_order.return_value = (True, "ok")

    mock_cb = MagicMock()
    mock_cb.check_limits.return_value = True

    mock_oms = MagicMock()
    mock_oms.add_order.side_effect = Exception("DB write failed")

    router = OrderRouter(
        gateway=mock_gateway, risk_gate=mock_risk_gate,
        circuit_breaker=mock_cb, order_manager=mock_oms,
    )

    order = _make_order()
    import pytest
    with pytest.raises(PersistenceError, match="DB write failed"):
        router.submit_order(
            order=order, positions=[],
            available_margin=Decimal("100000"),
            daily_loss=Decimal("0"),
            portfolio_value=Decimal("1000000"),
        )

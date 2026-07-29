"""OrderRouter must raise on persistence failure before order placed (K-016)."""
from decimal import Decimal
from unittest.mock import MagicMock

from scalpr.domain.instrument import Exchange
from scalpr.domain.order import Order, OrderSide, OrderState, OrderType
from scalpr.execution.order_router import OrderRouter


def _make_order():
    return Order(
        order_id="ord_1", symbol="RELIANCE", exchange=Exchange.NSE,
        side=OrderSide.BUY, order_type=OrderType.LIMIT,
        quantity=10, price=Decimal("2500"), state=OrderState.PENDING,
    )


def test_submit_order_should_raise_on_persistence_failure():
    """K-016: If OMS persistence fails, broker must never be called."""
    mock_gateway = MagicMock()

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
    with pytest.raises(Exception, match="DB write failed"):
        router.submit_order(
            order=order, positions=[],
            available_margin=Decimal("100000"),
            daily_loss=Decimal("0"),
            portfolio_value=Decimal("1000000"),
        )
    # Broker must NOT have been called — persistence happens first
    mock_gateway.place_order.assert_not_called()

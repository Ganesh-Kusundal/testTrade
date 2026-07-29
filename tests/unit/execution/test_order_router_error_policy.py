"""OrderRouter must raise on persistence failure before order placed (K-016)."""
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from scalpr.domain.instrument import Exchange
from scalpr.domain.order import Order, OrderSide, OrderState, OrderType
from scalpr.execution.order_router import OrderRouter
from scalpr.oms.order_manager import OrderManager
from scalpr.risk.circuit_breaker import CircuitBreaker
from scalpr.risk.pre_trade import PreTradeRiskGate
from scalpr.simulation.simulated_gateway import SimulatedGateway


def _make_order():
    return Order(
        order_id="ord_1", symbol="RELIANCE", exchange=Exchange.NSE,
        side=OrderSide.BUY, order_type=OrderType.LIMIT,
        quantity=10, price=Decimal("2500"), state=OrderState.PENDING,
    )


def test_submit_order_should_raise_on_persistence_failure():
    """K-016: If OMS persistence fails, broker must never be called."""
    mock_gateway = MagicMock(spec=SimulatedGateway)

    risk_gate = PreTradeRiskGate(max_capital_risk_pct=0.03)
    cb = CircuitBreaker()

    mock_oms = MagicMock(spec=OrderManager)
    mock_oms.add_order.side_effect = Exception("DB write failed")

    router = OrderRouter(
        gateway=mock_gateway, risk_gate=risk_gate,
        circuit_breaker=cb, order_manager=mock_oms,
    )

    order = _make_order()
    with pytest.raises(Exception, match="DB write failed"):
        router.submit_order(
            order=order, positions=[],
            available_margin=Decimal("100000"),
            daily_loss=Decimal("0"),
            portfolio_value=Decimal("1000000"),
        )
    # Broker must NOT have been called — persistence happens first
    mock_gateway.place_order.assert_not_called()

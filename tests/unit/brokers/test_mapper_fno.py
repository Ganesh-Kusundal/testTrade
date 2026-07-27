"""Test that mapper correctly handles F&O exchange segment."""
from decimal import Decimal

import pytest

from scalpr.brokers.dhan.mapper import DhanMapper
from scalpr.domain.order import Order, OrderSide, OrderType, OrderState
from scalpr.domain.instrument import Exchange


def test_mapper_should_handle_nse_fno_exchange_segment():
    """NSE F&O orders must map to exchangeSegment NSE_FNO."""
    order = Order(
        order_id="fno_ord_1", symbol="NIFTY26JUN22000CE",
        exchange=Exchange.NSE_FNO, side=OrderSide.BUY,
        order_type=OrderType.LIMIT, quantity=50,
        price=Decimal("150.00"), state=OrderState.PENDING,
        product_type="INTRADAY",
    )
    result = DhanMapper.order_to_dhan_request(order, "client123", "security456")
    assert result.is_ok
    assert result.value.exchangeSegment == "NSE_FNO"


def test_mapper_should_still_handle_nse_eq():
    """NSE equity orders must still map to NSE_EQ."""
    order = Order(
        order_id="eq_ord_1", symbol="RELIANCE",
        exchange=Exchange.NSE, side=OrderSide.BUY,
        order_type=OrderType.LIMIT, quantity=10,
        price=Decimal("2500.00"), state=OrderState.PENDING,
    )
    result = DhanMapper.order_to_dhan_request(order, "client123", "security789")
    assert result.is_ok
    assert result.value.exchangeSegment == "NSE_EQ"


def test_mapper_should_still_handle_mcx():
    """MCX orders must still map to MCX_COMM."""
    order = Order(
        order_id="mcx_ord_1", symbol="GOLD",
        exchange=Exchange.MCX, side=OrderSide.BUY,
        order_type=OrderType.LIMIT, quantity=1,
        price=Decimal("50000"), state=OrderState.PENDING,
    )
    result = DhanMapper.order_to_dhan_request(order, "client123", "security101")
    assert result.is_ok
    assert result.value.exchangeSegment == "MCX_COMM"


# W3 equivalence guard: every Exchange member must map to the exact segment
# the pre-consolidation if/elif chain produced.
@pytest.mark.parametrize("exchange,expected_segment", [
    (Exchange.NSE, "NSE_EQ"),
    (Exchange.NSE_FNO, "NSE_FNO"),
    (Exchange.MCX, "MCX_COMM"),
    (Exchange.BSE, "BSE_EQ"),
])
def test_mapper_segment_equivalence_all_exchanges(exchange, expected_segment):
    order = Order(
        order_id="eq_guard", symbol="X",
        exchange=exchange, side=OrderSide.BUY,
        order_type=OrderType.LIMIT, quantity=1,
        price=Decimal("100"), state=OrderState.PENDING,
    )
    result = DhanMapper.order_to_dhan_request(order, "c", "s")
    assert result.is_ok
    assert result.value.exchangeSegment == expected_segment

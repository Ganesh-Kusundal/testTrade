"""Contract tests: verify order request payloads match Dhan API expectations.

Dhan API expects these fields for POST /orders:
- dhanClientId: string (non-empty)
- correlationId: string
- transactionType: "BUY" | "SELL"
- exchangeSegment: "NSE_EQ" | "NSE_FNO" | "MCX_COMM" | ...
- productType: "INTRADAY" | "DELIVERY" | "MARGIN"
- orderType: "LIMIT" | "MARKET" | "SL" | "SL-M"
- quantity: integer > 0
- price: string (Decimal as string)
- triggerPrice: string (Decimal as string)
- securityId: string (non-empty)
"""
from decimal import Decimal

import pytest

from scalpr.brokers.dhan.mapper import DhanMapper
from scalpr.domain.instrument import Exchange
from scalpr.domain.order import Order, OrderSide, OrderState, OrderType

REQUIRED_FIELDS = [
    "dhanClientId", "correlationId", "transactionType",
    "exchangeSegment", "productType", "orderType",
    "quantity", "price", "triggerPrice", "securityId",
]


class TestDhanOrderPayloadContract:
    """Verify mapper output matches Dhan API contract."""

    def _map(self, order, exchange=None, security_id="12345"):
        from dataclasses import replace
        if exchange is not None:
            order = replace(order, exchange=exchange)
        result = DhanMapper.order_to_dhan_request(order, "CLIENT_ID", security_id)
        assert result.is_ok, f"Mapping failed: {result.error}"
        return result.value

    def test_all_required_fields_present(self):
        order = Order(
            order_id="t1", symbol="RELIANCE", exchange=Exchange.NSE,
            side=OrderSide.BUY, order_type=OrderType.LIMIT,
            quantity=10, price=Decimal("2500"), state=OrderState.PENDING,
            product_type="INTRADAY",
        )
        dto = self._map(order)
        for field in REQUIRED_FIELDS:
            assert hasattr(dto, field), f"Missing required field: {field}"

    def test_price_must_be_decimal_type(self):
        order = Order(
            order_id="t2", symbol="RELIANCE", exchange=Exchange.NSE,
            side=OrderSide.BUY, order_type=OrderType.LIMIT,
            quantity=10, price=Decimal("2500.50"), state=OrderState.PENDING,
        )
        dto = self._map(order)
        assert isinstance(dto.price, Decimal)
        assert isinstance(dto.triggerPrice, Decimal)

    def test_nse_eq_exchange_segment(self):
        order = Order(
            order_id="t3", symbol="RELIANCE", exchange=Exchange.NSE,
            side=OrderSide.BUY, order_type=OrderType.LIMIT,
            quantity=10, price=Decimal("2500"), state=OrderState.PENDING,
        )
        dto = self._map(order)
        assert dto.exchangeSegment == "NSE_EQ"

    def test_nse_fno_exchange_segment(self):
        order = Order(
            order_id="t4", symbol="NIFTY26JUN22000CE", exchange=Exchange.NSE_FNO,
            side=OrderSide.BUY, order_type=OrderType.LIMIT,
            quantity=50, price=Decimal("150"), state=OrderState.PENDING,
        )
        dto = self._map(order)
        assert dto.exchangeSegment == "NSE_FNO"

    def test_mcx_comm_exchange_segment(self):
        order = Order(
            order_id="t5", symbol="GOLD", exchange=Exchange.MCX,
            side=OrderSide.BUY, order_type=OrderType.LIMIT,
            quantity=1, price=Decimal("50000"), state=OrderState.PENDING,
        )
        dto = self._map(order)
        assert dto.exchangeSegment == "MCX_COMM"

    def test_transaction_type_must_be_buy_or_sell(self):
        for side in [OrderSide.BUY, OrderSide.SELL]:
            order = Order(
                order_id=f"t6_{side.value}", symbol="RELIANCE", exchange=Exchange.NSE,
                side=side, order_type=OrderType.LIMIT,
                quantity=10, price=Decimal("2500"), state=OrderState.PENDING,
            )
            dto = self._map(order)
            assert dto.transactionType in ("BUY", "SELL")

    @pytest.mark.parametrize("order_type,expected", [
        (OrderType.LIMIT, "LIMIT"),
        (OrderType.MARKET, "MARKET"),
        (OrderType.STOP_LOSS, "SL"),
        (OrderType.STOP_LOSS_MARKET, "SL-M"),
    ])
    def test_order_type_mapping(self, order_type, expected):
        order = Order(
            order_id=f"t7_{expected}", symbol="RELIANCE", exchange=Exchange.NSE,
            side=OrderSide.BUY, order_type=order_type,
            quantity=10, price=Decimal("2500"), state=OrderState.PENDING,
        )
        dto = self._map(order)
        assert dto.orderType == expected

    def test_quantity_must_be_positive_integer(self):
        order = Order(
            order_id="t8", symbol="RELIANCE", exchange=Exchange.NSE,
            side=OrderSide.BUY, order_type=OrderType.LIMIT,
            quantity=10, price=Decimal("2500"), state=OrderState.PENDING,
        )
        dto = self._map(order)
        assert isinstance(dto.quantity, int)
        assert dto.quantity > 0

    def test_security_id_must_be_non_empty_string(self):
        order = Order(
            order_id="t9", symbol="RELIANCE", exchange=Exchange.NSE,
            side=OrderSide.BUY, order_type=OrderType.LIMIT,
            quantity=10, price=Decimal("2500"), state=OrderState.PENDING,
        )
        dto = self._map(order, security_id="2885")
        assert dto.securityId == "2885"
        assert len(dto.securityId) > 0

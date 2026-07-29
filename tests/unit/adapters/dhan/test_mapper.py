from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import pytest

from scalpr.adapters.dhan._mapper import (
    InvalidValueError,
    MissingFieldError,
    order_status_from_dhan,
    order_to_dhan_request,
    order_type_from_domain,
    raw_order_to_order,
    raw_trade_to_fill,
    response_to_fill,
    to_option_chain,
    to_position,
    to_quote,
    transaction_type_from_side,
)
from scalpr.domain.instrument import Exchange, SimpleInstrumentId
from scalpr.domain.order import Order, OrderSide, OrderState, OrderType
from scalpr.domain.position import PositionSide, PositionState
from scalpr.domain.values import ZERO

# =========================================================================
# order_to_dhan_request
# =========================================================================

class TestOrderToDhanRequest:
    def test_market_order_buy(self):
        order = Order(
            order_id="o1", symbol="RELIANCE", exchange=Exchange.NSE,
            side=OrderSide.BUY, order_type=OrderType.MARKET,
            quantity=10, price=ZERO,
        )
        result = order_to_dhan_request(order, "11536", "NSE_EQ", "client1")
        assert result["dhanClientId"] == "client1"
        assert result["securityId"] == "11536"
        assert result["exchangeSegment"] == "NSE_EQ"
        assert result["transactionType"] == "BUY"
        assert result["orderType"] == "MARKET"
        assert result["quantity"] == 10

    def test_market_order_sell(self):
        order = Order(
            order_id="o2", symbol="TCS", exchange=Exchange.NSE,
            side=OrderSide.SELL, order_type=OrderType.MARKET,
            quantity=5, price=ZERO,
        )
        result = order_to_dhan_request(order, "11536", "NSE_EQ", "client1")
        assert result["transactionType"] == "SELL"

    def test_limit_order_buy(self):
        order = Order(
            order_id="o3", symbol="RELIANCE", exchange=Exchange.NSE,
            side=OrderSide.BUY, order_type=OrderType.LIMIT,
            quantity=10, price=Decimal("2500.50"),
        )
        result = order_to_dhan_request(order, "11536", "NSE_EQ", "client1")
        assert result["orderType"] == "LIMIT"
        assert result["price"] == "2500.50"

    def test_limit_order_with_correlation_id(self):
        order = Order(
            order_id="o4", symbol="TCS", exchange=Exchange.NSE,
            side=OrderSide.BUY, order_type=OrderType.LIMIT,
            quantity=1, price=Decimal("100"), correlation_id="corr-123",
        )
        result = order_to_dhan_request(order, "11536", "NSE_EQ", "client1")
        assert result["correlationId"] == "corr-123"

    def test_sl_order(self):
        order = Order(
            order_id="o5", symbol="RELIANCE", exchange=Exchange.NSE,
            side=OrderSide.BUY, order_type=OrderType.STOP_LOSS,
            quantity=10, price=Decimal("2500"), trigger_price=Decimal("2480"),
        )
        result = order_to_dhan_request(order, "11536", "NSE_EQ", "client1")
        assert result["orderType"] == "SL"
        assert result["triggerPrice"] == "2480"

    def test_sl_market_order(self):
        order = Order(
            order_id="o6", symbol="RELIANCE", exchange=Exchange.NSE,
            side=OrderSide.SELL, order_type=OrderType.STOP_LOSS_MARKET,
            quantity=10, price=ZERO, trigger_price=Decimal("2400"),
        )
        result = order_to_dhan_request(order, "11536", "NSE_EQ", "client1")
        assert result["orderType"] == "SL-M"

    def test_with_nse_fno_segment(self):
        order = Order(
            order_id="o7", symbol="NIFTY26JUN22000CE", exchange=Exchange.NSE,
            side=OrderSide.BUY, order_type=OrderType.LIMIT,
            quantity=50, price=Decimal("150.00"),
        )
        result = order_to_dhan_request(order, "sec456", "NSE_FNO", "client1")
        assert result["exchangeSegment"] == "NSE_FNO"

    def test_with_bse_fno_segment(self):
        order = Order(
            order_id="o8", symbol="SENSEX2570881000CE", exchange=Exchange.BSE,
            side=OrderSide.BUY, order_type=OrderType.LIMIT,
            quantity=20, price=Decimal("120.00"),
        )
        result = order_to_dhan_request(order, "sec999", "BSE_FNO", "client1")
        assert result["exchangeSegment"] == "BSE_FNO"

    def test_with_mcx_segment(self):
        order = Order(
            order_id="o9", symbol="GOLD", exchange=Exchange.MCX,
            side=OrderSide.BUY, order_type=OrderType.LIMIT,
            quantity=1, price=Decimal("50000"),
        )
        result = order_to_dhan_request(order, "sec101", "MCX_COMM", "client1")
        assert result["exchangeSegment"] == "MCX_COMM"

    def test_with_idx_i_segment(self):
        order = Order(
            order_id="o10", symbol="NIFTY", exchange=Exchange.NSE,
            side=OrderSide.BUY, order_type=OrderType.MARKET,
            quantity=75, price=ZERO,
        )
        result = order_to_dhan_request(order, "13", "IDX_I", "client1")
        assert result["exchangeSegment"] == "IDX_I"

    def test_raises_on_invalid_order_type(self):
        class FakeType:
            value = "FAKE"
        order = Order(
            order_id="o11", symbol="X", exchange=Exchange.NSE,
            side=OrderSide.BUY, order_type="FAKE_TYPE",  # type: ignore[arg-type]
            quantity=1, price=Decimal("100"),
        )
        with pytest.raises(InvalidValueError):
            order_to_dhan_request(order, "s", "NSE_EQ", "c")

    def test_raises_on_invalid_side(self):
        order = Order(
            order_id="o12", symbol="X", exchange=Exchange.NSE,
            side="HOLD", order_type=OrderType.MARKET,  # type: ignore[arg-type]
            quantity=1, price=ZERO,
        )
        with pytest.raises(InvalidValueError):
            order_to_dhan_request(order, "s", "NSE_EQ", "c")

    def test_empty_correlation_id(self):
        order = Order(
            order_id="o13", symbol="X", exchange=Exchange.NSE,
            side=OrderSide.BUY, order_type=OrderType.MARKET,
            quantity=1, price=ZERO, correlation_id=None,
        )
        result = order_to_dhan_request(order, "s", "NSE_EQ", "c")
        assert result["correlationId"] == ""

    def test_zero_quantity_order(self):
        order = Order(
            order_id="o14", symbol="X", exchange=Exchange.NSE,
            side=OrderSide.BUY, order_type=OrderType.MARKET,
            quantity=1, price=ZERO,
        )
        result = order_to_dhan_request(order, "s", "NSE_EQ", "c")
        assert result["quantity"] == 1

    def test_round_lot_quantity(self):
        order = Order(
            order_id="o15", symbol="X", exchange=Exchange.NSE,
            side=OrderSide.BUY, order_type=OrderType.MARKET,
            quantity=75, price=ZERO,
        )
        result = order_to_dhan_request(order, "s", "NSE_EQ", "c")
        assert result["quantity"] == 75

    def test_client_id_in_request(self):
        order = Order(
            order_id="o16", symbol="X", exchange=Exchange.NSE,
            side=OrderSide.BUY, order_type=OrderType.MARKET,
            quantity=1, price=ZERO,
        )
        result = order_to_dhan_request(order, "s", "NSE_EQ", "my-client-007")
        assert result["dhanClientId"] == "my-client-007"

    def test_price_as_string_in_dict(self):
        order = Order(
            order_id="o17", symbol="X", exchange=Exchange.NSE,
            side=OrderSide.BUY, order_type=OrderType.LIMIT,
            quantity=10, price=Decimal("1234.56"),
        )
        result = order_to_dhan_request(order, "s", "NSE_EQ", "c")
        assert isinstance(result["price"], str)
        assert result["price"] == "1234.56"

    def test_trigger_price_as_string_in_dict(self):
        order = Order(
            order_id="o18", symbol="X", exchange=Exchange.NSE,
            side=OrderSide.BUY, order_type=OrderType.STOP_LOSS,
            quantity=10, price=Decimal("100"), trigger_price=Decimal("95.50"),
        )
        result = order_to_dhan_request(order, "s", "NSE_EQ", "c")
        assert isinstance(result["triggerPrice"], str)
        assert result["triggerPrice"] == "95.50"

    def test_validity_default(self):
        order = Order(
            order_id="o19", symbol="X", exchange=Exchange.NSE,
            side=OrderSide.BUY, order_type=OrderType.MARKET,
            quantity=1, price=ZERO,
        )
        result = order_to_dhan_request(order, "s", "NSE_EQ", "c")
        assert result["validity"] == "DAY"

    def test_product_type(self):
        order = Order(
            order_id="o20", symbol="X", exchange=Exchange.NSE,
            side=OrderSide.BUY, order_type=OrderType.MARKET,
            quantity=1, price=ZERO, product_type="CNC",
        )
        result = order_to_dhan_request(order, "s", "NSE_EQ", "c")
        assert result["productType"] == "CNC"


# =========================================================================
# response_to_fill
# =========================================================================

class TestResponseToFill:
    def make_order(self, **kwargs: Any) -> Order:
        defaults = {
            "order_id": "o1", "symbol": "RELIANCE", "exchange": Exchange.NSE,
            "side": OrderSide.BUY, "order_type": OrderType.MARKET,
            "quantity": 10, "price": ZERO,
        }
        defaults.update(kwargs)
        return Order(**defaults)

    def test_full_fill(self):
        order = self.make_order(filled_quantity=10, avg_price=Decimal("2500"))
        resp = {"orderId": "ORD123", "filledQuantity": 10, "tradedPrice": "2500.50"}
        fill = response_to_fill(resp, order)
        assert fill.fill_id == "f_ORD123"
        assert fill.order_id == "ORD123"
        assert fill.symbol == "RELIANCE"
        assert fill.side == OrderSide.BUY
        assert fill.quantity == 10
        assert fill.price == Decimal("2500.50")

    def test_partial_fill(self):
        order = self.make_order(filled_quantity=3, avg_price=Decimal("2490"))
        resp = {"orderId": "ORD456", "filledQuantity": 3, "tradedPrice": "2490.00"}
        fill = response_to_fill(resp, order)
        assert fill.quantity == 3
        assert fill.price == Decimal("2490.00")

    def test_fill_with_fillPrice_fallback(self):
        order = self.make_order(filled_quantity=5)
        resp = {"orderId": "ORD789", "filledQuantity": 5, "fillPrice": "2520.75"}
        fill = response_to_fill(resp, order)
        assert fill.price == Decimal("2520.75")

    def test_fill_falls_back_to_order_fields(self):
        order = self.make_order(filled_quantity=7, avg_price=Decimal("2500"))
        resp = {"orderId": "ORD999"}
        fill = response_to_fill(resp, order)
        assert fill.quantity == 7
        assert fill.price == Decimal("2500")

    def test_raises_missing_order_id(self):
        order = self.make_order()
        with pytest.raises(MissingFieldError):
            response_to_fill({}, order)

    def test_raises_missing_order_id_none(self):
        order = self.make_order()
        with pytest.raises(MissingFieldError):
            response_to_fill({"orderId": None}, order)

    def test_fill_has_timestamp(self):
        order = self.make_order(filled_quantity=1, avg_price=Decimal("100"))
        resp = {"orderId": "ORD_TS", "filledQuantity": 1}
        fill = response_to_fill(resp, order)
        assert fill.timestamp is not None
        assert fill.timestamp.tzinfo == timezone.utc

    def test_sell_fill(self):
        order = self.make_order(side=OrderSide.SELL, filled_quantity=5)
        resp = {"orderId": "ORD_SELL", "filledQuantity": 5, "tradedPrice": "3000"}
        fill = response_to_fill(resp, order)
        assert fill.side == OrderSide.SELL

    def test_zero_quantity_fill(self):
        order = self.make_order(filled_quantity=0, avg_price=ZERO)
        resp = {"orderId": "ORD_ZERO", "filledQuantity": 0, "tradedPrice": "2500"}
        fill = response_to_fill(resp, order)
        assert fill.quantity == 0

    def test_fill_id_format(self):
        order = self.make_order(filled_quantity=10)
        resp = {"orderId": "ABC-123-XYZ"}
        fill = response_to_fill(resp, order)
        assert fill.fill_id == "f_ABC-123-XYZ"


# =========================================================================
# to_position
# =========================================================================

class TestToPosition:
    def test_long_position(self):
        data = {"symbol": "RELIANCE", "exchange": "NSE", "quantity": 10, "avgPrice": "2500", "ltp": "2550", "realizedPnl": "500"}
        pos = to_position(data)
        assert pos.symbol == "RELIANCE"
        assert pos.quantity == 10
        assert pos.avg_price == Decimal("2500")
        assert pos.ltp == Decimal("2550")
        assert pos.position_side == PositionSide.LONG
        assert pos.state == PositionState.OPEN

    def test_long_position_unrealised_pnl(self):
        data = {"symbol": "TCS", "exchange": "NSE", "quantity": 5, "avgPrice": "3500", "ltp": "3600"}
        pos = to_position(data)
        assert pos.unrealised_pnl == Decimal("500")

    def test_short_position(self):
        data = {"symbol": "RELIANCE", "exchange": "NSE", "quantity": -10, "avgPrice": "2600", "ltp": "2500", "realizedPnl": "-200"}
        pos = to_position(data)
        assert pos.quantity == -10
        assert pos.position_side == PositionSide.SHORT
        assert pos.state == PositionState.OPEN

    def test_short_position_unrealised_pnl(self):
        data = {"symbol": "TCS", "exchange": "NSE", "quantity": -5, "avgPrice": "3500", "ltp": "3400"}
        pos = to_position(data)
        assert pos.unrealised_pnl == Decimal("500")

    def test_flat_position(self):
        data = {"symbol": "RELIANCE", "exchange": "NSE", "quantity": 0, "avgPrice": "2500", "ltp": "2550"}
        pos = to_position(data)
        assert pos.quantity == 0
        assert pos.position_side == PositionSide.FLAT
        assert pos.state == PositionState.FLAT
        assert pos.unrealised_pnl == ZERO

    def test_flat_realised_pnl(self):
        data = {"symbol": "RELIANCE", "exchange": "NSE", "quantity": 0, "avgPrice": "2500", "ltp": "2550", "realizedPnl": "1000"}
        pos = to_position(data)
        assert pos.realised_pnl == Decimal("1000")

    def test_bse_exchange(self):
        data = {"symbol": "SENSEX", "exchange": "BSE", "quantity": 10, "avgPrice": "60000", "ltp": "60500"}
        pos = to_position(data)
        assert pos.exchange == Exchange.BSE

    def test_mcx_exchange(self):
        data = {"symbol": "GOLD", "exchange": "MCX", "quantity": 1, "avgPrice": "50000", "ltp": "50500"}
        pos = to_position(data)
        assert pos.exchange == Exchange.MCX

    def test_missing_exchange_defaults_to_nse(self):
        data = {"symbol": "X", "quantity": 10, "avgPrice": "100", "ltp": "110"}
        pos = to_position(data)
        assert pos.exchange == Exchange.NSE

    def test_missing_symbol_defaults_to_empty(self):
        data = {"exchange": "NSE", "quantity": 10, "avgPrice": "100", "ltp": "110"}
        pos = to_position(data)
        assert pos.symbol == ""

    def test_raises_on_invalid_quantity(self):
        data = {"symbol": "X", "exchange": "NSE", "quantity": "abc", "avgPrice": "100", "ltp": "110"}
        with pytest.raises(InvalidValueError):
            to_position(data)

    def test_raises_on_invalid_avg_price(self):
        data = {"symbol": "X", "exchange": "NSE", "quantity": 10, "avgPrice": None, "ltp": "110"}
        with pytest.raises(InvalidValueError):
            to_position(data)

    def test_raises_on_invalid_ltp(self):
        data = {"symbol": "X", "exchange": "NSE", "quantity": 10, "avgPrice": "100", "ltp": None}
        with pytest.raises(InvalidValueError):
            to_position(data)

    def test_negative_short_quantity(self):
        data = {"symbol": "X", "exchange": "NSE", "quantity": -25, "avgPrice": "200", "ltp": "190"}
        pos = to_position(data)
        assert pos.quantity == -25
        assert pos.unrealised_pnl == Decimal("250")

    def test_large_position(self):
        data = {"symbol": "NIFTY", "exchange": "NSE", "quantity": 750, "avgPrice": "18000", "ltp": "18100"}
        pos = to_position(data)
        assert pos.unrealised_pnl == Decimal(750) * (Decimal("18100") - Decimal("18000"))

    def test_decimal_values_from_string(self):
        data = {"symbol": "X", "exchange": "NSE", "quantity": 10, "avgPrice": "100.50", "ltp": "101.75"}
        pos = to_position(data)
        assert pos.avg_price == Decimal("100.50")
        assert pos.ltp == Decimal("101.75")


# =========================================================================
# to_quote / to_option_chain
# =========================================================================

class TestToQuote:
    def test_rest_quote(self):
        instrument_id = SimpleInstrumentId.parse("RELIANCE:NSE")
        data = {
            "last_price": "2500.50",
            "net_change": "12.00",
            "ohlc": {"open": "2480", "high": "2510", "low": "2475", "close": "2488.50"},
            "volume": 1500000,
            "oi": 50000,
        }
        quote = to_quote(data, instrument_id)
        assert isinstance(quote, dict)
        assert quote["symbol"] == "RELIANCE"
        assert quote["ltp"] == Decimal("2500.50")
        assert quote["open"] == Decimal("2480")
        assert quote["high"] == Decimal("2510")
        assert quote["low"] == Decimal("2475")
        assert quote["close"] == Decimal("2488.50")
        assert quote["volume"] == 1500000
        assert quote["change"] == Decimal("12.00")
        assert quote["oi"] == 50000

    def test_rest_quote_change_percent(self):
        instrument_id = SimpleInstrumentId.parse("TCS:NSE")
        data = {
            "last_price": "3600",
            "net_change": "50",
            "ohlc": {"open": "3550", "high": "3620", "low": "3540", "close": "3550"},
            "volume": 500000,
            "oi": 0,
        }
        quote = to_quote(data, instrument_id)
        expected_pct = Decimal("50") / Decimal("3550") * 100
        assert quote["change_percent"] == expected_pct

    def test_rest_quote_zero_close(self):
        instrument_id = SimpleInstrumentId.parse("X:NSE")
        data = {
            "last_price": "100",
            "net_change": "0",
            "ohlc": {"open": "0", "high": "0", "low": "0", "close": "0"},
            "volume": 0,
            "oi": 0,
        }
        quote = to_quote(data, instrument_id)
        assert quote["change_percent"] == ZERO


class TestToOptionChain:
    def test_empty_chain(self):
        assert to_option_chain([]) == []

    def test_single_strike(self):
        data = [{
            "strike": "25000",
            "ce": {
                "security_id": 123,
                "symbol": "NIFTY 01AUG26 25000 CE",
                "top_bid_price": "100",
                "top_bid_quantity": 500,
                "top_ask_price": "105",
                "top_ask_quantity": 500,
                "oi": 10000,
                "volume": 5000,
                "last_price": "102",
                "implied_volatility": "15.5",
                "greeks": {"delta": "0.5", "theta": "-0.2", "gamma": "0.01", "vega": "0.3"},
            },
            "pe": {
                "security_id": 124,
                "symbol": "NIFTY 01AUG26 25000 PE",
                "top_bid_price": "95",
                "top_bid_quantity": 300,
                "top_ask_price": "98",
                "top_ask_quantity": 300,
                "oi": 8000,
                "volume": 3000,
                "last_price": "96",
                "implied_volatility": "14.2",
                "greeks": {"delta": "-0.5", "theta": "-0.15", "gamma": "0.01", "vega": "0.25"},
            },
        }]
        result = to_option_chain(data)
        assert len(result) == 2
        assert result[0]["strike"] == Decimal("25000")
        assert result[0]["option_type"] == "CE"
        assert result[0]["bid"] == Decimal("100")
        assert result[0]["ask"] == Decimal("105")
        assert result[0]["delta"] == "0.5"

    def test_ce_only(self):
        data = [{
            "strike": "20000",
            "ce": {
                "security_id": 1,
                "top_bid_price": "50",
                "top_ask_price": "55",
                "oi": 1000,
                "volume": 500,
                "last_price": "52",
                "greeks": {},
            },
        }]
        result = to_option_chain(data)
        assert len(result) == 1
        assert result[0]["option_type"] == "CE"

    def test_pe_only(self):
        data = [{
            "strike": "20000",
            "pe": {
                "security_id": 2,
                "top_bid_price": "45",
                "top_ask_price": "48",
                "oi": 2000,
                "volume": 300,
                "last_price": "46",
                "greeks": {},
            },
        }]
        result = to_option_chain(data)
        assert len(result) == 1
        assert result[0]["option_type"] == "PE"

    def test_multiple_strikes(self):
        data = [
            {"strike": "20000", "ce": {"security_id": 1, "top_bid_price": "100", "top_ask_price": "105", "oi": 1000, "volume": 500, "last_price": "102", "greeks": {}}},
            {"strike": "20100", "ce": {"security_id": 3, "top_bid_price": "50", "top_ask_price": "55", "oi": 2000, "volume": 300, "last_price": "52", "greeks": {}}},
        ]
        result = to_option_chain(data)
        assert len(result) == 2
        assert result[0]["strike"] == Decimal("20000")
        assert result[1]["strike"] == Decimal("20100")

    def test_missing_greeks(self):
        data = [{
            "strike": "25000",
            "ce": {"security_id": 1, "top_bid_price": "100", "top_ask_price": "105", "oi": 1000, "volume": 500, "last_price": "102"},
        }]
        result = to_option_chain(data)
        assert result[0]["delta"] is None
        assert result[0]["theta"] is None

    def test_none_security_id(self):
        data = [{
            "strike": "25000",
            "ce": {"security_id": None, "top_bid_price": "100", "top_ask_price": "105", "oi": 1000, "volume": 500, "last_price": "102", "greeks": {}},
        }]
        result = to_option_chain(data)
        assert result[0]["security_id"] is None


# =========================================================================
# order_status_from_dhan
# =========================================================================

class TestOrderStatusFromDhan:
    @pytest.mark.parametrize("dhan_status,expected", [
        ("PENDING", OrderState.PENDING),
        ("OPEN", OrderState.OPEN),
        ("PARTIALLY FILLED", OrderState.PARTIALLY_FILLED),
        ("FILLED", OrderState.FILLED),
        ("TRADED", OrderState.FILLED),
        ("CANCELLED", OrderState.CANCELLED),
        ("REJECTED", OrderState.REJECTED),
        ("EXPIRED", OrderState.EXPIRED),
        ("TRIGGER PENDING", OrderState.PENDING),
        ("pending", OrderState.PENDING),
        ("Traded", OrderState.FILLED),
    ])
    def test_known_statuses(self, dhan_status, expected):
        assert order_status_from_dhan(dhan_status) == expected

    def test_unknown_status_raises(self):
        with pytest.raises(InvalidValueError):
            order_status_from_dhan("UNKNOWN_STATUS")

    def test_empty_status_raises(self):
        with pytest.raises(InvalidValueError):
            order_status_from_dhan("")


# =========================================================================
# transaction_type_from_side
# =========================================================================

class TestTransactionTypeFromSide:
    def test_buy(self):
        assert transaction_type_from_side(OrderSide.BUY) == "BUY"

    def test_sell(self):
        assert transaction_type_from_side(OrderSide.SELL) == "SELL"

    def test_raises_on_invalid_side(self):
        with pytest.raises(InvalidValueError):
            transaction_type_from_side("HOLD")  # type: ignore[arg-type]


# =========================================================================
# order_type_from_domain
# =========================================================================

class TestOrderTypeFromDomain:
    @pytest.mark.parametrize("order_type,expected", [
        (OrderType.LIMIT, "LIMIT"),
        (OrderType.MARKET, "MARKET"),
        (OrderType.STOP_LOSS, "SL"),
        (OrderType.STOP_LOSS_MARKET, "SL-M"),
    ])
    def test_all_types(self, order_type, expected):
        assert order_type_from_domain(order_type) == expected

    def test_raises_on_unknown_type(self):
        with pytest.raises(InvalidValueError):
            order_type_from_domain("FAKE")  # type: ignore[arg-type]


# =========================================================================
# raw_order_to_order
# =========================================================================

class TestRawOrderToOrder:
    def test_minimal(self):
        raw = {"order_id": "ORD1", "symbol": "RELIANCE", "side": "BUY", "order_type": "MARKET", "quantity": 10}
        order = raw_order_to_order(raw)
        assert order.order_id == "ORD1"
        assert order.symbol == "RELIANCE"
        assert order.side == OrderSide.BUY
        assert order.order_type == OrderType.MARKET
        assert order.quantity == 10

    def test_state_mapping(self):
        raw = {"order_id": "O1", "symbol": "X", "side": "BUY", "order_type": "LIMIT", "quantity": 1, "status": "TRADED", "price": "100"}
        order = raw_order_to_order(raw)
        assert order.state == OrderState.FILLED

    def test_sl_order_type(self):
        raw = {"order_id": "O1", "symbol": "X", "side": "SELL", "order_type": "SL", "quantity": 5}
        order = raw_order_to_order(raw)
        assert order.order_type == OrderType.STOP_LOSS

    def test_sl_m_order_type(self):
        raw = {"order_id": "O1", "symbol": "X", "side": "BUY", "order_type": "SL-M", "quantity": 10}
        order = raw_order_to_order(raw)
        assert order.order_type == OrderType.STOP_LOSS_MARKET

    def test_mcx_segment(self):
        raw = {"order_id": "O1", "symbol": "GOLD", "side": "BUY", "order_type": "LIMIT", "quantity": 1, "price": "50000", "exchange_segment": "MCX_COMM"}
        order = raw_order_to_order(raw)
        assert order.exchange == Exchange.MCX

    def test_bse_segment(self):
        raw = {"order_id": "O1", "symbol": "SENSEX", "side": "BUY", "order_type": "LIMIT", "quantity": 1, "price": "60000", "exchange_segment": "BSE_EQ"}
        order = raw_order_to_order(raw)
        assert order.exchange == Exchange.BSE


# =========================================================================
# raw_trade_to_fill
# =========================================================================

class TestRawTradeToFill:
    def test_minimal(self):
        raw = {"trade_id": "T1", "order_id": "O1", "symbol": "RELIANCE", "side": "BUY", "quantity": 10, "price": "2500.50"}
        fill = raw_trade_to_fill(raw)
        assert fill.fill_id == "T1"
        assert fill.order_id == "O1"
        assert fill.symbol == "RELIANCE"
        assert fill.side == OrderSide.BUY
        assert fill.quantity == 10
        assert fill.price == Decimal("2500.50")

    def test_sell_side(self):
        raw = {"trade_id": "T2", "order_id": "O2", "symbol": "TCS", "side": "SELL", "quantity": 5, "price": "3500"}
        fill = raw_trade_to_fill(raw)
        assert fill.side == OrderSide.SELL

    def test_with_trade_date(self):
        raw = {"trade_id": "T3", "order_id": "O3", "symbol": "X", "side": "BUY", "quantity": 1, "price": "100", "trade_date": "2026-07-29T10:30:00"}
        fill = raw_trade_to_fill(raw)
        assert fill.timestamp is not None
        assert isinstance(fill.timestamp, datetime)

    def test_with_exchange_segment(self):
        raw = {"trade_id": "T4", "order_id": "O4", "symbol": "X", "side": "BUY", "quantity": 1, "price": "100", "exchange_segment": "NSE_FNO"}
        fill = raw_trade_to_fill(raw)
        assert fill.exchange == "NSE"

    def test_zero_price(self):
        raw = {"trade_id": "T5", "order_id": "O5", "symbol": "X", "side": "SELL", "quantity": 1, "price": "0"}
        fill = raw_trade_to_fill(raw)
        assert fill.price == ZERO

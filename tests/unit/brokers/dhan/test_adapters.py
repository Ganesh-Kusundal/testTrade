"""Comprehensive unit tests for Dhan broker adapters.

Tests cover MarketDataAdapter, OrdersAdapter, PortfolioAdapter,
and HistoricalDataAdapter with happy paths, error scenarios,
idempotency, P&L calculations, timeframe validation, and symbol
resolution integration.
"""

from __future__ import annotations

import pytest
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

from scalpr.brokers.dhan.market_data import MarketDataAdapter
from scalpr.brokers.dhan.orders import OrdersAdapter
from scalpr.brokers.dhan.portfolio import PortfolioAdapter
from scalpr.brokers.dhan.historical import HistoricalDataAdapter
from scalpr.brokers.dhan.exceptions import BrokerError, OrderError, InstrumentNotFoundError
from scalpr.brokers.dhan.dtos import DhanOrderResponse
from scalpr.domain.order import Order, OrderSide, OrderType, OrderState
from scalpr.domain.fill import Fill
from scalpr.domain.position import Position, PositionSide, PositionState
from scalpr.domain.instrument import Exchange


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_http_client():
    """Provide a MagicMock DhanHttpClient."""
    client = MagicMock()
    client.client_id = "test_client_123"
    return client


@pytest.fixture
def mock_resolver():
    """Provide a SymbolResolver stub that resolves known symbols."""
    resolver = MagicMock()
    inst = MagicMock()
    inst.symbol = "RELIANCE"
    inst.exchange = Exchange.NSE
    inst.segment = MagicMock()
    inst.segment.value = "EQUITY"
    inst.security_id = 1  # Integer, not string
    inst.lot_size = 1
    inst.tick_size = Decimal("0.05")
    resolver.resolve.return_value = inst
    resolver.wire_segment_of.return_value = "NSE_EQ"
    resolver.instrument_kind_of.return_value = "EQUITY"
    return resolver


@pytest.fixture
def market_adapter(mock_http_client, mock_resolver):
    return MarketDataAdapter(client=mock_http_client, resolver=mock_resolver)


@pytest.fixture
def orders_adapter(mock_http_client, mock_resolver):
    return OrdersAdapter(client=mock_http_client, resolver=mock_resolver)


@pytest.fixture
def portfolio_adapter(mock_http_client, mock_resolver):
    return PortfolioAdapter(client=mock_http_client, resolver=mock_resolver)


@pytest.fixture
def historical_adapter(mock_http_client, mock_resolver):
    return HistoricalDataAdapter(client=mock_http_client, resolver=mock_resolver)


def make_order(
    order_id="ord_1",
    symbol="RELIANCE",
    exchange=Exchange.NSE,
    side=OrderSide.BUY,
    order_type=OrderType.LIMIT,
    quantity=10,
    price=Decimal("2500.00"),
    trigger_price=Decimal("0"),
    state=OrderState.PENDING,
    correlation_id=None,
    product_type="INTRADAY",
):
    """Factory helper for Order domain objects."""
    return Order(
        order_id=order_id,
        symbol=symbol,
        exchange=exchange,
        side=side,
        order_type=order_type,
        quantity=quantity,
        price=price,
        trigger_price=trigger_price,
        state=state,
        correlation_id=correlation_id,
        product_type=product_type,
    )


# ===================================================================
# TestMarketDataAdapter
# ===================================================================

class TestMarketDataAdapter:
    """Tests for MarketDataAdapter covering LTP, Quote, Depth, Batch."""

    # --- get_ltp ---

    def test_should_return_ltp_as_decimal_when_api_returns_valid_data(self, market_adapter, mock_http_client):
        # API response uses string keys (JSON serialization)
        mock_http_client.post.return_value = {
            "data": {"NSE_EQ": {"1": {"last_price": "2510.50"}}}
        }
        ltp = market_adapter.get_ltp("RELIANCE", "NSE")
        assert isinstance(ltp, Decimal)
        assert ltp == Decimal("2510.50")
        # Request uses integer security_id
        mock_http_client.post.assert_called_once_with(
            "/marketfeed/ltp", json={"NSE_EQ": [1]}
        )

    def test_should_raise_value_error_when_ltp_missing_for_symbol(self, market_adapter, mock_http_client):
        mock_http_client.post.return_value = {"data": {"NSE_EQ": {}}}
        with pytest.raises(ValueError, match="No LTP data for RELIANCE"):
            market_adapter.get_ltp("RELIANCE", "NSE")

    def test_should_resolve_segment_via_resolver_for_ltp(self, market_adapter, mock_http_client, mock_resolver):
        mock_http_client.post.return_value = {
            "data": {"NSE_EQ": {"1": {"last_price": "100"}}}
        }
        market_adapter.get_ltp("RELIANCE", "NSE")
        mock_resolver.resolve.assert_called_once_with("RELIANCE", "NSE")

    # --- get_quote ---

    def test_should_return_full_quote_with_decimal_fields(self, market_adapter, mock_http_client):
        mock_http_client.post.return_value = {
            "data": {
                "NSE_EQ": {
                    "1": {
                        "last_price": 2510.50,
                        "net_change": 15.30,
                        "volume": 123456,
                        "average_price": 2505.25,
                        "buy_quantity": 50000,
                        "sell_quantity": 45000,
                        "last_quantity": 100,
                        "last_trade_time": 1722345600,
                        "lower_circuit_limit": 2250.00,
                        "upper_circuit_limit": 2750.00,
                        "oi": 1000000,
                        "oi_day_high": 1200000,
                        "oi_day_low": 900000,
                        "ohlc": {
                            "open": 2495.00,
                            "high": 2520.00,
                            "low": 2490.00,
                            "close": 2495.20,
                        },
                    }
                }
            }
        }
        quote = market_adapter.get_quote("RELIANCE", "NSE")
        assert quote["symbol"] == "RELIANCE"
        assert quote["ltp"] == Decimal("2510.50")
        assert quote["open"] == Decimal("2495.00")
        assert quote["high"] == Decimal("2520.00")
        assert quote["low"] == Decimal("2490.00")
        assert quote["close"] == Decimal("2495.20")
        assert quote["volume"] == 123456
        assert quote["change"] == Decimal("15.30")
        assert quote["average_price"] == Decimal("2505.25")
        assert quote["buy_quantity"] == 50000
        assert quote["sell_quantity"] == 45000
        assert quote["last_quantity"] == 100
        assert quote["last_trade_time"] == 1722345600
        assert quote["lower_circuit_limit"] == Decimal("2250.00")
        assert quote["upper_circuit_limit"] == Decimal("2750.00")
        assert quote["oi"] == 1000000
        assert quote["oi_day_high"] == Decimal("1200000")
        assert quote["oi_day_low"] == Decimal("900000")

    def test_should_compute_change_percent_from_net_change_and_close(self, market_adapter, mock_http_client):
        """B-003: change_percent = net_change / close * 100."""
        mock_http_client.post.return_value = {
            "data": {
                "NSE_EQ": {
                    "1": {
                        "last_price": 2510.50,
                        "net_change": 15.30,
                        "ohlc": {"open": 2495.00, "high": 2520.00, "low": 2490.00, "close": 2495.20},
                    }
                }
            }
        }
        quote = market_adapter.get_quote("RELIANCE", "NSE")
        expected = Decimal("15.30") / Decimal("2495.20") * 100
        assert quote["change_percent"] == expected

    def test_change_percent_zero_close_guard(self, market_adapter, mock_http_client):
        """B-003: When close is 0, change_percent must be 0 (no division by zero)."""
        mock_http_client.post.return_value = {
            "data": {
                "NSE_EQ": {
                    "1": {
                        "last_price": 100.0,
                        "net_change": 5.0,
                        "ohlc": {"open": 95.0, "high": 105.0, "low": 90.0, "close": 0},
                    }
                }
            }
        }
        quote = market_adapter.get_quote("TEST", "NSE")
        assert quote["change_percent"] == Decimal("0")

    def test_should_raise_when_quote_entry_empty(self, market_adapter, mock_http_client):
        mock_http_client.post.return_value = {"data": {"NSE_EQ": {"1": {}}}}
        with pytest.raises(ValueError, match="No quote data"):
            market_adapter.get_quote("RELIANCE", "NSE")

    def test_quote_by_id_raises_when_entry_missing(self, market_adapter, mock_http_client):
        mock_http_client.post.return_value = {"data": {"NSE_EQ": {}}}
        with pytest.raises(ValueError, match="No quote data"):
            market_adapter.get_quote_by_id(1, "NSE_EQ", symbol="RELIANCE")

    def test_depth_by_id_raises_when_entry_missing(self, market_adapter, mock_http_client):
        mock_http_client.post.return_value = {"data": {"NSE_EQ": {}}}
        with pytest.raises(ValueError, match="No depth data"):
            market_adapter.get_depth_by_id(1, "NSE_EQ", symbol="RELIANCE")

    # --- get_depth ---

    def test_should_return_bids_and_asks_with_decimal_prices(self, market_adapter, mock_http_client):
        mock_http_client.post.return_value = {
            "data": {
                "NSE_EQ": {
                    "1": {
                        "depth": {
                            "buy": [
                                {"price": 2510.00, "quantity": 100, "orders": 5},
                                {"price": 2509.50, "quantity": 200, "orders": 3},
                            ],
                            "sell": [
                                {"price": 2511.00, "quantity": 150, "orders": 4},
                            ],
                        }
                    }
                }
            }
        }
        depth = market_adapter.get_depth("RELIANCE", "NSE")
        assert depth["symbol"] == "RELIANCE"
        assert len(depth["bids"]) == 2
        assert depth["bids"][0]["price"] == Decimal("2510.00")
        assert depth["bids"][0]["quantity"] == 100
        assert len(depth["asks"]) == 1
        assert depth["asks"][0]["price"] == Decimal("2511.00")

    def test_should_limit_depth_to_five_levels(self, market_adapter, mock_http_client):
        buy_levels = [{"price": 2500 + i, "quantity": 10, "orders": 1} for i in range(10)]
        sell_levels = [{"price": 2510 + i, "quantity": 10, "orders": 1} for i in range(10)]
        mock_http_client.post.return_value = {
            "data": {"NSE_EQ": {"1": {"depth": {"buy": buy_levels, "sell": sell_levels}}}}
        }
        depth = market_adapter.get_depth("RELIANCE", "NSE")
        assert len(depth["bids"]) == 5
        assert len(depth["asks"]) == 5

    # --- get_batch_ltp ---

    def test_should_return_ltp_for_multiple_symbols(self, market_adapter, mock_http_client, mock_resolver):
        inst_tcs = MagicMock()
        inst_tcs.symbol = "TCS"
        inst_tcs.exchange = Exchange.NSE
        inst_tcs.security_id = "2"
        mock_resolver.resolve.side_effect = lambda sym, exch: {
            "RELIANCE": MagicMock(symbol="RELIANCE", exchange=Exchange.NSE, security_id="1"),
            "TCS": inst_tcs,
        }[sym]
        mock_http_client.post.return_value = {
            "data": {
                "NSE_EQ": {
                    "1": {"last_price": 2510},
                    "2": {"last_price": 3600},
                }
            }
        }
        result = market_adapter.get_batch_ltp(["RELIANCE", "TCS"], "NSE")
        assert result == {"RELIANCE": Decimal("2510"), "TCS": Decimal("3600")}

    def test_should_skip_unresolvable_symbols_in_batch(self, market_adapter, mock_http_client, mock_resolver):
        mock_resolver.resolve.side_effect = InstrumentNotFoundError("not found")
        result = market_adapter.get_batch_ltp(["RELIANCE"], "NSE")
        assert result == {}
        mock_http_client.post.assert_not_called()

    def test_should_return_empty_dict_when_no_symbols_resolve(self, market_adapter, mock_http_client, mock_resolver):
        mock_resolver.resolve.side_effect = InstrumentNotFoundError("not found")
        result = market_adapter.get_batch_ltp(["UNKNOWN"], "NSE")
        assert result == {}

    # --- get_batch_quote ---

    def test_should_return_quotes_for_multiple_symbols(self, market_adapter, mock_http_client, mock_resolver):
        inst_tcs = MagicMock()
        inst_tcs.symbol = "TCS"
        inst_tcs.exchange = Exchange.NSE
        inst_tcs.security_id = "2"
        mock_resolver.resolve.side_effect = lambda sym, exch: {
            "RELIANCE": MagicMock(symbol="RELIANCE", exchange=Exchange.NSE, security_id="1"),
            "TCS": inst_tcs,
        }[sym]
        mock_http_client.post.return_value = {
            "data": {
                "NSE_EQ": {
                    "1": {"last_price": 2510, "volume": 1000, "ohlc": {"open": 2500, "high": 2520, "low": 2490, "close": 2500}},
                    "2": {"last_price": 3600, "volume": 2000, "ohlc": {"open": 3590, "high": 3610, "low": 3580, "close": 3590}},
                }
            }
        }
        result = market_adapter.get_batch_quote(["RELIANCE", "TCS"], "NSE")
        assert "RELIANCE" in result
        assert "TCS" in result
        assert result["RELIANCE"]["ltp"] == Decimal("2510")
        assert result["TCS"]["volume"] == 2000

    def test_should_make_correct_api_call_with_segment_for_market_data(self, market_adapter, mock_http_client):
        mock_http_client.post.return_value = {"data": {"NSE_EQ": {"1": {"last_price": 100}}}}
        market_adapter.get_ltp("RELIANCE", "NSE")
        args, kwargs = mock_http_client.post.call_args
        assert args[0] == "/marketfeed/ltp"
        assert "NSE_EQ" in kwargs["json"]


# ===================================================================
# TestOrdersAdapter
# ===================================================================

class TestOrdersAdapter:
    """Tests for OrdersAdapter covering place, modify, cancel,
    orderbook, tradebook, idempotency, and validation."""

    # --- place_order happy path ---

    def test_should_place_order_and_return_fill(self, orders_adapter, mock_http_client):
        mock_http_client.post.return_value = {
            "orderId": "dhan_ord_1",
            "orderStatus": "FILLED",
            "tradedQuantity": 10,
            "tradedPrice": 2500.00,
        }
        order = make_order()
        fill = orders_adapter.place_order(order)
        assert isinstance(fill, Fill)
        assert fill.order_id == "dhan_ord_1"
        assert fill.quantity == 10
        assert fill.price == Decimal("2500.00")
        assert fill.symbol == "RELIANCE"

    def test_should_send_correct_payload_to_api(self, orders_adapter, mock_http_client):
        mock_http_client.post.return_value = {
            "orderId": "dhan_ord_1",
            "orderStatus": "FILLED",
            "tradedQuantity": 10,
            "tradedPrice": 2500.00,
        }
        order = make_order(order_id="ord_5", quantity=50, price=Decimal("2600.00"))
        orders_adapter.place_order(order)
        args, kwargs = mock_http_client.post.call_args
        assert args[0] == "/orders"
        payload = kwargs["json"]
        assert payload["quantity"] == 50
        assert payload["price"] == "2600.00"  # Fixed: now string, not float
        assert payload["dhanClientId"] == "test_client_123"

    def test_should_use_order_price_when_no_traded_price_in_response(self, orders_adapter, mock_http_client):
        mock_http_client.post.return_value = {
            "orderId": "dhan_ord_1",
            "orderStatus": "OPEN",
            "tradedQuantity": 0,
            "tradedPrice": 0,
        }
        order = make_order(price=Decimal("2550.00"))
        fill = orders_adapter.place_order(order)
        assert fill.price == Decimal("2550.00")
        assert fill.quantity == 10

    # --- idempotency ---

    def test_should_block_duplicate_order_by_correlation_id(self, orders_adapter, mock_http_client):
        order1 = make_order(correlation_id="corr_1")
        mock_http_client.post.return_value = {
            "orderId": "dhan_1", "orderStatus": "FILLED",
            "tradedQuantity": 10, "tradedPrice": 2500,
        }
        orders_adapter.place_order(order1)

        order2 = make_order(order_id="ord_2", correlation_id="corr_1")
        with pytest.raises(OrderError, match="Duplicate order blocked"):
            orders_adapter.place_order(order2)
        mock_http_client.post.assert_called_once()

    def test_should_allow_new_order_with_different_correlation_id(self, orders_adapter, mock_http_client):
        mock_http_client.post.return_value = {
            "orderId": "dhan_1", "orderStatus": "FILLED",
            "tradedQuantity": 10, "tradedPrice": 2500,
        }
        order1 = make_order(correlation_id="corr_A")
        order2 = make_order(order_id="ord_2", correlation_id="corr_B")
        fill1 = orders_adapter.place_order(order1)
        fill2 = orders_adapter.place_order(order2)
        assert fill1.order_id == "dhan_1"
        assert fill2.order_id == "dhan_1"
        assert mock_http_client.post.call_count == 2

    def test_should_not_add_to_idempotency_cache_on_api_failure(self, orders_adapter, mock_http_client):
        mock_http_client.post.side_effect = Exception("network timeout")
        order = make_order(correlation_id="corr_fail")
        with pytest.raises(OrderError):
            orders_adapter.place_order(order)

        # Retry should be allowed
        mock_http_client.post.side_effect = None
        mock_http_client.post.return_value = {
            "orderId": "dhan_retry", "orderStatus": "FILLED",
            "tradedQuantity": 10, "tradedPrice": 2500,
        }
        fill = orders_adapter.place_order(order)
        assert fill.order_id == "dhan_retry"

    def test_should_use_order_id_as_correlation_id_fallback(self, orders_adapter, mock_http_client):
        mock_http_client.post.return_value = {
            "orderId": "dhan_1", "orderStatus": "FILLED",
            "tradedQuantity": 10, "tradedPrice": 2500,
        }
        order = make_order(correlation_id=None, order_id="unique_ord")
        orders_adapter.place_order(order)

        duplicate = make_order(correlation_id=None, order_id="unique_ord")
        with pytest.raises(OrderError, match="Duplicate order blocked"):
            orders_adapter.place_order(duplicate)

    def test_should_raise_order_error_when_response_is_rejected(self, orders_adapter, mock_http_client):
        mock_http_client.post.return_value = {
            "orderId": "dhan_rej",
            "orderStatus": "REJECTED",
            "errorMessage": "Insufficient margin",
        }
        order = make_order()
        with pytest.raises(OrderError, match="Order rejected by broker"):
            orders_adapter.place_order(order)

    def test_should_raise_order_error_when_symbol_resolution_fails(self, orders_adapter, mock_resolver):
        mock_resolver.resolve.side_effect = InstrumentNotFoundError("not found")
        order = make_order()
        with pytest.raises(OrderError, match="Cannot resolve security_id"):
            orders_adapter.place_order(order)

    def test_should_raise_order_error_when_mapper_fails_for_unsupported_exchange(self, orders_adapter, mock_http_client, mock_resolver):
        # The DhanMapper returns Result.failure for exchanges other than NSE/MCX
        # Exchange.MCX is supported, so we need to mock an exchange the mapper doesn't handle
        # We use BSE which is in the Exchange enum but not in the mapper's segment map
        inst = MagicMock()
        inst.symbol = "RELIANCE"
        inst.exchange = Exchange.NSE  # Resolver returns NSE
        mock_resolver.resolve.return_value = inst
        # But we create an order with BSE exchange (mapper doesn't support BSE)
        order = make_order(exchange=Exchange.NSE)
        # Patch the mapper to simulate a failure
        from scalpr.brokers.dhan import mapper as mapper_mod
        original = mapper_mod.DhanMapper.order_to_dhan_request
        mapper_mod.DhanMapper.order_to_dhan_request = staticmethod(
            lambda *a, **k: type('R', (), {'is_ok': False, 'error': "Unsupported exchange: BSE", 'value': None})()
        )
        try:
            with pytest.raises(OrderError, match="Order mapping failed"):
                orders_adapter.place_order(order)
        finally:
            mapper_mod.DhanMapper.order_to_dhan_request = original

    # --- validation ---

    def test_should_raise_error_for_zero_quantity(self, orders_adapter):
        order = make_order(quantity=0)
        with pytest.raises(OrderError, match="Invalid quantity"):
            orders_adapter.place_order(order)

    def test_should_not_construct_order_with_negative_quantity(self):
        """Order domain object prevents negative quantity at construction."""
        with pytest.raises(ValueError, match="quantity must be non-negative"):
            make_order(quantity=-5)

    def test_should_not_construct_limit_order_with_zero_price(self):
        """Order domain object prevents LIMIT order with zero price at construction."""
        with pytest.raises(ValueError, match="LIMIT orders must have price"):
            make_order(order_type=OrderType.LIMIT, price=Decimal("0"))

    def test_should_raise_error_for_terminal_state_order(self, orders_adapter):
        order = make_order(state=OrderState.FILLED)
        with pytest.raises(OrderError, match="Cannot place order in terminal state"):
            orders_adapter.place_order(order)

    def test_should_raise_error_for_cancelled_state_order(self, orders_adapter):
        order = make_order(state=OrderState.CANCELLED)
        with pytest.raises(OrderError, match="Cannot place order in terminal state"):
            orders_adapter.place_order(order)

    def test_should_accept_market_order_with_zero_price(self, orders_adapter, mock_http_client):
        mock_http_client.post.return_value = {
            "orderId": "dhan_1", "orderStatus": "FILLED",
            "tradedQuantity": 10, "tradedPrice": 2500,
        }
        order = make_order(order_type=OrderType.MARKET, price=Decimal("0"))
        fill = orders_adapter.place_order(order)
        assert fill is not None

    # --- modify_order ---

    def test_should_modify_order_and_return_true(self, orders_adapter, mock_http_client):
        mock_http_client.put.return_value = {"orderStatus": "MODIFIED"}
        result = orders_adapter.modify_order("dhan_1", Decimal("2600.00"), 20)
        assert result is True
        mock_http_client.put.assert_called_once()
        args, kwargs = mock_http_client.put.call_args
        assert args[0] == "/orders/dhan_1"
        assert kwargs["json"]["price"] == "2600.00"  # Fixed: now string, not float
        assert kwargs["json"]["quantity"] == 20

    def test_should_include_trigger_price_when_provided(self, orders_adapter, mock_http_client):
        mock_http_client.put.return_value = {"orderStatus": "MODIFIED"}
        orders_adapter.modify_order(
            "dhan_1", Decimal("2600.00"), 20, trigger_price=Decimal("2550.00")
        )
        args, kwargs = mock_http_client.put.call_args
        assert kwargs["json"]["triggerPrice"] == "2550.00"  # Fixed: now string, not float

    def test_should_raise_error_when_modify_rejected(self, orders_adapter, mock_http_client):
        mock_http_client.put.return_value = {
            "orderStatus": "REJECTED",
            "errorMessage": "Order not modifiable",
        }
        with pytest.raises(OrderError, match="Modify rejected"):
            orders_adapter.modify_order("dhan_1", Decimal("2600.00"), 20)

    def test_should_raise_error_for_invalid_modify_quantity(self, orders_adapter):
        with pytest.raises(OrderError, match="Invalid quantity"):
            orders_adapter.modify_order("dhan_1", Decimal("2600.00"), 0)

    def test_should_raise_error_for_negative_modify_quantity(self, orders_adapter):
        with pytest.raises(OrderError, match="Invalid quantity"):
            orders_adapter.modify_order("dhan_1", Decimal("2600.00"), -5)

    # --- cancel_order ---

    def test_should_cancel_order_and_return_true(self, orders_adapter, mock_http_client):
        mock_http_client.delete.return_value = {"orderStatus": "CANCELLED"}
        result = orders_adapter.cancel_order("dhan_1")
        assert result is True
        mock_http_client.delete.assert_called_once_with("/orders/dhan_1")

    def test_should_raise_error_when_cancel_rejected(self, orders_adapter, mock_http_client):
        mock_http_client.delete.return_value = {
            "orderStatus": "REJECTED",
            "errorMessage": "Order already filled",
        }
        with pytest.raises(OrderError, match="Cancel rejected"):
            orders_adapter.cancel_order("dhan_1")

    # --- get_orderbook ---

    def test_should_return_parsed_orderbook(self, orders_adapter, mock_http_client):
        mock_http_client.get.return_value = [
            {
                "orderId": "dhan_1",
                "tradingSymbol": "RELIANCE",
                "exchangeSegment": "NSE_EQ",
                "transactionType": "BUY",
                "orderType": "LIMIT",
                "quantity": 10,
                "price": 2500.0,
                "triggerPrice": 0,
                "orderStatus": "OPEN",
                "tradedQuantity": 0,
                "tradedPrice": 0,
                "productType": "INTRADAY",
                "validity": "DAY",
                "createTime": "2024-01-15T09:15:00Z",
                "updateTime": "2024-01-15T09:15:00Z",
                "correlationId": "corr_1",
                "remarks": "",
            }
        ]
        orderbook = orders_adapter.get_orderbook()
        assert len(orderbook) == 1
        assert orderbook[0]["order_id"] == "dhan_1"
        assert orderbook[0]["symbol"] == "RELIANCE"
        assert orderbook[0]["price"] == Decimal("2500.0")
        assert orderbook[0]["status"] == "OPEN"

    def test_should_handle_wrapped_orderbook_response(self, orders_adapter, mock_http_client):
        mock_http_client.get.return_value = {
            "data": [
                {"orderId": "dhan_1", "tradingSymbol": "TCS", "quantity": 5, "price": 3600, "orderStatus": "FILLED"}
            ]
        }
        orderbook = orders_adapter.get_orderbook()
        assert len(orderbook) == 1
        assert orderbook[0]["order_id"] == "dhan_1"

    def test_should_raise_order_error_when_orderbook_fetch_fails(self, orders_adapter, mock_http_client):
        mock_http_client.get.side_effect = Exception("API down")
        with pytest.raises(OrderError, match="Orderbook fetch failed"):
            orders_adapter.get_orderbook()

    # --- get_tradebook ---

    def test_should_return_parsed_tradebook(self, orders_adapter, mock_http_client):
        mock_http_client.get.return_value = [
            {
                "tradeId": "trade_1",
                "orderId": "dhan_1",
                "tradingSymbol": "RELIANCE",
                "transactionType": "BUY",
                "quantity": 10,
                "price": 2500.0,
                "tradeDate": "2024-01-15",
                "exchangeSegment": "NSE_EQ",
                "productType": "INTRADAY",
            }
        ]
        tradebook = orders_adapter.get_tradebook()
        assert len(tradebook) == 1
        assert tradebook[0]["trade_id"] == "trade_1"
        assert tradebook[0]["quantity"] == 10
        assert tradebook[0]["price"] == Decimal("2500.0")

    def test_should_raise_order_error_when_tradebook_fetch_fails(self, orders_adapter, mock_http_client):
        mock_http_client.get.side_effect = Exception("API down")
        with pytest.raises(OrderError, match="Tradebook fetch failed"):
            orders_adapter.get_tradebook()

    # --- idempotency cache management ---

    def test_should_clear_idempotency_cache(self, orders_adapter, mock_http_client):
        mock_http_client.post.return_value = {
            "orderId": "dhan_1", "orderStatus": "FILLED",
            "tradedQuantity": 10, "tradedPrice": 2500,
        }
        order = make_order(correlation_id="to_clear")
        orders_adapter.place_order(order)
        assert "to_clear" in orders_adapter._idempotency_cache

        orders_adapter.clear_idempotency_cache()
        assert len(orders_adapter._idempotency_cache) == 0

        mock_http_client.post.return_value = {
            "orderId": "dhan_2", "orderStatus": "FILLED",
            "tradedQuantity": 10, "tradedPrice": 2500,
        }
        fill = orders_adapter.place_order(order)
        assert fill.order_id == "dhan_2"


# ===================================================================
# TestPortfolioAdapter
# ===================================================================

class TestPortfolioAdapter:
    """Tests for PortfolioAdapter covering positions, holdings,
    fund limits, P&L calculations, and empty/error responses."""

    # --- get_positions ---

    def test_should_return_list_of_positions(self, portfolio_adapter, mock_http_client):
        mock_http_client.get.return_value = [
            {
                "symbol": "RELIANCE",
                "exchange": "NSE",
                "quantity": 10,
                "avgPrice": 2500.00,
                "ltp": 2510.00,
                "realizedPnl": 0,
            }
        ]
        positions = portfolio_adapter.get_positions()
        assert len(positions) == 1
        assert isinstance(positions[0], Position)
        assert positions[0].symbol == "RELIANCE"
        assert positions[0].quantity == 10
        assert positions[0].exchange == Exchange.NSE

    def test_should_filter_out_flat_positions(self, portfolio_adapter, mock_http_client):
        mock_http_client.get.return_value = [
            {"symbol": "RELIANCE", "exchange": "NSE", "quantity": 10, "avgPrice": 2500, "ltp": 2510, "realizedPnl": 0},
            {"symbol": "TCS", "exchange": "NSE", "quantity": 0, "avgPrice": 3600, "ltp": 3610, "realizedPnl": 0},
        ]
        positions = portfolio_adapter.get_positions()
        assert len(positions) == 1
        assert positions[0].symbol == "RELIANCE"

    def test_should_raise_broker_error_on_api_error(self, portfolio_adapter, mock_http_client):
        # C3 fail-closed: an outage must never fabricate an empty book
        mock_http_client.get.side_effect = Exception("API down")
        with pytest.raises(BrokerError, match="positions"):
            portfolio_adapter.get_positions()

    def test_should_handle_wrapped_position_response(self, portfolio_adapter, mock_http_client):
        mock_http_client.get.return_value = {
            "data": [
                {"symbol": "TCS", "exchange": "NSE", "quantity": 5, "avgPrice": 3600, "ltp": 3620, "realizedPnl": 50},
            ]
        }
        positions = portfolio_adapter.get_positions()
        assert len(positions) == 1
        assert positions[0].symbol == "TCS"

    def test_should_map_short_position_correctly(self, portfolio_adapter, mock_http_client):
        mock_http_client.get.return_value = [
            {"symbol": "INFY", "exchange": "NSE", "quantity": -20, "avgPrice": 1500, "ltp": 1480, "realizedPnl": 0},
        ]
        positions = portfolio_adapter.get_positions()
        assert positions[0].position_side == PositionSide.SHORT
        assert positions[0].state == PositionState.OPEN

    # --- get_holdings ---

    def test_should_return_holdings_as_positions(self, portfolio_adapter, mock_http_client):
        mock_http_client.get.return_value = [
            {"symbol": "HDFC", "exchange": "NSE", "quantity": 50, "avgPrice": 1600, "ltp": 1650},
        ]
        holdings = portfolio_adapter.get_holdings()
        assert len(holdings) == 1
        assert holdings[0].symbol == "HDFC"
        assert holdings[0].position_side == PositionSide.LONG
        assert holdings[0].state == PositionState.OPEN
        assert holdings[0].realised_pnl == Decimal("0")

    def test_should_raise_broker_error_on_holdings_error(self, portfolio_adapter, mock_http_client):
        mock_http_client.get.side_effect = Exception("API down")
        with pytest.raises(BrokerError, match="holdings"):
            portfolio_adapter.get_holdings()

    # --- fund_limits ---

    def test_should_return_fund_limits_dict(self, portfolio_adapter, mock_http_client):
        mock_http_client.get.return_value = {
            "availableBalance": 50000,
            "utilizedMargin": 10000,
            "totalBalance": 60000,
            "collateral": 5000,
            "realtime": True,
        }
        limits = portfolio_adapter.get_fund_limits()
        # Dhan v2 endpoint is singular /fundlimit — plural 404s live (found 2026-07-27)
        mock_http_client.get.assert_called_once_with("/fundlimit")
        assert limits["available_margin"] == Decimal("50000")
        assert limits["used_margin"] == Decimal("10000")
        assert limits["total_balance"] == Decimal("60000")
        assert limits["collateral"] == Decimal("5000")
        assert limits["realtime"] is True

    def test_should_raise_broker_error_on_fund_limits_error(self, portfolio_adapter, mock_http_client):
        mock_http_client.get.side_effect = Exception("API down")
        with pytest.raises(BrokerError, match="fund limits"):
            portfolio_adapter.get_fund_limits()

    def test_should_handle_alternate_field_names_in_fund_limits(self, portfolio_adapter, mock_http_client):
        mock_http_client.get.return_value = {
            "availabelMargin": 40000,
            "utilisedMargin": 8000,
            "totalMargin": 48000,
            "collateralAmount": 3000,
        }
        limits = portfolio_adapter.get_fund_limits()
        assert limits["available_margin"] == Decimal("40000")
        assert limits["used_margin"] == Decimal("8000")
        assert limits["total_balance"] == Decimal("48000")
        assert limits["collateral"] == Decimal("3000")

    # --- get_position (single lookup) ---

    def test_should_find_position_by_symbol_and_exchange(self, portfolio_adapter, mock_http_client):
        mock_http_client.get.return_value = [
            {"symbol": "RELIANCE", "exchange": "NSE", "quantity": 10, "avgPrice": 2500, "ltp": 2510, "realizedPnl": 0},
            {"symbol": "TCS", "exchange": "NSE", "quantity": 5, "avgPrice": 3600, "ltp": 3620, "realizedPnl": 0},
        ]
        pos = portfolio_adapter.get_position("RELIANCE", "NSE")
        assert pos is not None
        assert pos.symbol == "RELIANCE"

    def test_should_return_none_for_non_existent_position(self, portfolio_adapter, mock_http_client):
        mock_http_client.get.return_value = [
            {"symbol": "RELIANCE", "exchange": "NSE", "quantity": 10, "avgPrice": 2500, "ltp": 2510, "realizedPnl": 0},
        ]
        pos = portfolio_adapter.get_position("TCS", "NSE")
        assert pos is None

    # --- P&L calculation ---

    def test_should_calculate_unrealised_pnl_for_long_position(self, portfolio_adapter):
        pnl = portfolio_adapter._calculate_unrealised_pnl(10, Decimal("2500"), Decimal("2510"))
        assert pnl == Decimal("100")

    def test_should_calculate_unrealised_pnl_for_short_position(self, portfolio_adapter):
        pnl = portfolio_adapter._calculate_unrealised_pnl(-20, Decimal("1500"), Decimal("1480"))
        assert pnl == Decimal("400")

    def test_should_return_zero_pnl_for_flat_position(self, portfolio_adapter):
        pnl = portfolio_adapter._calculate_unrealised_pnl(0, Decimal("2500"), Decimal("2510"))
        assert pnl == Decimal("0")

    def test_should_calculate_negative_pnl_when_long_is_loss(self, portfolio_adapter):
        pnl = portfolio_adapter._calculate_unrealised_pnl(10, Decimal("2500"), Decimal("2490"))
        assert pnl == Decimal("-100")

    def test_should_calculate_negative_pnl_when_short_is_loss(self, portfolio_adapter):
        pnl = portfolio_adapter._calculate_unrealised_pnl(-20, Decimal("1500"), Decimal("1520"))
        assert pnl == Decimal("-400")

    # --- derive side and state ---

    def test_should_derive_long_for_positive_quantity(self, portfolio_adapter):
        side, state = portfolio_adapter._derive_side_and_state(10)
        assert side == PositionSide.LONG
        assert state == PositionState.OPEN

    def test_should_derive_short_for_negative_quantity(self, portfolio_adapter):
        side, state = portfolio_adapter._derive_side_and_state(-15)
        assert side == PositionSide.SHORT
        assert state == PositionState.OPEN

    def test_should_derive_flat_for_zero_quantity(self, portfolio_adapter):
        side, state = portfolio_adapter._derive_side_and_state(0)
        assert side == PositionSide.FLAT
        assert state == PositionState.FLAT

    # --- _extract_list ---

    def test_should_extract_list_from_direct_list_response(self, portfolio_adapter):
        data = [{"symbol": "A"}, {"symbol": "B"}]
        result = portfolio_adapter._extract_list(data)
        assert len(result) == 2

    def test_should_extract_list_from_data_key(self, portfolio_adapter):
        data = {"data": [{"symbol": "A"}]}
        result = portfolio_adapter._extract_list(data)
        assert len(result) == 1

    def test_should_extract_list_from_positions_key(self, portfolio_adapter):
        data = {"positions": [{"symbol": "A"}, {"symbol": "B"}]}
        result = portfolio_adapter._extract_list(data)
        assert len(result) == 2

    def test_should_return_empty_list_for_unexpected_structure(self, portfolio_adapter):
        data = {"status": "error", "message": "not found"}
        result = portfolio_adapter._extract_list(data)
        assert result == []

    def test_should_return_empty_list_for_non_dict_non_list(self, portfolio_adapter):
        result = portfolio_adapter._extract_list("not a dict")
        assert result == []

    # --- normalise exchange ---

    def test_should_normalise_known_exchange(self, portfolio_adapter):
        exch = portfolio_adapter._normalise_exchange("NSE")
        assert exch == Exchange.NSE

    def test_should_normalise_mcx_exchange(self, portfolio_adapter):
        exch = portfolio_adapter._normalise_exchange("MCX")
        assert exch == Exchange.MCX

    def test_should_default_to_nse_for_unknown_exchange(self, portfolio_adapter):
        exch = portfolio_adapter._normalise_exchange("UNKNOWN")
        assert exch == Exchange.NSE

    # --- _is_open ---

    def test_should_return_true_for_non_zero_quantity(self, portfolio_adapter):
        assert portfolio_adapter._is_open({"quantity": 10}) is True
        assert portfolio_adapter._is_open({"quantity": -5}) is True

    def test_should_return_false_for_zero_quantity(self, portfolio_adapter):
        assert portfolio_adapter._is_open({"quantity": 0}) is False

    def test_should_handle_non_numeric_quantity_gracefully(self, portfolio_adapter):
        assert portfolio_adapter._is_open({"quantity": "invalid"}) is False


# ===================================================================
# TestHistoricalDataAdapter
# ===================================================================

class TestHistoricalDataAdapter:
    """Tests for HistoricalDataAdapter covering OHLCV fetching,
    timeframe validation, date handling, response parsing, and
    lookback estimation."""

    # --- get_ohlcv (wire contract verified live against Dhan v2, 2026-07-27) ---

    def test_should_fetch_ohlcv_and_parse_column_array_response(self, historical_adapter, mock_http_client):
        mock_http_client.post.return_value = {
            "open": [2456.50, 2458.75],
            "high": [2460.00, 2462.00],
            "low": [2455.00, 2457.00],
            "close": [2458.75, 2460.50],
            "volume": [12345, 6789],
            "timestamp": [1705292700.0, 1705293000.0],
        }
        candles = historical_adapter.get_ohlcv(
            symbol="RELIANCE",
            exchange="NSE",
            timeframe="5m",
            from_date=date(2024, 1, 15),
            to_date=date(2024, 1, 15),
        )
        assert len(candles) == 2
        assert candles[0]["open"] == Decimal("2456.5")
        assert candles[0]["high"] == Decimal("2460.0")
        assert candles[0]["low"] == Decimal("2455.0")
        assert candles[0]["close"] == Decimal("2458.75")
        assert candles[0]["volume"] == 12345
        assert candles[0]["timestamp"] == datetime.fromtimestamp(1705292700, tz=timezone.utc)

    def test_should_post_intraday_with_interval_and_instrument(self, historical_adapter, mock_http_client):
        mock_http_client.post.return_value = {}
        historical_adapter.get_ohlcv(
            symbol="RELIANCE",
            exchange="NSE",
            timeframe="15m",
            from_date=date(2024, 1, 15),
            to_date=date(2024, 1, 15),
        )
        args, kwargs = mock_http_client.post.call_args
        assert args[0] == "/charts/intraday"
        body = kwargs["json"]
        assert body["interval"] == "15"
        assert body["instrument"] == "EQUITY"
        assert body["securityId"] == 1
        assert body["exchangeSegment"] == "NSE_EQ"
        assert body["fromDate"] == "2024-01-15"
        assert body["toDate"] == "2024-01-15"
        assert "timeFrame" not in body

    def test_should_post_daily_historical_with_expiry_code(self, historical_adapter, mock_http_client):
        mock_http_client.post.return_value = {}
        historical_adapter.get_ohlcv(
            symbol="RELIANCE",
            exchange="NSE",
            timeframe="1D",
            from_date=date(2024, 1, 1),
            to_date=date(2024, 1, 31),
        )
        args, kwargs = mock_http_client.post.call_args
        assert args[0] == "/charts/historical"
        body = kwargs["json"]
        assert body["expiryCode"] == 0
        assert body["instrument"] == "EQUITY"
        assert "interval" not in body

    def test_should_use_resolver_instrument_kind_in_body(self, historical_adapter, mock_http_client, mock_resolver):
        mock_resolver.instrument_kind_of.return_value = "INDEX"
        mock_http_client.post.return_value = {}
        historical_adapter.get_ohlcv(
            symbol="NIFTY",
            exchange="NSE",
            timeframe="1D",
            from_date=date(2024, 1, 1),
            to_date=date(2024, 1, 31),
        )
        _, kwargs = mock_http_client.post.call_args
        assert kwargs["json"]["instrument"] == "INDEX"

    # --- timeframe validation ---

    def test_should_validate_supported_timeframe(self, historical_adapter):
        # Only intervals Dhan v2 actually serves: 1/3/5/15/25/60 minute + daily
        for tf in ["1m", "3m", "5m", "15m", "25m", "60m", "1H", "1D"]:
            assert historical_adapter.validate_timeframe(tf) is True, f"{tf} should be valid"

    def test_should_reject_unsupported_timeframe(self, historical_adapter):
        # Dhan v2 has no 2/10/30/120/240-minute intervals and no weekly/monthly endpoint
        for tf in ["2m", "7m", "10m", "30m", "2H", "4H", "8H", "1W", "1M", "abc"]:
            assert historical_adapter.validate_timeframe(tf) is False, f"{tf} should be invalid"

    def test_should_raise_value_error_for_invalid_timeframe_in_get_ohlcv(self, historical_adapter):
        with pytest.raises(ValueError, match="Invalid timeframe"):
            historical_adapter.get_ohlcv(
                symbol="RELIANCE",
                exchange="NSE",
                timeframe="7m",
                from_date=date(2024, 1, 15),
                to_date=date(2024, 1, 15),
            )

    def test_should_raise_value_error_for_empty_symbol(self, historical_adapter):
        with pytest.raises(ValueError, match="symbol must not be empty"):
            historical_adapter.get_ohlcv(
                symbol="",
                exchange="NSE",
                timeframe="5m",
                from_date=date(2024, 1, 15),
                to_date=date(2024, 1, 15),
            )

    def test_should_raise_value_error_for_whitespace_symbol(self, historical_adapter):
        with pytest.raises(ValueError, match="symbol must not be empty"):
            historical_adapter.get_ohlcv(
                symbol="   ",
                exchange="NSE",
                timeframe="5m",
                from_date=date(2024, 1, 15),
                to_date=date(2024, 1, 15),
            )

    def test_should_raise_value_error_for_empty_exchange(self, historical_adapter):
        with pytest.raises(ValueError, match="exchange must not be empty"):
            historical_adapter.get_ohlcv(
                symbol="RELIANCE",
                exchange="",
                timeframe="5m",
                from_date=date(2024, 1, 15),
                to_date=date(2024, 1, 15),
            )

    def test_should_raise_value_error_when_from_date_after_to_date(self, historical_adapter):
        with pytest.raises(ValueError, match="from_date.*must be.*<= to_date"):
            historical_adapter.get_ohlcv(
                symbol="RELIANCE",
                exchange="NSE",
                timeframe="5m",
                from_date=date(2024, 2, 1),
                to_date=date(2024, 1, 1),
            )

    def test_should_raise_value_error_when_to_date_in_future(self, historical_adapter):
        future = date.today() + timedelta(days=1)
        with pytest.raises(ValueError, match="cannot be in the future"):
            historical_adapter.get_ohlcv(
                symbol="RELIANCE",
                exchange="NSE",
                timeframe="5m",
                from_date=date(2024, 1, 1),
                to_date=future,
            )

    # --- get_ohlcv_latest ---

    def test_should_fetch_latest_candles(self, historical_adapter, mock_http_client):
        candles = [
            {"timestamp": datetime(2024, 1, 15, 9, 15, tzinfo=timezone.utc), "open": Decimal("2500"), "high": Decimal("2510"), "low": Decimal("2495"), "close": Decimal("2505"), "volume": 100}
            for _ in range(20)
        ]
        with patch.object(historical_adapter, "get_ohlcv", return_value=candles):
            result = historical_adapter.get_ohlcv_latest("RELIANCE", "NSE", "5m", count=5)
        assert len(result) == 5

    def test_should_return_all_candles_when_fewer_than_requested(self, historical_adapter, mock_http_client):
        candles = [
            {"timestamp": datetime(2024, 1, 15, 9, 15, tzinfo=timezone.utc), "open": Decimal("2500"), "high": Decimal("2510"), "low": Decimal("2495"), "close": Decimal("2505"), "volume": 100}
            for _ in range(3)
        ]
        with patch.object(historical_adapter, "get_ohlcv", return_value=candles):
            result = historical_adapter.get_ohlcv_latest("RELIANCE", "NSE", "5m", count=10)
        assert len(result) == 3

    def test_should_raise_error_for_zero_count_in_ohlcv_latest(self, historical_adapter):
        with pytest.raises(ValueError, match="count must be positive"):
            historical_adapter.get_ohlcv_latest("RELIANCE", "NSE", "5m", count=0)

    def test_should_raise_error_for_negative_count_in_ohlcv_latest(self, historical_adapter):
        with pytest.raises(ValueError, match="count must be positive"):
            historical_adapter.get_ohlcv_latest("RELIANCE", "NSE", "5m", count=-5)

    # --- _parse_candles (Dhan v2 column-array format) ---

    def test_should_return_empty_list_for_empty_response(self, historical_adapter):
        assert historical_adapter._parse_candles({"open": [], "timestamp": []}) == []

    def test_should_return_empty_list_for_missing_data_keys(self, historical_adapter):
        assert historical_adapter._parse_candles({}) == []

    def test_should_parse_columns_with_decimal_types(self, historical_adapter):
        response = {
            "open": [2500.0],
            "high": [2510.0],
            "low": [2495.0],
            "close": [2505.0],
            "volume": [100.0],
            "timestamp": [1705292700.0],
        }
        candles = historical_adapter._parse_candles(response)
        assert len(candles) == 1
        assert isinstance(candles[0]["open"], Decimal)
        assert isinstance(candles[0]["high"], Decimal)
        assert isinstance(candles[0]["low"], Decimal)
        assert isinstance(candles[0]["close"], Decimal)
        assert isinstance(candles[0]["volume"], int)
        assert candles[0]["timestamp"].tzinfo == timezone.utc

    def test_should_truncate_to_shortest_column_on_length_mismatch(self, historical_adapter):
        response = {
            "open": [2500.0, 2505.0, 2510.0],
            "high": [2510.0, 2515.0],
            "low": [2495.0, 2500.0],
            "close": [2505.0, 2510.0],
            "volume": [100.0, 120.0],
            "timestamp": [1705292700.0, 1705293000.0],
        }
        candles = historical_adapter._parse_candles(response)
        assert len(candles) == 2

    # --- _estimate_lookback_days ---

    def test_should_estimate_lookback_for_minute_timeframe(self, historical_adapter):
        days = historical_adapter._estimate_lookback_days("5m", 50)
        assert days >= 1
        assert days <= 365

    def test_should_estimate_larger_lookback_for_daily_timeframe(self, historical_adapter):
        days = historical_adapter._estimate_lookback_days("1D", 30)
        assert days >= 30

    def test_should_cap_lookback_at_365_days(self, historical_adapter):
        days = historical_adapter._estimate_lookback_days("1m", 100000)
        assert days <= 365

    def test_should_return_minimum_1_day(self, historical_adapter):
        days = historical_adapter._estimate_lookback_days("1m", 1)
        assert days >= 1

    # --- _timeframe_to_minutes ---

    def test_should_convert_minute_timeframes_to_minutes(self, historical_adapter):
        assert historical_adapter._timeframe_to_minutes("1m") == 1
        assert historical_adapter._timeframe_to_minutes("15m") == 15
        assert historical_adapter._timeframe_to_minutes("25m") == 25
        assert historical_adapter._timeframe_to_minutes("60m") == 60
        assert historical_adapter._timeframe_to_minutes("1H") == 60

    def test_should_return_none_for_daily_timeframe(self, historical_adapter):
        assert historical_adapter._timeframe_to_minutes("1D") is None

    # --- resolve segment integration ---

    def test_should_resolve_segment_via_resolver(self, historical_adapter, mock_resolver):
        historical_adapter._resolve_segment("RELIANCE", "NSE")
        mock_resolver.resolve.assert_called_once_with("RELIANCE", "NSE")

    def test_should_raise_instrument_not_found_when_resolver_fails(self, historical_adapter, mock_resolver):
        mock_resolver.resolve.side_effect = InstrumentNotFoundError("not found")
        with pytest.raises(InstrumentNotFoundError):
            historical_adapter._resolve_segment("UNKNOWN", "NSE")

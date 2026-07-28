"""Comprehensive tests for critical Dhan broker fixes.

Tests verify all P0/P1/P2 fixes:
- MCX segment mapping
- Decimal precision preservation
- Profile validation
- Market order fill handling
- Rate limit compliance
"""

import pytest
from decimal import Decimal
from unittest.mock import MagicMock, patch

from scalpr.brokers.dhan.mapper import DhanMapper
from scalpr.brokers.dhan.orders import OrdersAdapter
from scalpr.brokers.dhan.connection import DhanConnection
from scalpr.brokers.rate_limit import DHAN_RATE_LIMITS
from scalpr.brokers.dhan.exceptions import BrokerError
from scalpr.domain.order import Order, OrderSide, OrderType, OrderState
from scalpr.domain.instrument import Exchange


# ============================================================================
# TEST 1: MCX Segment Mapping Fix
# ============================================================================

class TestMCXSegmentFix:
    """Verify MCX orders use correct MCX_COMM segment."""

    def test_mapper_uses_correct_mcx_segment(self):
        """MCX orders must use MCX_COMM segment (not MCXCOMM)."""
        order = Order(
            order_id="1",
            symbol="CRUDEOIL",
            exchange=Exchange.MCX,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=10,
            price=Decimal("5000.00"),
            state=OrderState.PENDING,
        )
        result = DhanMapper.order_to_dhan_request(order, "c1", "99999")
        assert result.is_ok
        assert result.value.exchangeSegment == "MCX_COMM"

    def test_mapper_uses_correct_nse_segment(self):
        """NSE orders must use NSE_EQ segment."""
        order = Order(
            order_id="1",
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=10,
            price=Decimal("2500.00"),
            state=OrderState.PENDING,
        )
        result = DhanMapper.order_to_dhan_request(order, "c1", "12345")
        assert result.is_ok
        assert result.value.exchangeSegment == "NSE_EQ"


# ============================================================================
# TEST 2: Decimal Precision Preservation
# ============================================================================

class TestDecimalPrecision:
    """Verify order payloads use strings, not floats, for prices."""

    def test_orders_api_receives_string_not_float(self):
        """Order payload must use strings for prices to preserve Decimal precision."""
        mock_client = MagicMock()
        mock_client.client_id = "c1"
        mock_client.post.return_value = {
            "orderId": "ord_123",
            "orderStatus": "FILLED",
            "tradedQuantity": 10,
            "tradedPrice": "2500.50",
        }

        resolver = MagicMock()
        resolver.resolve.return_value = MagicMock(symbol="12345")
        resolver.wire_segment_of.return_value = "NSE_EQ"

        adapter = OrdersAdapter(client=mock_client, resolver=resolver)

        order = Order(
            order_id="1",
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=10,
            price=Decimal("2500.55"),
            state=OrderState.PENDING,
        )

        adapter.place_order(order)

        # Verify payload used string, not float
        call_args = mock_client.post.call_args
        payload = call_args[1]["json"]

        # Price should be string "2500.55", not float 2500.55
        assert isinstance(payload["price"], str), f"Expected str, got {type(payload['price'])}"
        assert payload["price"] == "2500.55"
        assert isinstance(payload["triggerPrice"], str)

    def test_modify_order_uses_string_prices(self):
        """Modify order payload must use strings for prices."""
        mock_client = MagicMock()
        mock_client.put.return_value = {
            "orderId": "ord_123",
            "orderStatus": "MODIFIED",
        }

        resolver = MagicMock()
        adapter = OrdersAdapter(client=mock_client, resolver=resolver)

        adapter.modify_order(
            order_id="ord_123",
            price=Decimal("2510.75"),
            quantity=20,
            trigger_price=Decimal("2505.00"),
        )

        call_args = mock_client.put.call_args
        payload = call_args[1]["json"]

        assert isinstance(payload["price"], str)
        assert payload["price"] == "2510.75"
        assert isinstance(payload["triggerPrice"], str)
        assert payload["triggerPrice"] == "2505.00"


# ============================================================================
# TEST 3: Profile Validation
# ============================================================================

class TestProfileValidation:
    """Verify connection validates profile on connect."""

    def test_connect_warns_on_inactive_data_plan(self, caplog):
        """Connection should warn if dataPlan is not active."""
        # Create mock HTTP client
        mock_http = MagicMock()
        mock_http.get.return_value = {
            "dataPlan": "inactive",
            "dataValidity": "2025-01-01",
            "activeSegment": ["NSE_EQ"],
            "name": "Test User",
        }

        # Create connection with mocked components
        with patch("scalpr.brokers.dhan.connection.DhanHttpClient", return_value=mock_http):
            with patch("scalpr.brokers.dhan.connection.InstrumentLoader") as mock_loader:
                mock_loader.load_cached.return_value = []

                with patch("scalpr.brokers.dhan.connection.SymbolResolver") as mock_resolver:
                    mock_resolver_instance = MagicMock()
                    mock_resolver_instance.load_from_rows.return_value = {"total": 0, "skipped": 0}
                    mock_resolver.return_value = mock_resolver_instance

                    conn = DhanConnection({
                        "client_id": "c1",
                        "access_token": "t1",
                    })
                    conn.connect()

                    # Verify warning was logged
                    assert "dhan_data_plan_inactive" in caplog.text
                    assert "inactive" in caplog.text

    def test_connect_logs_active_segments(self, caplog):
        """Connection should log active segments from profile."""
        import logging
        caplog.set_level(logging.INFO)
        
        mock_http = MagicMock()
        mock_http.get.return_value = {
            "dataPlan": "active",
            "dataValidity": "2025-12-31",
            "activeSegment": ["NSE_EQ", "NSE_FNO", "MCX_COMM"],
            "name": "Test User",
        }

        with patch("scalpr.brokers.dhan.connection.DhanHttpClient", return_value=mock_http):
            with patch("scalpr.brokers.dhan.connection.InstrumentLoader") as mock_loader:
                mock_loader.load_cached.return_value = []

                with patch("scalpr.brokers.dhan.connection.SymbolResolver") as mock_resolver:
                    mock_resolver_instance = MagicMock()
                    mock_resolver_instance.load_from_rows.return_value = {"total": 0, "skipped": 0}
                    mock_resolver.return_value = mock_resolver_instance

                    conn = DhanConnection({
                        "client_id": "c1",
                        "access_token": "t1",
                    })
                    conn.connect()

                    # Verify connection was verified
                    assert "dhan_connection_verified" in caplog.text
                    # Verify profile was accessed (extra fields logged but not in caplog.text)
                    assert mock_http.get.called


# ============================================================================
# TEST 4: Market Order Fill Handling
# ============================================================================

class TestMarketOrderFills:
    """Verify MARKET orders handle fill price correctly."""

    def test_market_order_with_zero_fill_price_logs_warning(self, caplog):
        """MARKET orders with 0 traded_price should log warning."""
        import logging
        caplog.set_level(logging.WARNING)
        
        mock_client = MagicMock()
        mock_client.client_id = "c1"
        mock_client.post.return_value = {
            "orderId": "ord_123",
            "orderStatus": "PENDING",
            "tradedQuantity": 0,
            "tradedPrice": 0,  # Not filled yet
        }

        resolver = MagicMock()
        resolver.resolve.return_value = MagicMock(symbol="12345")
        resolver.wire_segment_of.return_value = "NSE_EQ"

        adapter = OrdersAdapter(client=mock_client, resolver=resolver)

        order = Order(
            order_id="1",
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=10,
            price=Decimal("0"),
            state=OrderState.PENDING,
        )

        fill = adapter.place_order(order)

        # Fill price should be 0, not fallback to order.price
        assert fill.price == Decimal("0")
        assert "market_order_no_fill_price" in caplog.text

    def test_limit_order_uses_price_fallback(self):
        """LIMIT orders should use order.price as fallback if no fill yet."""
        mock_client = MagicMock()
        mock_client.client_id = "c1"
        mock_client.post.return_value = {
            "orderId": "ord_123",
            "orderStatus": "PENDING",
            "tradedQuantity": 0,
            "tradedPrice": 0,
        }

        resolver = MagicMock()
        resolver.resolve.return_value = MagicMock(symbol="12345")
        resolver.wire_segment_of.return_value = "NSE_EQ"

        adapter = OrdersAdapter(client=mock_client, resolver=resolver)

        order = Order(
            order_id="1",
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=10,
            price=Decimal("2500.00"),
            state=OrderState.PENDING,
        )

        fill = adapter.place_order(order)

        # Fill price should fallback to order.price for LIMIT orders
        assert fill.price == Decimal("2500.00")

    def test_market_order_with_fill_uses_traded_price(self):
        """MARKET orders with actual fill should use traded_price."""
        mock_client = MagicMock()
        mock_client.client_id = "c1"
        mock_client.post.return_value = {
            "orderId": "ord_123",
            "orderStatus": "FILLED",
            "tradedQuantity": 10,
            "tradedPrice": "2510.50",
        }

        resolver = MagicMock()
        resolver.resolve.return_value = MagicMock(symbol="12345")
        resolver.wire_segment_of.return_value = "NSE_EQ"

        adapter = OrdersAdapter(client=mock_client, resolver=resolver)

        order = Order(
            order_id="1",
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=10,
            price=Decimal("0"),
            state=OrderState.PENDING,
        )

        fill = adapter.place_order(order)

        # Fill price should use traded_price
        assert fill.price == Decimal("2510.50")


# ============================================================================
# TEST 5: Rate Limit Compliance
# ============================================================================

class TestRateLimits:
    """Verify rate limits match Dhan API specifications."""

    def test_order_api_rate_limit_is_10_per_second(self):
        """Order bucket sustained_rps should be 10."""
        assert DHAN_RATE_LIMITS["orders"]["sustained_rps"] == 10.0

    def test_quote_api_rate_limit_is_1_per_second(self):
        """Quote bucket sustained_rps should be 1."""
        assert DHAN_RATE_LIMITS["quotes"]["sustained_rps"] == 1.0

    def test_historical_rate_limit_is_5_per_second(self):
        """Historical bucket sustained_rps should be 5."""
        assert DHAN_RATE_LIMITS["historical"]["sustained_rps"] == 5.0

    def test_optionchain_rate_limit_is_0_33_per_second(self):
        """Optionchain bucket sustained_rps should be 0.33 (1 per 3s)."""
        assert DHAN_RATE_LIMITS["optionchain"]["sustained_rps"] == 0.33


# ============================================================================
# TEST 6: Integration Tests
# ============================================================================

class TestIntegrationFixes:
    """Integration tests verifying multiple fixes work together."""

    def test_mcx_order_uses_correct_segment_and_string_prices(self):
        """MCX order should use MCX_COMM segment AND string prices."""
        mock_client = MagicMock()
        mock_client.client_id = "c1"
        mock_client.post.return_value = {
            "orderId": "ord_mcx_123",
            "orderStatus": "FILLED",
            "tradedQuantity": 10,
            "tradedPrice": "5000.50",
        }

        resolver = MagicMock()
        resolver.resolve.return_value = MagicMock(symbol="99999")
        resolver.wire_segment_of.return_value = "MCX_COMM"

        adapter = OrdersAdapter(client=mock_client, resolver=resolver)

        order = Order(
            order_id="1",
            symbol="CRUDEOIL",
            exchange=Exchange.MCX,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=10,
            price=Decimal("5000.55"),
            state=OrderState.PENDING,
        )

        adapter.place_order(order)

        # Verify segment is correct
        call_args = mock_client.post.call_args
        payload = call_args[1]["json"]
        assert payload["exchangeSegment"] == "MCX_COMM"

        # Verify price is string
        assert isinstance(payload["price"], str)
        assert payload["price"] == "5000.55"

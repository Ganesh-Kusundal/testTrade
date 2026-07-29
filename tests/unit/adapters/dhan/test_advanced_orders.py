from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from scalpr.adapters.dhan._mapper import (
    InvalidValueError,
    conditional_trigger_to_dhan_request,
    forever_order_to_dhan_request,
    super_order_to_dhan_request,
)

# =========================================================================
# super_order_to_dhan_request — mapper
# =========================================================================

class TestSuperOrderToDhanRequest:
    def test_builds_payload(self):
        result = super_order_to_dhan_request(
            "12345", "NSE_EQ", "BUY", 10, "LIMIT", "INTRADAY", 150.0,
            target_price=200.0, stop_loss_price=140.0, trailing_jump=5.0,
        )
        assert result["securityId"] == "12345"
        assert result["exchangeSegment"] == "NSE_EQ"
        assert result["transactionType"] == "BUY"
        assert result["quantity"] == 10
        assert result["orderType"] == "LIMIT"
        assert result["productType"] == "INTRADAY"
        assert result["price"] == 150.0
        assert result["targetPrice"] == 200.0
        assert result["stopLossPrice"] == 140.0
        assert result["trailingJump"] == 5.0

    def test_defaults_zero_for_optional_legs(self):
        result = super_order_to_dhan_request("12345", "NSE_EQ", "BUY", 10, "LIMIT", "INTRADAY", 150.0)
        assert result["targetPrice"] == 0.0
        assert result["stopLossPrice"] == 0.0
        assert result["trailingJump"] == 0.0

    def test_includes_correlation_id_when_tag_provided(self):
        result = super_order_to_dhan_request(
            "12345", "NSE_EQ", "BUY", 10, "LIMIT", "INTRADAY", 150.0, tag="my-tag",
        )
        assert result["correlationId"] == "my-tag"

    def test_omits_correlation_id_when_tag_none(self):
        result = super_order_to_dhan_request("12345", "NSE_EQ", "BUY", 10, "LIMIT", "INTRADAY", 150.0)
        assert "correlationId" not in result

    def test_invalid_transaction_type_raises(self):
        with pytest.raises(InvalidValueError):
            super_order_to_dhan_request("12345", "NSE_EQ", "HOLD", 10, "LIMIT", "INTRADAY", 150.0)

    def test_invalid_quantity_raises(self):
        with pytest.raises(InvalidValueError):
            super_order_to_dhan_request("12345", "NSE_EQ", "BUY", -1, "LIMIT", "INTRADAY", 150.0)

    def test_zero_quantity_raises(self):
        with pytest.raises(InvalidValueError):
            super_order_to_dhan_request("12345", "NSE_EQ", "BUY", 0, "LIMIT", "INTRADAY", 150.0)

    def test_zero_price_raises(self):
        with pytest.raises(InvalidValueError):
            super_order_to_dhan_request("12345", "NSE_EQ", "BUY", 10, "LIMIT", "INTRADAY", 0)


# =========================================================================
# forever_order_to_dhan_request — mapper
# =========================================================================

class TestForeverOrderToDhanRequest:
    def test_builds_payload(self):
        result = forever_order_to_dhan_request(
            "12345", "NSE_EQ", "BUY", 10, 150.0, 0.0,
            "LIMIT", "INTRADAY", validity="DAY",
            disclosed_quantity=5, symbol="RELIANCE",
        )
        assert result["securityId"] == "12345"
        assert result["exchangeSegment"] == "NSE_EQ"
        assert result["transactionType"] == "BUY"
        assert result["quantity"] == 10
        assert result["price"] == 150.0
        assert result["triggerPrice"] == 0.0
        assert result["orderType"] == "LIMIT"
        assert result["productType"] == "INTRADAY"
        assert result["validity"] == "DAY"
        assert result["orderFlag"] == "SINGLE"
        assert result["disclosedQuantity"] == 5
        assert result["tradingSymbol"] == "RELIANCE"

    def test_defaults(self):
        result = forever_order_to_dhan_request("12345", "NSE_EQ", "BUY", 10, 150.0, 0.0, "LIMIT", "INTRADAY")
        assert result["orderFlag"] == "SINGLE"
        assert result["validity"] == "DAY"
        assert result["disclosedQuantity"] == 0
        assert result["price1"] == 0.0
        assert result["triggerPrice1"] == 0.0
        assert result["quantity1"] == 0
        assert result["tradingSymbol"] == ""

    def test_oco_order_flag(self):
        result = forever_order_to_dhan_request(
            "12345", "NSE_EQ", "BUY", 10, 150.0, 0.0,
            "LIMIT", "INTRADAY", order_flag="OCO",
        )
        assert result["orderFlag"] == "OCO"

    def test_gtd_validity(self):
        result = forever_order_to_dhan_request(
            "12345", "NSE_EQ", "BUY", 10, 150.0, 0.0,
            "LIMIT", "INTRADAY", validity="GTD",
        )
        assert result["validity"] == "GTD"

    def test_includes_correlation_id_when_tag_provided(self):
        result = forever_order_to_dhan_request(
            "12345", "NSE_EQ", "BUY", 10, 150.0, 0.0,
            "LIMIT", "INTRADAY", tag="forever-1",
        )
        assert result["correlationId"] == "forever-1"

    def test_omits_correlation_id_when_tag_none(self):
        result = forever_order_to_dhan_request("12345", "NSE_EQ", "BUY", 10, 150.0, 0.0, "LIMIT", "INTRADAY")
        assert "correlationId" not in result

    def test_invalid_transaction_type_raises(self):
        with pytest.raises(InvalidValueError):
            forever_order_to_dhan_request("12345", "NSE_EQ", "HOLD", 10, 150.0, 0.0, "LIMIT", "INTRADAY")

    def test_invalid_quantity_raises(self):
        with pytest.raises(InvalidValueError):
            forever_order_to_dhan_request("12345", "NSE_EQ", "BUY", 0, 150.0, 0.0, "LIMIT", "INTRADAY")

    def test_invalid_order_flag_raises(self):
        with pytest.raises(InvalidValueError):
            forever_order_to_dhan_request("12345", "NSE_EQ", "BUY", 10, 150.0, 0.0, "LIMIT", "INTRADAY", order_flag="INVALID")

    def test_invalid_validity_raises(self):
        with pytest.raises(InvalidValueError):
            forever_order_to_dhan_request("12345", "NSE_EQ", "BUY", 10, 150.0, 0.0, "LIMIT", "INTRADAY", validity="INVALID")

    def test_oco_with_secondary_legs(self):
        result = forever_order_to_dhan_request(
            "12345", "NSE_EQ", "BUY", 10, 150.0, 145.0,
            "LIMIT", "INTRADAY", order_flag="OCO",
            price1=160.0, trigger_price1=161.0, quantity1=10,
        )
        assert result["price1"] == 160.0
        assert result["triggerPrice1"] == 161.0
        assert result["quantity1"] == 10


# =========================================================================
# conditional_trigger_to_dhan_request — mapper
# =========================================================================

class TestConditionalTriggerToDhanRequest:
    def test_builds_payload(self):
        result = conditional_trigger_to_dhan_request(
            "12345", "NSE_EQ", "BUY", 10, 150.0, 155.0,
            "LIMIT", "INTRADAY",
        )
        assert result["securityId"] == "12345"
        assert result["exchangeSegment"] == "NSE_EQ"
        assert result["transactionType"] == "BUY"
        assert result["quantity"] == 10
        assert result["price"] == 150.0
        assert result["triggerPrice"] == 155.0
        assert result["orderType"] == "LIMIT"
        assert result["productType"] == "INTRADAY"
        assert result["triggerType"] == "PRICE_TRIGGER"
        assert result["validity"] == "DAY"
        assert result["disclosedQuantity"] == 0

    def test_custom_trigger_type(self):
        result = conditional_trigger_to_dhan_request(
            "12345", "NSE_EQ", "BUY", 10, 150.0, 155.0,
            "LIMIT", "INTRADAY", trigger_type="PERCENTAGE_TRIGGER",
        )
        assert result["triggerType"] == "PERCENTAGE_TRIGGER"

    def test_gtd_validity(self):
        result = conditional_trigger_to_dhan_request(
            "12345", "NSE_EQ", "BUY", 10, 150.0, 155.0,
            "LIMIT", "INTRADAY", validity="GTD",
        )
        assert result["validity"] == "GTD"

    def test_gtc_validity(self):
        result = conditional_trigger_to_dhan_request(
            "12345", "NSE_EQ", "BUY", 10, 150.0, 155.0,
            "LIMIT", "INTRADAY", validity="GTC",
        )
        assert result["validity"] == "GTC"

    def test_disclosed_quantity(self):
        result = conditional_trigger_to_dhan_request(
            "12345", "NSE_EQ", "BUY", 10, 150.0, 155.0,
            "LIMIT", "INTRADAY", disclosed_quantity=5,
        )
        assert result["disclosedQuantity"] == 5

    def test_includes_correlation_id_when_tag_provided(self):
        result = conditional_trigger_to_dhan_request(
            "12345", "NSE_EQ", "BUY", 10, 150.0, 155.0,
            "LIMIT", "INTRADAY", tag="trigger-1",
        )
        assert result["correlationId"] == "trigger-1"

    def test_omits_correlation_id_when_tag_none(self):
        result = conditional_trigger_to_dhan_request(
            "12345", "NSE_EQ", "BUY", 10, 150.0, 155.0,
            "LIMIT", "INTRADAY",
        )
        assert "correlationId" not in result

    def test_invalid_transaction_type_raises(self):
        with pytest.raises(InvalidValueError):
            conditional_trigger_to_dhan_request("12345", "NSE_EQ", "HOLD", 10, 150.0, 155.0, "LIMIT", "INTRADAY")

    def test_invalid_quantity_raises(self):
        with pytest.raises(InvalidValueError):
            conditional_trigger_to_dhan_request("12345", "NSE_EQ", "BUY", 0, 150.0, 155.0, "LIMIT", "INTRADAY")

    def test_zero_trigger_price_raises(self):
        with pytest.raises(InvalidValueError):
            conditional_trigger_to_dhan_request("12345", "NSE_EQ", "BUY", 10, 150.0, 0, "LIMIT", "INTRADAY")

    def test_invalid_validity_raises(self):
        with pytest.raises(InvalidValueError):
            conditional_trigger_to_dhan_request("12345", "NSE_EQ", "BUY", 10, 150.0, 155.0, "LIMIT", "INTRADAY", validity="INVALID")


# =========================================================================
# DhanClient — place_super_order delegation
# =========================================================================

class TestDhanClientPlaceSuperOrder:
    @pytest.fixture
    def client(self):
        with (
            patch("scalpr.adapters.dhan.client.TokenManager"),
            patch("scalpr.adapters.dhan.client.DhanHttpClient"),
            patch("scalpr.adapters.dhan.client.RateLimiter"),
            patch("scalpr.adapters.dhan.client.DhanWebSocket"),
            patch("scalpr.adapters.dhan.client.SymbolResolver"),
            patch("scalpr.adapters.dhan.client.super_order_to_dhan_request") as mock_mapper,
        ):
            from scalpr.adapters.dhan.client import DhanClient
            from scalpr.engine.clock import StaticClock
            from scalpr.engine.message_bus import RecordingBus

            bus = RecordingBus()
            clock = StaticClock()
            config = {"client_id": "c1", "access_token": "tok", "totp_secret": "sec"}

            c = DhanClient(bus, clock, config)
            c._rate_limiter = MagicMock()
            c._token_manager = MagicMock()
            c._http_client = MagicMock()
            c._mock_mapper = mock_mapper
            yield c

    def test_calls_mapper(self, client):
        client._mock_mapper.return_value = {"securityId": "12345"}
        client._http_client.post.return_value = {"orderIds": ["SO-1", "SO-2"]}
        client.place_super_order("12345", "NSE_EQ", "BUY", 10, 150.0)
        client._mock_mapper.assert_called_once()

    def test_posts_to_superorders_endpoint(self, client):
        client._mock_mapper.return_value = {"securityId": "12345"}
        client._http_client.post.return_value = {"orderIds": ["SO-1"]}
        client.place_super_order("12345", "NSE_EQ", "BUY", 10, 150.0)
        client._http_client.post.assert_called_once_with(
            "/superorders", data=client._mock_mapper.return_value,
        )

    def test_acquires_rate_limit(self, client):
        client._mock_mapper.return_value = {"securityId": "12345"}
        client._http_client.post.return_value = {"orderIds": ["SO-1"]}
        client.place_super_order("12345", "NSE_EQ", "BUY", 10, 150.0)
        client._rate_limiter.acquire.assert_any_call("orders")

    def test_gets_token(self, client):
        client._mock_mapper.return_value = {"securityId": "12345"}
        client._http_client.post.return_value = {"orderIds": ["SO-1"]}
        client.place_super_order("12345", "NSE_EQ", "BUY", 10, 150.0)
        client._token_manager.get_token.assert_called_once_with()

    def test_returns_order_ids_list(self, client):
        client._mock_mapper.return_value = {"securityId": "12345"}
        client._http_client.post.return_value = {"orderIds": ["SO-1", "SO-2"]}
        result = client.place_super_order("12345", "NSE_EQ", "BUY", 10, 150.0)
        assert result == ["SO-1", "SO-2"]

    def test_falls_back_to_single_order_id(self, client):
        client._mock_mapper.return_value = {"securityId": "12345"}
        client._http_client.post.return_value = {"orderId": "SO-1"}
        result = client.place_super_order("12345", "NSE_EQ", "BUY", 10, 150.0)
        assert result == ["SO-1"]

    def test_empty_response(self, client):
        client._mock_mapper.return_value = {"securityId": "12345"}
        client._http_client.post.return_value = {}
        result = client.place_super_order("12345", "NSE_EQ", "BUY", 10, 150.0)
        assert result == []

    def test_passes_all_kwargs_to_mapper(self, client):
        client._mock_mapper.return_value = {"securityId": "12345"}
        client._http_client.post.return_value = {"orderIds": ["SO-1"]}
        client.place_super_order(
            "12345", "NSE_EQ", "BUY", 10, 150.0,
            order_type="MARKET", product_type="CNC",
            target_price=200.0, stop_loss_price=140.0,
            trailing_jump=5.0, tag="my-so",
        )
        client._mock_mapper.assert_called_once_with(
            "12345", "NSE_EQ", "BUY", 10, "MARKET", "CNC", 150.0,
            target_price=200.0, stop_loss_price=140.0,
            trailing_jump=5.0, tag="my-so",
        )


# =========================================================================
# DhanClient — modify_super_order
# =========================================================================

class TestDhanClientModifySuperOrder:
    @pytest.fixture
    def client(self):
        with (
            patch("scalpr.adapters.dhan.client.TokenManager"),
            patch("scalpr.adapters.dhan.client.DhanHttpClient"),
            patch("scalpr.adapters.dhan.client.RateLimiter"),
            patch("scalpr.adapters.dhan.client.DhanWebSocket"),
            patch("scalpr.adapters.dhan.client.SymbolResolver"),
        ):
            from scalpr.adapters.dhan.client import DhanClient
            from scalpr.engine.clock import StaticClock
            from scalpr.engine.message_bus import RecordingBus

            bus = RecordingBus()
            clock = StaticClock()
            config = {"client_id": "c1", "access_token": "tok", "totp_secret": "sec"}

            c = DhanClient(bus, clock, config)
            c._rate_limiter = MagicMock()
            c._http_client = MagicMock()
            yield c

    def test_puts_to_superorders_endpoint(self, client):
        result = client.modify_super_order("SO-1")
        client._http_client.put.assert_called_once()
        args, _ = client._http_client.put.call_args
        assert args[0] == "/superorders/SO-1"
        assert result is True

    def test_acquires_rate_limit(self, client):
        client.modify_super_order("SO-1")
        client._rate_limiter.acquire.assert_any_call("orders")

    def test_sends_payload(self, client):
        client.modify_super_order(
            "SO-1", quantity=15, price=155.0,
            order_type="LIMIT", leg_name="ENTRY_LEG",
            target_price=200.0, stop_loss_price=140.0, trailing_jump=3.0,
        )
        payload = client._http_client.put.call_args[1]["data"]
        assert payload["orderId"] == "SO-1"
        assert payload["quantity"] == 15
        assert payload["price"] == 155.0
        assert payload["orderType"] == "LIMIT"
        assert payload["legName"] == "ENTRY_LEG"
        assert payload["targetPrice"] == 200.0
        assert payload["stopLossPrice"] == 140.0
        assert payload["trailingJump"] == 3.0

    def test_returns_true(self, client):
        result = client.modify_super_order("SO-1")
        assert result is True


# =========================================================================
# DhanClient — cancel_super_order
# =========================================================================

class TestDhanClientCancelSuperOrder:
    @pytest.fixture
    def client(self):
        with (
            patch("scalpr.adapters.dhan.client.TokenManager"),
            patch("scalpr.adapters.dhan.client.DhanHttpClient"),
            patch("scalpr.adapters.dhan.client.RateLimiter"),
            patch("scalpr.adapters.dhan.client.DhanWebSocket"),
            patch("scalpr.adapters.dhan.client.SymbolResolver"),
        ):
            from scalpr.adapters.dhan.client import DhanClient
            from scalpr.engine.clock import StaticClock
            from scalpr.engine.message_bus import RecordingBus

            bus = RecordingBus()
            clock = StaticClock()
            config = {"client_id": "c1", "access_token": "tok", "totp_secret": "sec"}

            c = DhanClient(bus, clock, config)
            c._rate_limiter = MagicMock()
            c._http_client = MagicMock()
            yield c

    def test_deletes_superorders_endpoint(self, client):
        result = client.cancel_super_order("SO-1")
        client._http_client.delete.assert_called_once_with("/superorders/SO-1")
        assert result is True

    def test_acquires_rate_limit(self, client):
        client.cancel_super_order("SO-1")
        client._rate_limiter.acquire.assert_any_call("orders")


# =========================================================================
# DhanClient — get_super_orders
# =========================================================================

class TestDhanClientGetSuperOrders:
    @pytest.fixture
    def client(self):
        with (
            patch("scalpr.adapters.dhan.client.TokenManager"),
            patch("scalpr.adapters.dhan.client.DhanHttpClient"),
            patch("scalpr.adapters.dhan.client.RateLimiter"),
            patch("scalpr.adapters.dhan.client.DhanWebSocket"),
            patch("scalpr.adapters.dhan.client.SymbolResolver"),
        ):
            from scalpr.adapters.dhan.client import DhanClient
            from scalpr.engine.clock import StaticClock
            from scalpr.engine.message_bus import RecordingBus

            bus = RecordingBus()
            clock = StaticClock()
            config = {"client_id": "c1", "access_token": "tok", "totp_secret": "sec"}

            c = DhanClient(bus, clock, config)
            c._rate_limiter = MagicMock()
            c._http_client = MagicMock()
            yield c

    def test_gets_superorders_endpoint(self, client):
        client._http_client.get.return_value = []
        client.get_super_orders()
        client._http_client.get.assert_called_once_with("/superorders", bucket="orders")

    def test_acquires_rate_limit(self, client):
        client._http_client.get.return_value = []
        client.get_super_orders()
        client._rate_limiter.acquire.assert_any_call("orders")

    def test_returns_list_when_response_is_list(self, client):
        client._http_client.get.return_value = [{"orderId": "SO-1"}]
        result = client.get_super_orders()
        assert result == [{"orderId": "SO-1"}]

    def test_extracts_data_key_when_response_is_dict(self, client):
        client._http_client.get.return_value = {"data": [{"orderId": "SO-1"}]}
        result = client.get_super_orders()
        assert result == [{"orderId": "SO-1"}]

    def test_returns_empty_list_on_empty_dict(self, client):
        client._http_client.get.return_value = {}
        result = client.get_super_orders()
        assert result == []


# =========================================================================
# DhanClient — place_forever_order delegation
# =========================================================================

class TestDhanClientPlaceForeverOrder:
    @pytest.fixture
    def client(self):
        with (
            patch("scalpr.adapters.dhan.client.TokenManager"),
            patch("scalpr.adapters.dhan.client.DhanHttpClient"),
            patch("scalpr.adapters.dhan.client.RateLimiter"),
            patch("scalpr.adapters.dhan.client.DhanWebSocket"),
            patch("scalpr.adapters.dhan.client.SymbolResolver"),
            patch("scalpr.adapters.dhan.client.forever_order_to_dhan_request") as mock_mapper,
        ):
            from scalpr.adapters.dhan.client import DhanClient
            from scalpr.engine.clock import StaticClock
            from scalpr.engine.message_bus import RecordingBus

            bus = RecordingBus()
            clock = StaticClock()
            config = {"client_id": "c1", "access_token": "tok", "totp_secret": "sec"}

            c = DhanClient(bus, clock, config)
            c._rate_limiter = MagicMock()
            c._token_manager = MagicMock()
            c._http_client = MagicMock()
            c._mock_mapper = mock_mapper
            yield c

    def test_calls_mapper(self, client):
        client._mock_mapper.return_value = {"securityId": "12345"}
        client._http_client.post.return_value = {"orderId": "FO-1"}
        client.place_forever_order("12345", "NSE_EQ", "BUY", 10, 150.0, 0.0)
        client._mock_mapper.assert_called_once()

    def test_posts_to_foreverorders_endpoint(self, client):
        client._mock_mapper.return_value = {"securityId": "12345"}
        client._http_client.post.return_value = {"orderId": "FO-1"}
        client.place_forever_order("12345", "NSE_EQ", "BUY", 10, 150.0, 0.0)
        client._http_client.post.assert_called_once_with(
            "/foreverorders", data=client._mock_mapper.return_value,
        )

    def test_acquires_rate_limit(self, client):
        client._mock_mapper.return_value = {"securityId": "12345"}
        client._http_client.post.return_value = {"orderId": "FO-1"}
        client.place_forever_order("12345", "NSE_EQ", "BUY", 10, 150.0, 0.0)
        client._rate_limiter.acquire.assert_any_call("orders")

    def test_gets_token(self, client):
        client._mock_mapper.return_value = {"securityId": "12345"}
        client._http_client.post.return_value = {"orderId": "FO-1"}
        client.place_forever_order("12345", "NSE_EQ", "BUY", 10, 150.0, 0.0)
        client._token_manager.get_token.assert_called_once_with()

    def test_returns_order_id(self, client):
        client._mock_mapper.return_value = {"securityId": "12345"}
        client._http_client.post.return_value = {"orderId": "FO-1"}
        result = client.place_forever_order("12345", "NSE_EQ", "BUY", 10, 150.0, 0.0)
        assert result == "FO-1"

    def test_empty_response_returns_empty_string(self, client):
        client._mock_mapper.return_value = {"securityId": "12345"}
        client._http_client.post.return_value = {}
        result = client.place_forever_order("12345", "NSE_EQ", "BUY", 10, 150.0, 0.0)
        assert result == ""

    def test_passes_all_kwargs_to_mapper(self, client):
        client._mock_mapper.return_value = {"securityId": "12345"}
        client._http_client.post.return_value = {"orderId": "FO-1"}
        client.place_forever_order(
            "12345", "NSE_EQ", "BUY", 10, 150.0, 145.0,
            order_type="LIMIT", product_type="CNC", validity="GTD",
            order_flag="SINGLE", disclosed_quantity=5,
            tag="my-forever", symbol="RELIANCE",
        )
        client._mock_mapper.assert_called_once_with(
            "12345", "NSE_EQ", "BUY", 10, 150.0, 145.0,
            "LIMIT", "CNC",
            validity="GTD", order_flag="SINGLE",
            disclosed_quantity=5,
            price1=0.0, trigger_price1=0.0, quantity1=0,
            tag="my-forever", symbol="RELIANCE",
        )


# =========================================================================
# DhanClient — modify_forever_order
# =========================================================================

class TestDhanClientModifyForeverOrder:
    @pytest.fixture
    def client(self):
        with (
            patch("scalpr.adapters.dhan.client.TokenManager"),
            patch("scalpr.adapters.dhan.client.DhanHttpClient"),
            patch("scalpr.adapters.dhan.client.RateLimiter"),
            patch("scalpr.adapters.dhan.client.DhanWebSocket"),
            patch("scalpr.adapters.dhan.client.SymbolResolver"),
        ):
            from scalpr.adapters.dhan.client import DhanClient
            from scalpr.engine.clock import StaticClock
            from scalpr.engine.message_bus import RecordingBus

            bus = RecordingBus()
            clock = StaticClock()
            config = {"client_id": "c1", "access_token": "tok", "totp_secret": "sec"}

            c = DhanClient(bus, clock, config)
            c._rate_limiter = MagicMock()
            c._http_client = MagicMock()
            yield c

    def test_puts_to_foreverorders_endpoint(self, client):
        result = client.modify_forever_order("FO-1")
        assert result is True
        args, _ = client._http_client.put.call_args
        assert args[0] == "/foreverorders/FO-1"

    def test_acquires_rate_limit(self, client):
        client.modify_forever_order("FO-1")
        client._rate_limiter.acquire.assert_any_call("orders")

    def test_sends_payload(self, client):
        client.modify_forever_order(
            "FO-1", quantity=15, price=155.0,
            trigger_price=150.0, disclosed_quantity=5,
            validity="GTD", order_flag="SINGLE",
        )
        payload = client._http_client.put.call_args[1]["data"]
        assert payload["orderId"] == "FO-1"
        assert payload["quantity"] == 15
        assert payload["price"] == 155.0
        assert payload["triggerPrice"] == 150.0
        assert payload["disclosedQuantity"] == 5
        assert payload["validity"] == "GTD"
        assert payload["orderFlag"] == "SINGLE"

    def test_returns_true(self, client):
        result = client.modify_forever_order("FO-1")
        assert result is True


# =========================================================================
# DhanClient — cancel_forever_order
# =========================================================================

class TestDhanClientCancelForeverOrder:
    @pytest.fixture
    def client(self):
        with (
            patch("scalpr.adapters.dhan.client.TokenManager"),
            patch("scalpr.adapters.dhan.client.DhanHttpClient"),
            patch("scalpr.adapters.dhan.client.RateLimiter"),
            patch("scalpr.adapters.dhan.client.DhanWebSocket"),
            patch("scalpr.adapters.dhan.client.SymbolResolver"),
        ):
            from scalpr.adapters.dhan.client import DhanClient
            from scalpr.engine.clock import StaticClock
            from scalpr.engine.message_bus import RecordingBus

            bus = RecordingBus()
            clock = StaticClock()
            config = {"client_id": "c1", "access_token": "tok", "totp_secret": "sec"}

            c = DhanClient(bus, clock, config)
            c._rate_limiter = MagicMock()
            c._http_client = MagicMock()
            yield c

    def test_deletes_foreverorders_endpoint(self, client):
        result = client.cancel_forever_order("FO-1")
        client._http_client.delete.assert_called_once_with("/foreverorders/FO-1")
        assert result is True

    def test_acquires_rate_limit(self, client):
        client.cancel_forever_order("FO-1")
        client._rate_limiter.acquire.assert_any_call("orders")


# =========================================================================
# DhanClient — get_forever_orders
# =========================================================================

class TestDhanClientGetForeverOrders:
    @pytest.fixture
    def client(self):
        with (
            patch("scalpr.adapters.dhan.client.TokenManager"),
            patch("scalpr.adapters.dhan.client.DhanHttpClient"),
            patch("scalpr.adapters.dhan.client.RateLimiter"),
            patch("scalpr.adapters.dhan.client.DhanWebSocket"),
            patch("scalpr.adapters.dhan.client.SymbolResolver"),
        ):
            from scalpr.adapters.dhan.client import DhanClient
            from scalpr.engine.clock import StaticClock
            from scalpr.engine.message_bus import RecordingBus

            bus = RecordingBus()
            clock = StaticClock()
            config = {"client_id": "c1", "access_token": "tok", "totp_secret": "sec"}

            c = DhanClient(bus, clock, config)
            c._rate_limiter = MagicMock()
            c._http_client = MagicMock()
            yield c

    def test_gets_foreverorders_endpoint(self, client):
        client._http_client.get.return_value = []
        client.get_forever_orders()
        client._http_client.get.assert_called_once_with("/foreverorders", bucket="orders")

    def test_acquires_rate_limit(self, client):
        client._http_client.get.return_value = []
        client.get_forever_orders()
        client._rate_limiter.acquire.assert_any_call("orders")

    def test_returns_list_when_response_is_list(self, client):
        client._http_client.get.return_value = [{"orderId": "FO-1"}]
        result = client.get_forever_orders()
        assert result == [{"orderId": "FO-1"}]

    def test_extracts_data_key_when_response_is_dict(self, client):
        client._http_client.get.return_value = {"data": [{"orderId": "FO-1"}]}
        result = client.get_forever_orders()
        assert result == [{"orderId": "FO-1"}]

    def test_returns_empty_list_on_empty_dict(self, client):
        client._http_client.get.return_value = {}
        result = client.get_forever_orders()
        assert result == []


# =========================================================================
# DhanClient — place_conditional_trigger
# =========================================================================

class TestDhanClientPlaceConditionalTrigger:
    @pytest.fixture
    def client(self):
        with (
            patch("scalpr.adapters.dhan.client.TokenManager"),
            patch("scalpr.adapters.dhan.client.DhanHttpClient"),
            patch("scalpr.adapters.dhan.client.RateLimiter"),
            patch("scalpr.adapters.dhan.client.DhanWebSocket"),
            patch("scalpr.adapters.dhan.client.SymbolResolver"),
            patch("scalpr.adapters.dhan.client.conditional_trigger_to_dhan_request") as mock_mapper,
        ):
            from scalpr.adapters.dhan.client import DhanClient
            from scalpr.engine.clock import StaticClock
            from scalpr.engine.message_bus import RecordingBus

            bus = RecordingBus()
            clock = StaticClock()
            config = {"client_id": "c1", "access_token": "tok", "totp_secret": "sec"}

            c = DhanClient(bus, clock, config)
            c._rate_limiter = MagicMock()
            c._token_manager = MagicMock()
            c._http_client = MagicMock()
            c._mock_mapper = mock_mapper
            yield c

    def test_calls_mapper(self, client):
        client._mock_mapper.return_value = {"securityId": "12345"}
        client._http_client.post.return_value = {"triggerId": "TG-1"}
        client.place_conditional_trigger("12345", "NSE_EQ", "BUY", 10, 150.0, 155.0)
        client._mock_mapper.assert_called_once()

    def test_posts_to_triggers_endpoint(self, client):
        client._mock_mapper.return_value = {"securityId": "12345"}
        client._http_client.post.return_value = {"triggerId": "TG-1"}
        client.place_conditional_trigger("12345", "NSE_EQ", "BUY", 10, 150.0, 155.0)
        client._http_client.post.assert_called_once_with(
            "/triggers", data=client._mock_mapper.return_value,
        )

    def test_acquires_rate_limit(self, client):
        client._mock_mapper.return_value = {"securityId": "12345"}
        client._http_client.post.return_value = {"triggerId": "TG-1"}
        client.place_conditional_trigger("12345", "NSE_EQ", "BUY", 10, 150.0, 155.0)
        client._rate_limiter.acquire.assert_any_call("orders")

    def test_gets_token(self, client):
        client._mock_mapper.return_value = {"securityId": "12345"}
        client._http_client.post.return_value = {"triggerId": "TG-1"}
        client.place_conditional_trigger("12345", "NSE_EQ", "BUY", 10, 150.0, 155.0)
        client._token_manager.get_token.assert_called_once_with()

    def test_returns_trigger_id(self, client):
        client._mock_mapper.return_value = {"securityId": "12345"}
        client._http_client.post.return_value = {"triggerId": "TG-1"}
        result = client.place_conditional_trigger("12345", "NSE_EQ", "BUY", 10, 150.0, 155.0)
        assert result == "TG-1"

    def test_empty_response_returns_empty_string(self, client):
        client._mock_mapper.return_value = {"securityId": "12345"}
        client._http_client.post.return_value = {}
        result = client.place_conditional_trigger("12345", "NSE_EQ", "BUY", 10, 150.0, 155.0)
        assert result == ""

    def test_passes_all_kwargs_to_mapper(self, client):
        client._mock_mapper.return_value = {"securityId": "12345"}
        client._http_client.post.return_value = {"triggerId": "TG-1"}
        client.place_conditional_trigger(
            "12345", "NSE_EQ", "BUY", 10, 150.0, 155.0,
            order_type="MARKET", product_type="CNC",
            trigger_type="PERCENTAGE_TRIGGER", validity="GTD",
            disclosed_quantity=5, tag="my-trigger",
        )
        client._mock_mapper.assert_called_once_with(
            "12345", "NSE_EQ", "BUY", 10, 150.0, 155.0,
            "MARKET", "CNC",
            trigger_type="PERCENTAGE_TRIGGER", validity="GTD",
            disclosed_quantity=5, tag="my-trigger",
        )


# =========================================================================
# DhanClient — delete_conditional_trigger
# =========================================================================

class TestDhanClientDeleteConditionalTrigger:
    @pytest.fixture
    def client(self):
        with (
            patch("scalpr.adapters.dhan.client.TokenManager"),
            patch("scalpr.adapters.dhan.client.DhanHttpClient"),
            patch("scalpr.adapters.dhan.client.RateLimiter"),
            patch("scalpr.adapters.dhan.client.DhanWebSocket"),
            patch("scalpr.adapters.dhan.client.SymbolResolver"),
        ):
            from scalpr.adapters.dhan.client import DhanClient
            from scalpr.engine.clock import StaticClock
            from scalpr.engine.message_bus import RecordingBus

            bus = RecordingBus()
            clock = StaticClock()
            config = {"client_id": "c1", "access_token": "tok", "totp_secret": "sec"}

            c = DhanClient(bus, clock, config)
            c._rate_limiter = MagicMock()
            c._http_client = MagicMock()
            yield c

    def test_deletes_triggers_endpoint(self, client):
        result = client.delete_conditional_trigger("TG-1")
        client._http_client.delete.assert_called_once_with("/triggers/TG-1")
        assert result is True

    def test_acquires_rate_limit(self, client):
        client.delete_conditional_trigger("TG-1")
        client._rate_limiter.acquire.assert_any_call("orders")


# =========================================================================
# DhanClient — get_all_conditional_triggers
# =========================================================================

class TestDhanClientGetAllConditionalTriggers:
    @pytest.fixture
    def client(self):
        with (
            patch("scalpr.adapters.dhan.client.TokenManager"),
            patch("scalpr.adapters.dhan.client.DhanHttpClient"),
            patch("scalpr.adapters.dhan.client.RateLimiter"),
            patch("scalpr.adapters.dhan.client.DhanWebSocket"),
            patch("scalpr.adapters.dhan.client.SymbolResolver"),
        ):
            from scalpr.adapters.dhan.client import DhanClient
            from scalpr.engine.clock import StaticClock
            from scalpr.engine.message_bus import RecordingBus

            bus = RecordingBus()
            clock = StaticClock()
            config = {"client_id": "c1", "access_token": "tok", "totp_secret": "sec"}

            c = DhanClient(bus, clock, config)
            c._rate_limiter = MagicMock()
            c._http_client = MagicMock()
            yield c

    def test_gets_triggers_endpoint(self, client):
        client._http_client.get.return_value = []
        client.get_all_conditional_triggers()
        client._http_client.get.assert_called_once_with("/triggers", bucket="orders")

    def test_acquires_rate_limit(self, client):
        client._http_client.get.return_value = []
        client.get_all_conditional_triggers()
        client._rate_limiter.acquire.assert_any_call("orders")

    def test_returns_list_when_response_is_list(self, client):
        client._http_client.get.return_value = [{"triggerId": "TG-1"}]
        result = client.get_all_conditional_triggers()
        assert result == [{"triggerId": "TG-1"}]

    def test_extracts_data_key_when_response_is_dict(self, client):
        client._http_client.get.return_value = {"data": [{"triggerId": "TG-1"}]}
        result = client.get_all_conditional_triggers()
        assert result == [{"triggerId": "TG-1"}]

    def test_returns_empty_list_on_empty_dict(self, client):
        client._http_client.get.return_value = {}
        result = client.get_all_conditional_triggers()
        assert result == []


# =========================================================================
# DhanClient — get_conditional_trigger_by_id
# =========================================================================

class TestDhanClientGetConditionalTriggerById:
    @pytest.fixture
    def client(self):
        with (
            patch("scalpr.adapters.dhan.client.TokenManager"),
            patch("scalpr.adapters.dhan.client.DhanHttpClient"),
            patch("scalpr.adapters.dhan.client.RateLimiter"),
            patch("scalpr.adapters.dhan.client.DhanWebSocket"),
            patch("scalpr.adapters.dhan.client.SymbolResolver"),
        ):
            from scalpr.adapters.dhan.client import DhanClient
            from scalpr.engine.clock import StaticClock
            from scalpr.engine.message_bus import RecordingBus

            bus = RecordingBus()
            clock = StaticClock()
            config = {"client_id": "c1", "access_token": "tok", "totp_secret": "sec"}

            c = DhanClient(bus, clock, config)
            c._rate_limiter = MagicMock()
            c._http_client = MagicMock()
            yield c

    def test_gets_triggers_by_id_endpoint(self, client):
        client._http_client.get.return_value = {"triggerId": "TG-1"}
        result = client.get_conditional_trigger_by_id("TG-1")
        client._http_client.get.assert_called_once_with("/triggers/TG-1", bucket="orders")
        assert result == {"triggerId": "TG-1"}

    def test_acquires_rate_limit(self, client):
        client._http_client.get.return_value = {"triggerId": "TG-1"}
        client.get_conditional_trigger_by_id("TG-1")
        client._rate_limiter.acquire.assert_any_call("orders")

    def test_returns_empty_dict_on_non_dict_response(self, client):
        client._http_client.get.return_value = []
        result = client.get_conditional_trigger_by_id("TG-1")
        assert result == {}

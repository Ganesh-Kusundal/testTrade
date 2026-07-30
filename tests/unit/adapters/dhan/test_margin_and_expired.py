from __future__ import annotations

from unittest.mock import patch

import pytest

from scalpr.adapters.dhan._mapper_orders import InvalidValueError
from scalpr.adapters.dhan._mapper_portfolio import margin_calc_to_dhan_request

# ============================================================================
# margin_calc_to_dhan_request (mapper)
# ============================================================================

class TestMarginCalcToDhanRequest:
    def test_basic_buy_intraday(self):
        result = margin_calc_to_dhan_request("12345", "NSE_EQ", "BUY", 10, "INTRADAY", 2500.50)
        assert result["securityId"] == "12345"
        assert result["exchangeSegment"] == "NSE_EQ"
        assert result["transactionType"] == "BUY"
        assert result["quantity"] == 10
        assert result["productType"] == "INTRADAY"
        assert result["price"] == 2500.50

    def test_sell_cnc(self):
        result = margin_calc_to_dhan_request("54321", "NSE_FNO", "SELL", 50, "CNC", 150.75)
        assert result["transactionType"] == "SELL"
        assert result["productType"] == "CNC"

    def test_with_trigger_price(self):
        result = margin_calc_to_dhan_request("12345", "NSE_EQ", "BUY", 10, "INTRADAY", 2500.50, trigger_price=2480.0)
        assert result["triggerPrice"] == 2480.0

    def test_zero_trigger_price_omitted(self):
        result = margin_calc_to_dhan_request("12345", "NSE_EQ", "BUY", 10, "INTRADAY", 2500.50, trigger_price=0)
        assert "triggerPrice" not in result

    def test_negative_trigger_price_omitted(self):
        result = margin_calc_to_dhan_request("12345", "NSE_EQ", "BUY", 10, "INTRADAY", 2500.50, trigger_price=-1)
        assert "triggerPrice" not in result

    def test_uppercases_exchange_segment(self):
        result = margin_calc_to_dhan_request("12345", "nse_eq", "BUY", 10, "INTRADAY", 100)
        assert result["exchangeSegment"] == "NSE_EQ"

    def test_uppercases_transaction_type(self):
        result = margin_calc_to_dhan_request("12345", "NSE_EQ", "buy", 10, "INTRADAY", 100)
        assert result["transactionType"] == "BUY"

    def test_uppercases_product_type(self):
        result = margin_calc_to_dhan_request("12345", "NSE_EQ", "BUY", 10, "intraday", 100)
        assert result["productType"] == "INTRADAY"

    def test_converts_quantity_to_int(self):
        result = margin_calc_to_dhan_request("12345", "NSE_EQ", "BUY", 10.7, "INTRADAY", 100)
        assert result["quantity"] == 10
        assert isinstance(result["quantity"], int)

    def test_converts_price_to_float(self):
        result = margin_calc_to_dhan_request("12345", "NSE_EQ", "BUY", 10, "INTRADAY", "2500.50")
        assert result["price"] == 2500.50
        assert isinstance(result["price"], float)

    def test_raises_on_invalid_transaction_type(self):
        with pytest.raises(InvalidValueError, match="BUY or SELL"):
            margin_calc_to_dhan_request("12345", "NSE_EQ", "HOLD", 10, "INTRADAY", 100)

    def test_raises_on_empty_transaction_type(self):
        with pytest.raises(InvalidValueError, match="BUY or SELL"):
            margin_calc_to_dhan_request("12345", "NSE_EQ", "", 10, "INTRADAY", 100)

    def test_mcx_segment(self):
        result = margin_calc_to_dhan_request("99999", "MCX_COMM", "BUY", 1, "INTRADAY", 50000)
        assert result["exchangeSegment"] == "MCX_COMM"

    def test_bse_segment(self):
        result = margin_calc_to_dhan_request("88888", "BSE_EQ", "SELL", 5, "CNC", 2500)
        assert result["exchangeSegment"] == "BSE_EQ"


# ============================================================================
# DhanClient.margin_calculator
# ============================================================================

class TestClientMarginCalculator:
    @pytest.fixture
    def client(self):
        patchers = [
            patch("scalpr.adapters.dhan.client.TokenManager"),
            patch("scalpr.adapters.dhan.client.DhanHttpClient"),
            patch("scalpr.adapters.dhan.client.RateLimiter"),
            patch("scalpr.adapters.dhan.client.DhanWebSocket"),
            patch("scalpr.adapters.dhan.client.SymbolResolver"),
        ]
        mocks = [p.start() for p in patchers]

        from datetime import datetime

        from scalpr.adapters.dhan.client import DhanClient
        from scalpr.engine.clock import StaticClock
        from scalpr.engine.message_bus import RecordingBus
        bus = RecordingBus()
        clock = StaticClock(datetime(2024, 6, 15, 10, 30))
        config = {"client_id": "c1", "access_token": "tok", "totp_secret": "sec"}
        c = DhanClient(bus, clock, config)

        yield c, mocks[1].return_value, mocks[2].return_value

        for p in patchers:
            p.stop()

    def test_posts_to_margincalculator_endpoint(self, client):
        c, http, _limiter = client
        http.post.return_value = {}
        c.margin_calculator("12345", "NSE_EQ", "BUY", 10, "INTRADAY", 2500.50)
        http.post.assert_called_once()
        assert http.post.call_args[0][0] == "/margincalculator"



    def test_sends_required_fields(self, client):
        c, http, _limiter = client
        http.post.return_value = {}
        c.margin_calculator("12345", "NSE_EQ", "SELL", 25, "CNC", 150.75)
        _, kwargs = http.post.call_args
        data = kwargs["data"]
        assert data["securityId"] == "12345"
        assert data["exchangeSegment"] == "NSE_EQ"
        assert data["transactionType"] == "SELL"
        assert data["quantity"] == 25
        assert data["productType"] == "CNC"
        assert data["price"] == 150.75

    def test_sends_trigger_price_when_provided(self, client):
        c, http, _limiter = client
        http.post.return_value = {}
        c.margin_calculator("12345", "NSE_EQ", "BUY", 10, "INTRADAY", 2500.50, trigger_price=2480.0)
        _, kwargs = http.post.call_args
        assert kwargs["data"]["triggerPrice"] == 2480.0

    def test_uses_portfolio_bucket(self, client):
        c, http, _limiter = client
        http.post.return_value = {}
        c.margin_calculator("12345", "NSE_EQ", "BUY", 10, "INTRADAY", 2500.50)
        _, kwargs = http.post.call_args
        assert kwargs["bucket"] == "portfolio"

    def test_returns_response_dict(self, client):
        c, http, _limiter = client
        expected = {"margin": 50000, "status": "success"}
        http.post.return_value = expected
        result = c.margin_calculator("12345", "NSE_EQ", "BUY", 10, "INTRADAY", 2500.50)
        assert result == expected


# ============================================================================
# DhanClient.get_expired_option_data
# ============================================================================

class TestClientExpiredOptionData:
    @pytest.fixture
    def client(self):
        patchers = [
            patch("scalpr.adapters.dhan.client.TokenManager"),
            patch("scalpr.adapters.dhan.client.DhanHttpClient"),
            patch("scalpr.adapters.dhan.client.RateLimiter"),
            patch("scalpr.adapters.dhan.client.DhanWebSocket"),
            patch("scalpr.adapters.dhan.client.SymbolResolver"),
        ]
        mocks = [p.start() for p in patchers]

        from datetime import datetime

        from scalpr.adapters.dhan.client import DhanClient
        from scalpr.engine.clock import StaticClock
        from scalpr.engine.message_bus import RecordingBus
        bus = RecordingBus()
        clock = StaticClock(datetime(2024, 6, 15, 10, 30))
        config = {"client_id": "c1", "access_token": "tok", "totp_secret": "sec"}
        c = DhanClient(bus, clock, config)

        yield c, mocks[1].return_value, mocks[2].return_value

        for p in patchers:
            p.stop()

    def test_acquires_history_bucket(self, client):
        c, http, _limiter = client
        http.post.return_value = {}
        c.get_expired_option_data(
            "12345", "NSE_FNO", "OPTIDX", "WEEK", 0,
            "ATM", "CALL", ["open", "high", "low", "close"],
            "2024-01-01", "2024-01-31",
        )
        # Rate limiting is handled by _http._request, verified in test_http.py

    def test_posts_to_rollingoption_endpoint(self, client):
        c, http, _limiter = client
        http.post.return_value = {}
        c.get_expired_option_data(
            "12345", "NSE_FNO", "OPTIDX", "WEEK", 0,
            "ATM", "CALL", ["open", "high", "low", "close"],
            "2024-01-01", "2024-01-31",
        )
        http.post.assert_called_once()
        args, _kwargs = http.post.call_args
        assert args[0] == "/charts/rollingoption"

    def test_sends_all_required_fields(self, client):
        c, http, _limiter = client
        http.post.return_value = {}
        c.get_expired_option_data(
            "12345", "NSE_FNO", "OPTIDX", "WEEK", 0,
            "ATM", "CALL", ["open", "close", "iv", "volume"],
            "2024-01-01", "2024-01-31",
        )
        _, kwargs = http.post.call_args
        data = kwargs["data"]
        assert data["securityId"] == "12345"
        assert data["exchangeSegment"] == "NSE_FNO"
        assert data["instrument"] == "OPTIDX"
        assert data["expiryFlag"] == "WEEK"
        assert data["expiryCode"] == 0
        assert data["strike"] == "ATM"
        assert data["drvOptionType"] == "CALL"
        assert data["requiredData"] == ["open", "close", "iv", "volume"]
        assert data["fromDate"] == "2024-01-01"
        assert data["toDate"] == "2024-01-31"
        assert data["interval"] == 1

    def test_sends_custom_interval(self, client):
        c, http, _limiter = client
        http.post.return_value = {}
        c.get_expired_option_data(
            "12345", "NSE_FNO", "OPTIDX", "WEEK", 0,
            "ATM", "CALL", ["open", "close"],
            "2024-01-01", "2024-01-31", interval=15,
        )
        _, kwargs = http.post.call_args
        assert kwargs["data"]["interval"] == 15

    def test_sends_expiry_flag_month(self, client):
        c, http, _limiter = client
        http.post.return_value = {}
        c.get_expired_option_data(
            "12345", "NSE_FNO", "OPTIDX", "MONTH", 1,
            "ATM", "PUT", ["open", "close"],
            "2024-01-01", "2024-01-31",
        )
        _, kwargs = http.post.call_args
        assert kwargs["data"]["expiryFlag"] == "MONTH"

    def test_sends_drv_option_type_put(self, client):
        c, http, _limiter = client
        http.post.return_value = {}
        c.get_expired_option_data(
            "12345", "NSE_FNO", "OPTIDX", "WEEK", 0,
            "ATM+1", "PUT", ["open", "high", "low", "close"],
            "2024-01-01", "2024-01-31",
        )
        _, kwargs = http.post.call_args
        assert kwargs["data"]["drvOptionType"] == "PUT"

    def test_uses_history_bucket(self, client):
        c, http, _limiter = client
        http.post.return_value = {}
        c.get_expired_option_data(
            "12345", "NSE_FNO", "OPTIDX", "WEEK", 0,
            "ATM", "CALL", ["open", "close"],
            "2024-01-01", "2024-01-31",
        )
        _, kwargs = http.post.call_args
        assert kwargs["bucket"] == "history"

    def test_with_optstk_instrument(self, client):
        c, http, _limiter = client
        http.post.return_value = {}
        c.get_expired_option_data(
            "12345", "NSE_FNO", "OPTSTK", "WEEK", 2,
            "ATM", "CALL", ["open", "high", "close"],
            "2024-01-01", "2024-01-31",
        )
        _, kwargs = http.post.call_args
        assert kwargs["data"]["instrument"] == "OPTSTK"

    def test_returns_response_dict(self, client):
        c, http, _limiter = client
        expected = {"status": "success", "data": {"timestamp": [], "open": []}}
        http.post.return_value = expected
        result = c.get_expired_option_data(
            "12345", "NSE_FNO", "OPTIDX", "WEEK", 0,
            "ATM", "CALL", ["open", "close"],
            "2024-01-01", "2024-01-31",
        )
        assert result == expected

    def test_default_interval_is_1(self, client):
        c, http, _limiter = client
        http.post.return_value = {}
        c.get_expired_option_data(
            "12345", "NSE_FNO", "OPTIDX", "WEEK", 0,
            "ATM", "CALL", ["open", "close"],
            "2024-01-01", "2024-01-31",
        )
        _, kwargs = http.post.call_args
        assert kwargs["data"]["interval"] == 1

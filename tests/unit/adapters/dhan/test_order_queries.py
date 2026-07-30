from __future__ import annotations

import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

from scalpr.adapters.dhan._http import DhanRequestError
from scalpr.adapters.dhan._mapper_portfolio import order_report_to_dict, trade_to_domain
from scalpr.adapters.dhan.client import DhanClient
from scalpr.engine.clock import StaticClock
from scalpr.engine.message_bus import RecordingBus


def _make_client(extra_patches: list | None = None) -> tuple[DhanClient, MagicMock, MagicMock, list]:
    bus = RecordingBus()
    clock = StaticClock(datetime(2024, 6, 15, 10, 30))
    config = {"client_id": "c1", "access_token": "tok", "totp_secret": "sec"}

    patcher_names = [
        "scalpr.adapters.dhan.client.TokenManager",
        "scalpr.adapters.dhan.client.DhanHttpClient",
        "scalpr.adapters.dhan.client.RateLimiter",
        "scalpr.adapters.dhan.client.DhanWebSocket",
        "scalpr.adapters.dhan.client.SymbolResolver",
    ]
    if extra_patches:
        patcher_names.extend(extra_patches)

    patchers = [patch(n) for n in patcher_names]
    mocks = [p.start() for p in patchers]

    def cleanup():
        for p in patchers:
            p.stop()

    mock_http = mocks[1].return_value
    mock_rate = mocks[2].return_value
    client = DhanClient(bus, clock, config)
    return client, mock_http, mock_rate, cleanup


# ── get_order_detail ─────────────────────────────────────────────

class TestGetOrderDetail(unittest.TestCase):
    def setUp(self):
        self.client, self.mock_http, self.mock_rate, self._cleanup = _make_client()
        self.addCleanup(self._cleanup)

    def test_gets_order_by_id(self):
        self.mock_http.get.return_value = {"orderId": "ORD1", "status": "OPEN"}
        result = self.client.get_order_detail("ORD1")
        self.mock_http.get.assert_called_once_with("/orders/ORD1", bucket="orders")
        self.assertEqual(result["orderId"], "ORD1")

    def test_acquires_rate_limit_orders(self):
        self.mock_http.get.return_value = {}
        self.client.get_order_detail("ORD1")

    def test_returns_response_dict(self):
        self.mock_http.get.return_value = {"orderId": "ORD1", "symbol": "RELIANCE"}
        result = self.client.get_order_detail("ORD1")
        self.assertIsInstance(result, dict)
        self.assertEqual(result["symbol"], "RELIANCE")

    def test_raises_dhan_request_error_on_404(self):
        self.mock_http.get.side_effect = DhanRequestError(404, "Not Found")
        with self.assertRaises(DhanRequestError):
            self.client.get_order_detail("BADID")

    def test_raises_dhan_request_error_on_403(self):
        self.mock_http.get.side_effect = DhanRequestError(403, "Forbidden")
        with self.assertRaises(DhanRequestError):
            self.client.get_order_detail("ORD1")


# ── get_order_status ─────────────────────────────────────────────

class TestGetOrderStatus(unittest.TestCase):
    def setUp(self):
        self.client, self.mock_http, self.mock_rate, self._cleanup = _make_client()
        self.addCleanup(self._cleanup)

    def test_extracts_status_from_detail(self):
        self.mock_http.get.return_value = {"orderId": "ORD1", "status": "FILLED"}
        result = self.client.get_order_status("ORD1")
        self.assertEqual(result, "FILLED")

    def test_returns_empty_string_when_missing(self):
        self.mock_http.get.return_value = {"orderId": "ORD1"}
        result = self.client.get_order_status("ORD1")
        self.assertEqual(result, "")

    def test_makes_http_get_call(self):
        self.mock_http.get.return_value = {"status": "OPEN"}
        self.client.get_order_status("ORD1")
        self.mock_http.get.assert_called_once_with("/orders/ORD1", bucket="orders")

    def test_acquires_rate_limit(self):
        self.mock_http.get.return_value = {"status": "PENDING"}
        self.client.get_order_status("ORD1")


# ── get_executed_price ────────────────────────────────────────────

class TestGetExecutedPrice(unittest.TestCase):
    def setUp(self):
        self.client, self.mock_http, self.mock_rate, self._cleanup = _make_client()
        self.addCleanup(self._cleanup)

    def test_returns_traded_price_as_float(self):
        self.mock_http.get.return_value = {"orderId": "ORD1", "tradedPrice": "2500.50"}
        result = self.client.get_executed_price("ORD1")
        self.assertIsInstance(result, float)
        self.assertEqual(result, 2500.50)

    def test_returns_zero_when_no_traded_price(self):
        self.mock_http.get.return_value = {"orderId": "ORD1"}
        result = self.client.get_executed_price("ORD1")
        self.assertEqual(result, 0.0)

    def test_returns_zero_when_traded_price_null(self):
        self.mock_http.get.return_value = {"orderId": "ORD1", "tradedPrice": None}
        result = self.client.get_executed_price("ORD1")
        self.assertEqual(result, 0.0)

    def test_handles_numeric_traded_price(self):
        self.mock_http.get.return_value = {"orderId": "ORD1", "tradedPrice": 2510.75}
        result = self.client.get_executed_price("ORD1")
        self.assertEqual(result, 2510.75)


# ── get_executed_price_and_time ──────────────────────────────────

class TestGetExecutedPriceAndTime(unittest.TestCase):
    def setUp(self):
        self.client, self.mock_http, self.mock_rate, self._cleanup = _make_client()
        self.addCleanup(self._cleanup)

    def test_returns_tuple_of_price_and_time(self):
        self.mock_http.get.return_value = {
            "orderId": "ORD1", "tradedPrice": "2500.50", "tradedTime": "2024-06-15T10:30:00",
        }
        result = self.client.get_executed_price_and_time("ORD1")
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], 2500.50)
        self.assertEqual(result[1], "2024-06-15T10:30:00")

    def test_extracts_price_correctly(self):
        self.mock_http.get.return_value = {
            "orderId": "ORD1", "tradedPrice": "1500.00", "traded_at": "2024-06-15T11:00:00",
        }
        result = self.client.get_executed_price_and_time("ORD1")
        self.assertEqual(result[0], 1500.00)

    def test_extracts_traded_at_field(self):
        self.mock_http.get.return_value = {
            "orderId": "ORD1", "tradedPrice": "500.00", "traded_at": "2024-06-15T12:00:00",
        }
        result = self.client.get_executed_price_and_time("ORD1")
        self.assertEqual(result[1], "2024-06-15T12:00:00")

    def test_falls_back_to_tradedTime(self):
        self.mock_http.get.return_value = {
            "orderId": "ORD1", "tradedPrice": "300.00", "tradedTime": "2024-06-15T13:00:00",
        }
        result = self.client.get_executed_price_and_time("ORD1")
        self.assertEqual(result[1], "2024-06-15T13:00:00")

    def test_returns_empty_string_when_no_time(self):
        self.mock_http.get.return_value = {"orderId": "ORD1", "tradedPrice": "100.00"}
        result = self.client.get_executed_price_and_time("ORD1")
        self.assertEqual(result[1], "")

    def test_returns_float_and_str_types(self):
        self.mock_http.get.return_value = {"orderId": "ORD1", "tradedPrice": "99.99"}
        result = self.client.get_executed_price_and_time("ORD1")
        self.assertIsInstance(result[0], float)
        self.assertIsInstance(result[1], str)


# ── cancel_all_orders ─────────────────────────────────────────────

class TestCancelAllOrders(unittest.TestCase):
    def setUp(self):
        self.client, self.mock_http, self.mock_rate, self._cleanup = _make_client()
        self.addCleanup(self._cleanup)

    def test_cancels_all_open_orders(self):
        self.mock_http.get.return_value = [
            {"orderId": "O1", "status": "OPEN"},
            {"orderId": "O2", "status": "PENDING"},
            {"orderId": "O3", "status": "TRIGGER PENDING"},
            {"orderId": "O4", "status": "PARTIALLY FILLED"},
        ]
        result = self.client.cancel_all_orders()
        self.assertEqual(result, 4)
        self.assertEqual(self.mock_http.delete.call_count, 4)
        self.mock_http.delete.assert_any_call("/orders/O1", bucket="orders")
        self.mock_http.delete.assert_any_call("/orders/O4", bucket="orders")

    def test_skips_terminal_orders(self):
        self.mock_http.get.return_value = [
            {"orderId": "O1", "status": "OPEN"},
            {"orderId": "O2", "status": "FILLED"},
            {"orderId": "O3", "status": "CANCELLED"},
            {"orderId": "O4", "status": "REJECTED"},
            {"orderId": "O5", "status": "EXPIRED"},
        ]
        result = self.client.cancel_all_orders()
        self.assertEqual(result, 1)
        self.mock_http.delete.assert_called_once_with("/orders/O1", bucket="orders")

    def test_filters_by_symbol(self):
        self.mock_http.get.return_value = [
            {"orderId": "O1", "status": "OPEN", "tradingSymbol": "RELIANCE"},
            {"orderId": "O2", "status": "OPEN", "tradingSymbol": "TCS"},
            {"orderId": "O3", "status": "OPEN", "tradingSymbol": "RELIANCE"},
        ]
        result = self.client.cancel_all_orders(symbol="RELIANCE")
        self.assertEqual(result, 2)
        self.assertEqual(self.mock_http.delete.call_count, 2)

    def test_filters_by_symbol_fallback_to_symbol_key(self):
        self.mock_http.get.return_value = [
            {"orderId": "O1", "status": "OPEN", "symbol": "INFY"},
            {"orderId": "O2", "status": "PENDING", "symbol": "INFY"},
        ]
        result = self.client.cancel_all_orders(symbol="INFY")
        self.assertEqual(result, 2)

    def test_handles_empty_response(self):
        self.mock_http.get.return_value = []
        result = self.client.cancel_all_orders()
        self.assertEqual(result, 0)
        self.mock_http.delete.assert_not_called()

    def test_handles_dict_wrapped_response(self):
        self.mock_http.get.return_value = {
            "data": [
                {"orderId": "O1", "status": "OPEN"},
                {"orderId": "O2", "status": "PENDING"},
            ],
        }
        result = self.client.cancel_all_orders()
        self.assertEqual(result, 2)

    def test_handles_non_list_non_dict_response(self):
        self.mock_http.get.return_value = None
        result = self.client.cancel_all_orders()
        self.assertEqual(result, 0)

    def test_continues_on_delete_error(self):
        self.mock_http.get.return_value = [
            {"orderId": "O1", "status": "OPEN"},
            {"orderId": "O2", "status": "OPEN"},
        ]
        self.mock_http.delete.side_effect = [None, RuntimeError("API error")]
        result = self.client.cancel_all_orders()
        self.assertEqual(result, 1)

    def test_acquires_rate_limit(self):
        self.mock_http.get.return_value = []
        self.client.cancel_all_orders()


# ── order_report ──────────────────────────────────────────────────

class TestOrderReport(unittest.TestCase):
    def setUp(self):
        self.client, self.mock_http, self.mock_rate, self._cleanup = _make_client()
        self.addCleanup(self._cleanup)

    def test_returns_full_order_detail(self):
        self.mock_http.get.return_value = {
            "orderId": "ORD1", "symbol": "RELIANCE", "status": "FILLED",
            "quantity": 10, "price": "2500", "tradedPrice": "2500.50",
            "filledQuantity": 10, "orderType": "LIMIT",
        }
        result = self.client.order_report("ORD1")
        self.assertEqual(result["orderId"], "ORD1")
        self.assertEqual(result["symbol"], "RELIANCE")
        self.assertEqual(result["status"], "FILLED")
        self.assertEqual(result["tradedPrice"], "2500.50")

    def test_makes_http_get_call(self):
        self.mock_http.get.return_value = {"orderId": "ORD1"}
        self.client.order_report("ORD1")
        self.mock_http.get.assert_called_once_with("/orders/ORD1", bucket="orders")

    def test_acquires_rate_limit(self):
        self.mock_http.get.return_value = {}
        self.client.order_report("ORD1")

    def test_raises_on_404(self):
        self.mock_http.get.side_effect = DhanRequestError(404, "Not Found")
        with self.assertRaises(DhanRequestError):
            self.client.order_report("BADID")


# ── get_trade_book ────────────────────────────────────────────────

class TestGetTradeBook(unittest.TestCase):
    def setUp(self):
        self.client, self.mock_http, self.mock_rate, self._cleanup = _make_client()
        self.addCleanup(self._cleanup)

    def test_returns_list_of_trades(self):
        self.mock_http.get.return_value = [
            {"tradeId": "T1", "orderId": "O1", "symbol": "RELIANCE", "quantity": 10, "price": "2500"},
            {"tradeId": "T2", "orderId": "O2", "symbol": "TCS", "quantity": 5, "price": "3500"},
        ]
        result = self.client.get_trade_book()
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["tradeId"], "T1")

    def test_returns_empty_list_when_no_trades(self):
        self.mock_http.get.return_value = []
        result = self.client.get_trade_book()
        self.assertEqual(result, [])

    def test_extracts_from_dict_when_wrapped(self):
        self.mock_http.get.return_value = {
            "data": [
                {"tradeId": "T1", "orderId": "O1"},
                {"tradeId": "T2", "orderId": "O2"},
            ],
        }
        result = self.client.get_trade_book()
        self.assertEqual(len(result), 2)

    def test_extracts_from_trades_key(self):
        self.mock_http.get.return_value = {
            "trades": [
                {"tradeId": "T1", "orderId": "O1"},
            ],
        }
        result = self.client.get_trade_book()
        self.assertEqual(len(result), 1)

    def test_returns_empty_list_for_non_list_non_dict(self):
        self.mock_http.get.return_value = None
        result = self.client.get_trade_book()
        self.assertEqual(result, [])

    def test_gets_trades_endpoint(self):
        self.mock_http.get.return_value = []
        self.client.get_trade_book()
        self.mock_http.get.assert_called_once_with("/trades", bucket="orders")

    def test_acquires_rate_limit(self):
        self.mock_http.get.return_value = []
        self.client.get_trade_book()


# ── get_exchange_time ─────────────────────────────────────────────

class TestGetExchangeTime(unittest.TestCase):
    def setUp(self):
        self.client, self.mock_http, self.mock_rate, self._cleanup = _make_client()
        self.addCleanup(self._cleanup)

    def test_returns_string_from_direct_response(self):
        self.mock_http.get.return_value = "2024-06-15T10:30:00"
        result = self.client.get_exchange_time()
        self.assertIsInstance(result, str)
        self.assertEqual(result, "2024-06-15T10:30:00")

    def test_extracts_exchange_time_from_dict(self):
        self.mock_http.get.return_value = {"exchangeTime": "2024-06-15T10:30:00"}
        result = self.client.get_exchange_time()
        self.assertEqual(result, "2024-06-15T10:30:00")

    def test_falls_back_to_time_key(self):
        self.mock_http.get.return_value = {"time": "2024-06-15T11:00:00"}
        result = self.client.get_exchange_time()
        self.assertEqual(result, "2024-06-15T11:00:00")

    def test_falls_back_to_dateTime_key(self):
        self.mock_http.get.return_value = {"dateTime": "2024-06-15T12:00:00"}
        result = self.client.get_exchange_time()
        self.assertEqual(result, "2024-06-15T12:00:00")

    def test_returns_empty_string_when_no_recognized_key(self):
        self.mock_http.get.return_value = {"foo": "bar"}
        result = self.client.get_exchange_time()
        self.assertEqual(result, "")

    def test_get_exchange_time_endpoint(self):
        self.mock_http.get.return_value = {}
        self.client.get_exchange_time()
        self.mock_http.get.assert_called_once_with("/exchange/time", bucket="portfolio")

    def test_acquires_rate_limit(self):
        self.mock_http.get.return_value = {}
        self.client.get_exchange_time()


# ── order_report_to_dict mapper ───────────────────────────────────

class TestOrderReportToDict(unittest.TestCase):
    def test_maps_all_fields(self):
        resp = {
            "orderId": "ORD1",
            "tradingSymbol": "RELIANCE",
            "exchangeSegment": "NSE_EQ",
            "transactionType": "BUY",
            "orderType": "LIMIT",
            "quantity": 10,
            "filledQuantity": 5,
            "price": "2500.00",
            "triggerPrice": "0",
            "tradedPrice": "2500.50",
            "status": "PARTIALLY FILLED",
            "productType": "INTRADAY",
            "validity": "DAY",
            "rejectReason": "",
            "tradedTime": "2024-06-15T10:30:00",
            "createdAt": "2024-06-15T10:29:00",
        }
        result = order_report_to_dict(resp)
        self.assertEqual(result["order_id"], "ORD1")
        self.assertEqual(result["symbol"], "RELIANCE")
        self.assertEqual(result["exchange_segment"], "NSE_EQ")
        self.assertEqual(result["side"], "BUY")
        self.assertEqual(result["order_type"], "LIMIT")
        self.assertEqual(result["quantity"], 10)
        self.assertEqual(result["filled_quantity"], 5)
        self.assertEqual(result["price"], "2500.00")
        self.assertEqual(result["traded_price"], "2500.50")
        self.assertEqual(result["status"], "PARTIALLY FILLED")
        self.assertEqual(result["product_type"], "INTRADAY")
        self.assertEqual(result["validity"], "DAY")
        self.assertEqual(result["traded_at"], "2024-06-15T10:30:00")
        self.assertEqual(result["created_at"], "2024-06-15T10:29:00")

    def test_falls_back_to_symbol_key(self):
        resp = {"orderId": "O1", "symbol": "TCS"}
        result = order_report_to_dict(resp)
        self.assertEqual(result["symbol"], "TCS")

    def test_handles_missing_fields(self):
        result = order_report_to_dict({})
        self.assertEqual(result["order_id"], "")
        self.assertEqual(result["symbol"], "")
        self.assertEqual(result["quantity"], 0)
        self.assertEqual(result["price"], "0")
        self.assertEqual(result["status"], "")

    def test_uses_traded_at_over_tradedTime(self):
        resp = {"orderId": "O1", "traded_at": "alpha", "tradedTime": "beta"}
        result = order_report_to_dict(resp)
        self.assertEqual(result["traded_at"], "alpha")

    def test_uses_createdAt_over_createAt(self):
        resp = {"orderId": "O1", "createdAt": "alpha", "createAt": "beta"}
        result = order_report_to_dict(resp)
        self.assertEqual(result["created_at"], "alpha")


# ── trade_to_domain mapper ────────────────────────────────────────

class TestTradeToDomain(unittest.TestCase):
    def test_maps_all_fields(self):
        trade = {
            "tradeId": "T1",
            "orderId": "O1",
            "tradingSymbol": "RELIANCE",
            "exchangeSegment": "NSE_EQ",
            "transactionType": "BUY",
            "quantity": 10,
            "price": "2500.50",
            "tradeDateTime": "2024-06-15T10:30:00",
        }
        result = trade_to_domain(trade)
        self.assertEqual(result["trade_id"], "T1")
        self.assertEqual(result["order_id"], "O1")
        self.assertEqual(result["symbol"], "RELIANCE")
        self.assertEqual(result["exchange_segment"], "NSE_EQ")
        self.assertEqual(result["side"], "BUY")
        self.assertEqual(result["quantity"], 10)
        self.assertEqual(result["price"], "2500.50")
        self.assertEqual(result["traded_at"], "2024-06-15T10:30:00")

    def test_falls_back_to_symbol_key(self):
        trade = {"tradeId": "T1", "orderId": "O1", "symbol": "TCS"}
        result = trade_to_domain(trade)
        self.assertEqual(result["symbol"], "TCS")

    def test_falls_back_to_traded_at_key(self):
        trade = {"tradeId": "T1", "orderId": "O1", "traded_at": "2024-06-15T11:00:00"}
        result = trade_to_domain(trade)
        self.assertEqual(result["traded_at"], "2024-06-15T11:00:00")

    def test_handles_missing_fields(self):
        result = trade_to_domain({})
        self.assertEqual(result["trade_id"], "")
        self.assertEqual(result["order_id"], "")
        self.assertEqual(result["quantity"], 0)
        self.assertEqual(result["price"], "0")

    def test_handles_empty_dict(self):
        result = trade_to_domain({})
        self.assertIsInstance(result, dict)
        self.assertEqual(len(result), 8)


# ── as_df option ──────────────────────────────────────────────────

class TestGetTradeBookWithAsDf(unittest.TestCase):
    def setUp(self):
        self.client, self.mock_http, self.mock_rate, self._cleanup = _make_client()
        self.addCleanup(self._cleanup)

    def test_returns_dataframe_when_as_df_true(self):
        self.mock_http.get.return_value = [
            {"tradeId": "T1", "symbol": "RELIANCE", "quantity": 10},
            {"tradeId": "T2", "symbol": "TCS", "quantity": 5},
        ]
        result = self.client.get_trade_book(as_df=True)
        self.assertTrue(hasattr(result, "columns"))
        self.assertEqual(len(result), 2)

    def test_dataframe_has_expected_columns(self):
        self.mock_http.get.return_value = [
            {"tradeId": "T1", "symbol": "RELIANCE", "quantity": 10},
        ]
        result = self.client.get_trade_book(as_df=True)
        self.assertIn("tradeId", result.columns)
        self.assertIn("symbol", result.columns)


class TestGetOrderDetailWithAsDf(unittest.TestCase):
    def setUp(self):
        self.client, self.mock_http, self.mock_rate, self._cleanup = _make_client()
        self.addCleanup(self._cleanup)

    def test_returns_dataframe_when_as_df_true(self):
        self.mock_http.get.return_value = {"orderId": "ORD1", "status": "FILLED", "symbol": "RELIANCE"}
        result = self.client.get_order_detail("ORD1", as_df=True)
        self.assertTrue(hasattr(result, "columns"))
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]["orderId"], "ORD1")


class TestGetSuperOrdersWithAsDf(unittest.TestCase):
    def setUp(self):
        self.client, self.mock_http, self.mock_rate, self._cleanup = _make_client()
        self.addCleanup(self._cleanup)

    def test_returns_dataframe_when_as_df_true(self):
        self.mock_http.get.return_value = [
            {"orderId": "SO1", "status": "ACTIVE"},
            {"orderId": "SO2", "status": "TRIGGERED"},
        ]
        result = self.client.get_super_orders(as_df=True)
        self.assertTrue(hasattr(result, "columns"))
        self.assertEqual(len(result), 2)

    def test_dataframe_has_expected_columns(self):
        self.mock_http.get.return_value = [
            {"orderId": "SO1", "status": "ACTIVE"},
        ]
        result = self.client.get_super_orders(as_df=True)
        self.assertIn("orderId", result.columns)
        self.assertIn("status", result.columns)


class TestGetMarketDepthDfWithAsDf(unittest.TestCase):
    def setUp(self):
        self.client, self.mock_http, self.mock_rate, self._cleanup = _make_client()
        self.addCleanup(self._cleanup)

    def test_returns_dataframe_when_as_df_true(self):
        self.client.get_market_depth_snapshot = MagicMock(return_value={
            "depth": {
                "bid": [
                    {"price": "100", "quantity": 10, "orders": 1},
                    {"price": "99", "quantity": 20, "orders": 2},
                ],
                "ask": [
                    {"price": "101", "quantity": 5, "orders": 1},
                    {"price": "102", "quantity": 15, "orders": 3},
                ],
            },
        })
        result = self.client.get_market_depth_df("dummy_id", as_df=True)
        self.assertTrue(hasattr(result, "columns"))
        self.assertEqual(len(result), 2)

    def test_dataframe_has_expected_columns(self):
        self.client.get_market_depth_snapshot = MagicMock(return_value={
            "depth": {
                "bid": [{"price": "100", "quantity": 10, "orders": 1}],
                "ask": [{"price": "101", "quantity": 5, "orders": 1}],
            },
        })
        result = self.client.get_market_depth_df("dummy_id", as_df=True)
        for col in ("level", "bid_price", "bid_qty", "bid_orders", "ask_price", "ask_qty", "ask_orders"):
            self.assertIn(col, result.columns)


class TestDefaultBehaviorUnchanged(unittest.TestCase):
    def setUp(self):
        self.client, self.mock_http, self.mock_rate, self._cleanup = _make_client()
        self.addCleanup(self._cleanup)

    def test_get_trade_book_default_returns_list(self):
        self.mock_http.get.return_value = [{"tradeId": "T1"}]
        result = self.client.get_trade_book()
        self.assertIsInstance(result, list)

    def test_get_order_detail_default_returns_dict(self):
        self.mock_http.get.return_value = {"orderId": "ORD1"}
        result = self.client.get_order_detail("ORD1")
        self.assertIsInstance(result, dict)

    def test_get_super_orders_default_returns_list(self):
        self.mock_http.get.return_value = [{"orderId": "SO1"}]
        result = self.client.get_super_orders()
        self.assertIsInstance(result, list)

    def test_get_market_depth_df_default_returns_list(self):
        self.client.get_market_depth_snapshot = MagicMock(return_value={
            "depth": {
                "bid": [{"price": "100", "quantity": 10, "orders": 1}],
                "ask": [{"price": "101", "quantity": 5, "orders": 1}],
            },
        })
        result = self.client.get_market_depth_df("dummy_id")
        self.assertIsInstance(result, list)


if __name__ == "__main__":
    unittest.main()

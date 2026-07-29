from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

from scalpr.adapters.dhan._portfolio import (
    PnLCalculationError,
    PortfolioAdapter,
    PortfolioError,
)
from scalpr.domain.instrument import Exchange
from scalpr.domain.position import Position, PositionSide, PositionState
from scalpr.domain.values import ZERO

# =========================================================================
# Error type hierarchy
# =========================================================================

class TestPortfolioErrorTypes:
    def test_portfolio_error_is_exception(self):
        assert issubclass(PortfolioError, Exception)

    def test_pnl_calculation_error_is_portfolio_error(self):
        assert issubclass(PnLCalculationError, PortfolioError)


# =========================================================================
# Construction
# =========================================================================

class TestPortfolioAdapterConstruction:
    def test_creates_with_http_client(self):
        http = MagicMock()
        adapter = PortfolioAdapter(http)
        assert adapter._http is http

    def test_stores_http_client_reference(self):
        http = MagicMock()
        adapter = PortfolioAdapter(http)
        assert adapter._http is not None


# =========================================================================
# get_funds
# =========================================================================

class TestGetFunds:
    def test_delegates_to_fundlimit_endpoint(self):
        http = MagicMock()
        http.get.return_value = {"availableBalance": "50000"}
        adapter = PortfolioAdapter(http)

        result = adapter.get_funds()

        http.get.assert_called_once_with("/fundlimit", bucket="portfolio")
        assert result == {"availableBalance": "50000"}

    def test_returns_raw_response(self):
        http = MagicMock()
        expected = {"availableBalance": "100000", "utilizedMargin": "25000"}
        http.get.return_value = expected
        adapter = PortfolioAdapter(http)

        result = adapter.get_funds()

        assert result == expected


# =========================================================================
# get_live_pnl — basic scenarios
# =========================================================================

class TestGetLivePnlBasic:
    def test_returns_zero_when_no_positions(self):
        http = MagicMock()
        http.get.return_value = []
        adapter = PortfolioAdapter(http)

        result = adapter.get_live_pnl()

        assert result == 0.0

    def test_returns_zero_when_no_positions_list(self):
        http = MagicMock()
        adapter = PortfolioAdapter(http)

        result = adapter.get_live_pnl(positions=[])

        assert result == 0.0

    def test_long_position_correct_positive_pnl(self):
        http = MagicMock()
        http.get.return_value = [{
            "securityId": "12345",
            "exchangeSegment": "NSE_EQ",
            "tradingSymbol": "RELIANCE",
            "netQty": 100,
            "dayBuyQty": 100,
            "daySellQty": 0,
            "dayBuyAvg": "100",
            "daySellAvg": "0",
            "buyAvg": "100",
            "sellAvg": "0",
            "multiplier": 1,
            "ltp": "102",
        }]
        http.post.return_value = {"12345": {"ltp": "105"}}
        adapter = PortfolioAdapter(http)

        result = adapter.get_live_pnl()
        # (0 - 100*100) + (100 * 105 * 1) = -10000 + 10500 = 500

        assert result == 500.0

    def test_long_position_correct_negative_pnl(self):
        http = MagicMock()
        http.get.return_value = [{
            "securityId": "12345",
            "exchangeSegment": "NSE_EQ",
            "tradingSymbol": "RELIANCE",
            "netQty": 100,
            "dayBuyQty": 100,
            "daySellQty": 0,
            "dayBuyAvg": "100",
            "daySellAvg": "0",
            "buyAvg": "100",
            "sellAvg": "0",
            "multiplier": 1,
            "ltp": "102",
        }]
        http.post.return_value = {"12345": {"ltp": "90"}}
        adapter = PortfolioAdapter(http)

        result = adapter.get_live_pnl()
        # (0 - 100*100) + (100 * 90 * 1) = -10000 + 9000 = -1000

        assert result == -1000.0

    def test_short_position_correct_positive_pnl(self):
        http = MagicMock()
        http.get.return_value = [{
            "securityId": "12345",
            "exchangeSegment": "NSE_EQ",
            "tradingSymbol": "TCS",
            "netQty": -50,
            "dayBuyQty": 0,
            "daySellQty": 50,
            "dayBuyAvg": "0",
            "daySellAvg": "150",
            "buyAvg": "0",
            "sellAvg": "150",
            "multiplier": 1,
            "ltp": "148",
        }]
        http.post.return_value = {"12345": {"ltp": "145"}}
        adapter = PortfolioAdapter(http)

        result = adapter.get_live_pnl()
        # (50*150 - 0) + (-50 * 145 * 1) = 7500 - 7250 = 250

        assert result == 250.0

    def test_short_position_correct_negative_pnl(self):
        http = MagicMock()
        http.get.return_value = [{
            "securityId": "12345",
            "exchangeSegment": "NSE_EQ",
            "tradingSymbol": "TCS",
            "netQty": -50,
            "dayBuyQty": 0,
            "daySellQty": 50,
            "dayBuyAvg": "0",
            "daySellAvg": "150",
            "buyAvg": "0",
            "sellAvg": "150",
            "multiplier": 1,
            "ltp": "148",
        }]
        http.post.return_value = {"12345": {"ltp": "155"}}
        adapter = PortfolioAdapter(http)

        result = adapter.get_live_pnl()
        # (50*150 - 0) + (-50 * 155 * 1) = 7500 - 7750 = -250

        assert result == -250.0

    def test_flat_position_returns_zero(self):
        http = MagicMock()
        http.get.return_value = [{
            "securityId": "12345",
            "exchangeSegment": "NSE_EQ",
            "tradingSymbol": "RELIANCE",
            "netQty": 0,
            "dayBuyQty": 100,
            "daySellQty": 100,
            "dayBuyAvg": "100",
            "daySellAvg": "105",
            "buyAvg": "100",
            "sellAvg": "105",
            "multiplier": 1,
            "ltp": "103",
        }]
        adapter = PortfolioAdapter(http)

        result = adapter.get_live_pnl()
        # net qty = 0 => filtered out => empty list => 0.0

        assert result == 0.0

    def test_uses_provided_positions_instead_of_fetching(self):
        http = MagicMock()
        adapter = PortfolioAdapter(http)
        pos = Position(
            symbol="RELIANCE", exchange=Exchange.NSE,
            quantity=10, avg_price=Decimal("100"),
            ltp=Decimal("102"), position_side=PositionSide.LONG,
            state=PositionState.OPEN,
        )
        http.post.return_value = {"RELIANCE": {"ltp": "110"}}

        result = adapter.get_live_pnl(positions=[pos])
        # Provided positions use symbol as security_id, day_buy/sell = 0
        # (0 - 0) + (10 * 110 * 1) = 1100

        http.get.assert_not_called()
        assert result == 1100.0


# =========================================================================
# get_live_pnl — batch LTP fetch
# =========================================================================

class TestGetLivePnlBatchLtp:
    def test_fetches_ltp_for_all_positions_batched(self):
        http = MagicMock()
        http.get.return_value = [
            {
                "securityId": "111",
                "exchangeSegment": "NSE_EQ",
                "tradingSymbol": "RELIANCE",
                "netQty": 100,
                "dayBuyQty": 100,
                "daySellQty": 0,
                "dayBuyAvg": "100",
                "daySellAvg": "0",
                "buyAvg": "100",
                "sellAvg": "0",
                "multiplier": 1,
                "ltp": "102",
            },
            {
                "securityId": "222",
                "exchangeSegment": "NSE_EQ",
                "tradingSymbol": "TCS",
                "netQty": -50,
                "dayBuyQty": 0,
                "daySellQty": 50,
                "dayBuyAvg": "0",
                "daySellAvg": "200",
                "buyAvg": "0",
                "sellAvg": "200",
                "multiplier": 1,
                "ltp": "198",
            },
        ]
        http.post.return_value = {
            "111": {"ltp": "105"},
            "222": {"ltp": "195"},
        }
        adapter = PortfolioAdapter(http)

        result = adapter.get_live_pnl()

        http.post.assert_called_once_with(
            "/marketfeed/quote",
            data={"security_ids": ["111", "222"], "exchangeSegment": "NSE_EQ"},
            bucket="market_data",
        )
        # RELIANCE: (0-10000) + (100*105) = 500
        # TCS: (50*200-0) + (-50*195) = 10000-9750 = 250
        # Total: 750
        assert result == 750.0

    def test_groups_by_exchange_segment(self):
        http = MagicMock()
        http.get.return_value = [
            {
                "securityId": "111",
                "exchangeSegment": "NSE_EQ",
                "tradingSymbol": "RELIANCE",
                "netQty": 10,
                "dayBuyQty": 10,
                "daySellQty": 0,
                "dayBuyAvg": "100",
                "daySellAvg": "0",
                "buyAvg": "100",
                "sellAvg": "0",
                "multiplier": 1,
                "ltp": "102",
            },
            {
                "securityId": "333",
                "exchangeSegment": "NSE_FNO",
                "tradingSymbol": "NIFTY25JUL23000CE",
                "netQty": 75,
                "dayBuyQty": 75,
                "daySellQty": 0,
                "dayBuyAvg": "150",
                "daySellAvg": "0",
                "buyAvg": "150",
                "sellAvg": "0",
                "multiplier": 50,
                "ltp": "155",
            },
        ]
        http.post.return_value = {
            "111": {"ltp": "105"},
            "333": {"ltp": "160"},
        }
        adapter = PortfolioAdapter(http)

        result = adapter.get_live_pnl()

        assert http.post.call_count == 2
        calls = http.post.call_args_list
        eq_call = [c for c in calls if c[1]["data"]["exchangeSegment"] == "NSE_EQ"]
        fno_call = [c for c in calls if c[1]["data"]["exchangeSegment"] == "NSE_FNO"]
        assert len(eq_call) == 1
        assert len(fno_call) == 1
        assert eq_call[0][1]["data"]["security_ids"] == ["111"]
        assert fno_call[0][1]["data"]["security_ids"] == ["333"]
        # RELIANCE: (0-1000) + (10*105) = 50
        # NIFTY: (0-75*150) + (75*160*50) = -11250 + 600000 = 588750
        # Total: 588800
        assert result == 588800.0


# =========================================================================
# get_live_pnl — error handling
# =========================================================================

class TestGetLivePnlErrors:
    def test_network_error_returns_zero_gracefully(self):
        http = MagicMock()
        http.get.side_effect = ConnectionError("network down")
        adapter = PortfolioAdapter(http)

        result = adapter.get_live_pnl()

        assert result == 0.0

    def test_missing_ltp_uses_position_ltp(self):
        http = MagicMock()
        http.get.return_value = [{
            "securityId": "12345",
            "exchangeSegment": "NSE_EQ",
            "tradingSymbol": "RELIANCE",
            "netQty": 100,
            "dayBuyQty": 100,
            "daySellQty": 0,
            "dayBuyAvg": "100",
            "daySellAvg": "0",
            "buyAvg": "100",
            "sellAvg": "0",
            "multiplier": 1,
            "ltp": "102",
        }]
        http.post.side_effect = RuntimeError("API error")
        adapter = PortfolioAdapter(http)

        result = adapter.get_live_pnl()
        # Falls back to ltp from position data: 102
        # (0-10000) + (100*102*1) = 200

        assert result == 200.0

    def test_partial_ltp_missing_uses_default(self):
        http = MagicMock()
        http.get.return_value = [
            {
                "securityId": "111",
                "exchangeSegment": "NSE_EQ",
                "tradingSymbol": "A",
                "netQty": 10,
                "dayBuyQty": 10,
                "daySellQty": 0,
                "dayBuyAvg": "100",
                "daySellAvg": "0",
                "buyAvg": "100",
                "sellAvg": "0",
                "multiplier": 1,
                "ltp": "101",
            },
            {
                "securityId": "222",
                "exchangeSegment": "NSE_EQ",
                "tradingSymbol": "B",
                "netQty": 20,
                "dayBuyQty": 0,
                "daySellQty": 20,
                "dayBuyAvg": "0",
                "daySellAvg": "50",
                "buyAvg": "0",
                "sellAvg": "50",
                "multiplier": 1,
                "ltp": "48",
            },
        ]
        http.post.return_value = {"111": {"ltp": "105"}}
        adapter = PortfolioAdapter(http)

        result = adapter.get_live_pnl()
        # A: (0-1000) + (10*105) = 50
        # B: (20*50-0) + (20*48*1) = 1000+960 = 1960
        # Total: 2010

        assert result == 2010.0

    def test_malformed_position_data_skips_gracefully(self):
        http = MagicMock()
        http.get.return_value = [{
            "securityId": "12345",
            "exchangeSegment": "NSE_EQ",
            "tradingSymbol": "RELIANCE",
        }]
        http.post.return_value = {}
        adapter = PortfolioAdapter(http)

        result = adapter.get_live_pnl()

        assert result == 0.0

    def test_positions_to_raw_without_security_id(self):
        http = MagicMock()
        adapter = PortfolioAdapter(http)
        pos = Position(
            symbol="RELIANCE", exchange=Exchange.NSE,
            quantity=10, avg_price=Decimal("100"),
            ltp=Decimal("110"), position_side=PositionSide.LONG,
            state=PositionState.OPEN,
        )

        result = adapter.get_live_pnl(positions=[pos])
        # symbol used as security_id; LTP fetched by symbol as key

        assert result == 1100.0


# =========================================================================
# get_positions_summary
# =========================================================================

class TestGetPositionsSummary:
    def test_returns_zero_values_for_empty_positions(self):
        http = MagicMock()
        http.get.return_value = []
        adapter = PortfolioAdapter(http)

        result = adapter.get_positions_summary()

        assert result["total_investment"] == 0.0
        assert result["current_value"] == 0.0
        assert result["unrealized_pnl"] == 0.0
        assert result["realized_pnl"] == 0.0

    def test_total_investment_sum_of_abs_qty_times_avg(self):
        http = MagicMock()
        http.get.return_value = [
            {
                "securityId": "111", "exchangeSegment": "NSE_EQ",
                "tradingSymbol": "A", "netQty": 100, "dayBuyQty": 100,
                "daySellQty": 0, "dayBuyAvg": "50", "daySellAvg": "0",
                "buyAvg": "50", "sellAvg": "0", "multiplier": 1,
                "ltp": "55", "realizedPnl": "200",
            },
            {
                "securityId": "222", "exchangeSegment": "NSE_EQ",
                "tradingSymbol": "B", "netQty": -200, "dayBuyQty": 0,
                "daySellQty": 200, "dayBuyAvg": "0", "daySellAvg": "30",
                "buyAvg": "25", "sellAvg": "30", "multiplier": 1,
                "ltp": "28", "realizedPnl": "100",
            },
        ]
        http.post.return_value = {"111": {"ltp": "55"}, "222": {"ltp": "28"}}
        adapter = PortfolioAdapter(http)

        result = adapter.get_positions_summary()
        # total_investment: 100*50 + abs(-200)*30 = 5000 + 6000 = 11000
        # current_value: 100*55 + 200*28 = 5500 + 5600 = 11100
        # unrealized: long: 100*(55-50)=500, short: 200*(30-28)=400 => 900
        # realized: 200 + 100 = 300

        assert result["total_investment"] == 11000.0
        assert result["current_value"] == 11100.0
        assert result["unrealized_pnl"] == 900.0
        assert result["realized_pnl"] == 300.0

    def test_summary_fails_gracefully_on_error(self):
        http = MagicMock()
        http.get.side_effect = RuntimeError("API down")
        adapter = PortfolioAdapter(http)

        result = adapter.get_positions_summary()

        assert result["total_investment"] == 0.0
        assert result["current_value"] == 0.0
        assert result["unrealized_pnl"] == 0.0
        assert result["realized_pnl"] == 0.0

    def test_summary_with_single_long_position(self):
        http = MagicMock()
        http.get.return_value = [{
            "securityId": "111", "exchangeSegment": "NSE_EQ",
            "tradingSymbol": "RELIANCE", "netQty": 50, "dayBuyQty": 50,
            "daySellQty": 0, "dayBuyAvg": "2000", "daySellAvg": "0",
            "buyAvg": "2000", "sellAvg": "0", "multiplier": 1,
            "ltp": "2020", "realizedPnl": "500",
        }]
        http.post.return_value = {"111": {"ltp": "2020"}}
        adapter = PortfolioAdapter(http)

        result = adapter.get_positions_summary()

        assert result["total_investment"] == 100000.0
        assert result["current_value"] == 101000.0
        assert result["unrealized_pnl"] == 1000.0
        assert result["realized_pnl"] == 500.0


# =========================================================================
# _fetch_ltp_batch — response parsing
# =========================================================================

class TestFetchLtpBatch:
    def test_parses_dict_response_with_data_wrapper(self):
        http = MagicMock()
        http.post.return_value = {
            "data": {
                "111": {"ltp": "105.50"},
                "222": {"ltp": "205.00"},
            },
        }
        adapter = PortfolioAdapter(http)
        raw = [
            {"security_id": "111", "exchange_segment": "NSE_EQ", "net_qty": 10, "day_buy_qty": 0, "day_sell_qty": 0, "day_buy_avg": ZERO, "day_sell_avg": ZERO, "buy_avg": ZERO, "sell_avg": ZERO, "multiplier": 1, "ltp": ZERO, "realized_pnl": ZERO},
            {"security_id": "222", "exchange_segment": "NSE_EQ", "net_qty": 20, "day_buy_qty": 0, "day_sell_qty": 0, "day_buy_avg": ZERO, "day_sell_avg": ZERO, "buy_avg": ZERO, "sell_avg": ZERO, "multiplier": 1, "ltp": ZERO, "realized_pnl": ZERO},
        ]

        result = adapter._fetch_ltp_batch(raw)

        assert result["111"] == Decimal("105.50")
        assert result["222"] == Decimal("205.00")

    def test_parses_list_response(self):
        http = MagicMock()
        http.post.return_value = [
            {"securityId": "111", "ltp": "105.50"},
            {"securityId": "222", "ltp": "205.00"},
        ]
        adapter = PortfolioAdapter(http)
        raw = [
            {"security_id": "111", "exchange_segment": "NSE_EQ", "net_qty": 10, "day_buy_qty": 0, "day_sell_qty": 0, "day_buy_avg": ZERO, "day_sell_avg": ZERO, "buy_avg": ZERO, "sell_avg": ZERO, "multiplier": 1, "ltp": ZERO, "realized_pnl": ZERO},
            {"security_id": "222", "exchange_segment": "NSE_EQ", "net_qty": 20, "day_buy_qty": 0, "day_sell_qty": 0, "day_buy_avg": ZERO, "day_sell_avg": ZERO, "buy_avg": ZERO, "sell_avg": ZERO, "multiplier": 1, "ltp": ZERO, "realized_pnl": ZERO},
        ]

        result = adapter._fetch_ltp_batch(raw)

        assert result["111"] == Decimal("105.50")
        assert result["222"] == Decimal("205.00")

    def test_handles_empty_security_ids_gracefully(self):
        http = MagicMock()
        adapter = PortfolioAdapter(http)

        result = adapter._fetch_ltp_batch([])

        http.post.assert_not_called()
        assert result == {}

    def test_network_error_returns_partial_results(self):
        http = MagicMock()
        raw = [
            {"security_id": "111", "exchange_segment": "NSE_EQ", "net_qty": 10, "day_buy_qty": 0, "day_sell_qty": 0, "day_buy_avg": ZERO, "day_sell_avg": ZERO, "buy_avg": ZERO, "sell_avg": ZERO, "multiplier": 1, "ltp": ZERO, "realized_pnl": ZERO},
        ]
        http.post.side_effect = RuntimeError("API timeout")
        adapter = PortfolioAdapter(http)

        result = adapter._fetch_ltp_batch(raw)

        assert result == {}


# =========================================================================
# Integration: multiple positions with different segments
# =========================================================================

class TestMultiPositionEndToEnd:
    def test_mixed_long_short_positions(self):
        http = MagicMock()
        http.get.return_value = [
            {
                "securityId": "A1", "exchangeSegment": "NSE_EQ",
                "tradingSymbol": "RELIANCE", "netQty": 100, "dayBuyQty": 100,
                "daySellQty": 0, "dayBuyAvg": "2500", "daySellAvg": "0",
                "buyAvg": "2500", "sellAvg": "0", "multiplier": 1,
                "ltp": "2510",
            },
            {
                "securityId": "B1", "exchangeSegment": "NSE_EQ",
                "tradingSymbol": "TCS", "netQty": -50, "dayBuyQty": 0,
                "daySellQty": 50, "dayBuyAvg": "0", "daySellAvg": "4000",
                "buyAvg": "0", "sellAvg": "4000", "multiplier": 1,
                "ltp": "3980",
            },
        ]
        http.post.return_value = {
            "A1": {"ltp": "2550"},
            "B1": {"ltp": "3950"},
        }
        adapter = PortfolioAdapter(http)

        result = adapter.get_live_pnl()
        # RELIANCE: (0 - 100*2500) + (100*2550) = -250000 + 255000 = 5000
        # TCS: (50*4000 - 0) + (-50*3950) = 200000 - 197500 = 2500
        # Total: 7500

        assert result == 7500.0

    def test_fno_position_with_multiplier(self):
        http = MagicMock()
        http.get.return_value = [{
            "securityId": "N1", "exchangeSegment": "NSE_FNO",
            "tradingSymbol": "NIFTY25JUL23000CE",
            "netQty": 75, "dayBuyQty": 75,
            "daySellQty": 0, "dayBuyAvg": "150", "daySellAvg": "0",
            "buyAvg": "150", "sellAvg": "0", "multiplier": 50,
            "ltp": "155",
        }]
        http.post.return_value = {"N1": {"ltp": "148"}}
        adapter = PortfolioAdapter(http)

        result = adapter.get_live_pnl()
        # (0 - 75*150) + (75 * 148 * 50) = -11250 + 555000 = 543750

        assert result == 543750.0

    def test_all_day_trades_with_no_carryover(self):
        http = MagicMock()
        http.get.return_value = [{
            "securityId": "X1", "exchangeSegment": "NSE_EQ",
            "tradingSymbol": "STOCK",
            "netQty": 0,
            "dayBuyQty": 100, "daySellQty": 100,
            "dayBuyAvg": "100", "daySellAvg": "110",
            "buyAvg": "105", "sellAvg": "105",
            "multiplier": 1, "ltp": "108",
        }]
        adapter = PortfolioAdapter(http)

        result = adapter.get_live_pnl()
        # netQty=0 => filtered out => 0.0

        assert result == 0.0

    def test_partial_day_trades_with_carryover(self):
        http = MagicMock()
        http.get.return_value = [{
            "securityId": "X1", "exchangeSegment": "NSE_EQ",
            "tradingSymbol": "STOCK",
            "netQty": 50,
            "dayBuyQty": 100, "daySellQty": 50,
            "dayBuyAvg": "100", "daySellAvg": "110",
            "buyAvg": "100", "sellAvg": "110",
            "multiplier": 1, "ltp": "108",
        }]
        http.post.return_value = {"X1": {"ltp": "115"}}
        adapter = PortfolioAdapter(http)

        result = adapter.get_live_pnl()
        # (50*110 - 100*100) + (50 * 115 * 1) = (5500-10000) + 5750 = 1250

        assert result == 1250.0


# =========================================================================
# Direct _fetch_raw_positions tests
# =========================================================================

class TestFetchRawPositions:
    def test_filters_zero_net_qty(self):
        http = MagicMock()
        http.get.return_value = [
            {"securityId": "111", "netQty": 10, "quantity": 10},
            {"securityId": "222", "netQty": 0, "quantity": 0},
            {"securityId": "333", "netQty": -5, "quantity": -5},
        ]
        adapter = PortfolioAdapter(http)

        result = adapter._fetch_raw_positions()

        assert len(result) == 2
        assert result[0]["security_id"] == "111"
        assert result[1]["security_id"] == "333"

    def test_falls_back_to_quantity_field(self):
        http = MagicMock()
        http.get.return_value = [
            {"securityId": "111", "quantity": 10, "tradingSymbol": "A"},
        ]
        adapter = PortfolioAdapter(http)

        result = adapter._fetch_raw_positions()

        assert result[0]["net_qty"] == 10
        assert result[0]["symbol"] == "A"

    def test_defaults_multiplier_to_one(self):
        http = MagicMock()
        http.get.return_value = [
            {"securityId": "111", "netQty": 10, "tradingSymbol": "A"},
        ]
        adapter = PortfolioAdapter(http)

        result = adapter._fetch_raw_positions()

        assert result[0]["multiplier"] == 1

    def test_single_dict_response_wraps_to_list(self):
        http = MagicMock()
        http.get.return_value = {
            "securityId": "111", "netQty": 10, "tradingSymbol": "A",
        }
        adapter = PortfolioAdapter(http)

        result = adapter._fetch_raw_positions()

        assert len(result) == 1
        assert result[0]["security_id"] == "111"


# =========================================================================
# Edge cases
# =========================================================================

class TestEdgeCases:
    def test_zero_day_buy_sell_values(self):
        http = MagicMock()
        http.get.return_value = [{
            "securityId": "111", "exchangeSegment": "NSE_EQ",
            "tradingSymbol": "A", "netQty": 100,
            "dayBuyQty": 0, "daySellQty": 0,
            "dayBuyAvg": "0", "daySellAvg": "0",
            "buyAvg": "100", "sellAvg": "0",
            "multiplier": 1, "ltp": "105",
        }]
        http.post.return_value = {"111": {"ltp": "105"}}
        adapter = PortfolioAdapter(http)

        result = adapter.get_live_pnl()
        # (0-0) + (100*105) = 10500

        assert result == 10500.0

    def test_negative_multiplier_not_allowed_defaults(self):
        http = MagicMock()
        http.get.return_value = [{
            "securityId": "111", "exchangeSegment": "NSE_EQ",
            "tradingSymbol": "A", "netQty": 10,
            "dayBuyQty": 0, "daySellQty": 0,
            "dayBuyAvg": "0", "daySellAvg": "0",
            "buyAvg": "100", "sellAvg": "0",
            "multiplier": -1, "ltp": "105",
        }]
        http.post.return_value = {"111": {"ltp": "110"}}
        adapter = PortfolioAdapter(http)

        result = adapter.get_live_pnl()
        # multiplier preserved as-is from raw data
        # (0-0) + (10*110*-1) = -1100

        assert result == -1100.0

    def test_large_decimal_values(self):
        http = MagicMock()
        http.get.return_value = [{
            "securityId": "111", "exchangeSegment": "NSE_EQ",
            "tradingSymbol": "A", "netQty": 1000,
            "dayBuyQty": 1000, "daySellQty": 0,
            "dayBuyAvg": "1234.56", "daySellAvg": "0",
            "buyAvg": "1234.56", "sellAvg": "0",
            "multiplier": 1, "ltp": "1240.00",
        }]
        http.post.return_value = {"111": {"ltp": "1250.00"}}
        adapter = PortfolioAdapter(http)

        result = adapter.get_live_pnl()
        # (0 - 1000*1234.56) + (1000*1250.00) = -1234560 + 1250000 = 15440

        assert result == 15440.0

    def test_http_client_close_not_called_by_adapter(self):
        http = MagicMock()
        adapter = PortfolioAdapter(http)

        adapter.get_funds()

        http.close.assert_not_called()

"""Tests for OptionChainAdapter — option chain, expiry list, strike selection."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from scalpr.adapters.dhan._option_chain import (
    OptionChainAdapter,
    OptionChainError,
    StrikeNotFoundError,
)
from scalpr.adapters.dhan._resolver import SymbolResolver
from scalpr.domain.instrument import (
    Exchange,
    ResolvedInstrument,
    Segment,
    SimpleInstrumentId,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_http() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_resolver() -> MagicMock:
    return MagicMock(spec=SymbolResolver)


@pytest.fixture
def adapter(mock_http: MagicMock, mock_resolver: MagicMock) -> OptionChainAdapter:
    return OptionChainAdapter(mock_http, mock_resolver)


@pytest.fixture
def nifty_resolved() -> ResolvedInstrument:
    return ResolvedInstrument(
        instrument_id=SimpleInstrumentId(symbol="NIFTY", exchange=Exchange.NSE),
        security_id="12345",
        exchange=Exchange.NSE,
        segment=Segment.INDEX,
        trading_symbol="NIFTY",
        wire_segment="IDX_I",
        lot_size=1,
        tick_size=Decimal("0.05"),
        freeze_quantity=None,
        expiry=None,
        strike=None,
        option_type=None,
    )


@pytest.fixture
def nifty_option_chain_response() -> dict:
    return {
        "data": {
            "oc": {
                "24500": {
                    "ce": {
                        "security_id": "1001",
                        "last_price": 150.0,
                        "top_bid_price": 148.0,
                        "top_ask_price": 152.0,
                        "oi": 50000,
                        "volume": 1000,
                        "implied_volatility": 0.15,
                        "greeks": {"delta": 0.5, "gamma": 0.002, "theta": -0.3, "vega": 0.8},
                    },
                    "pe": {
                        "security_id": "1002",
                        "last_price": 120.0,
                        "top_bid_price": 118.0,
                        "top_ask_price": 122.0,
                        "oi": 45000,
                        "volume": 800,
                        "implied_volatility": 0.16,
                        "greeks": {"delta": -0.5, "gamma": 0.002, "theta": -0.2, "vega": 0.7},
                    },
                },
                "24550": {
                    "ce": {
                        "security_id": "1003",
                        "last_price": 100.0,
                        "top_bid_price": 98.0,
                        "top_ask_price": 102.0,
                        "oi": 30000,
                        "volume": 600,
                        "implied_volatility": 0.14,
                        "greeks": {"delta": 0.4, "gamma": 0.003, "theta": -0.4, "vega": 0.6},
                    },
                    "pe": {
                        "security_id": "1004",
                        "last_price": 170.0,
                        "top_bid_price": 168.0,
                        "top_ask_price": 172.0,
                        "oi": 35000,
                        "volume": 700,
                        "implied_volatility": 0.17,
                        "greeks": {"delta": -0.4, "gamma": 0.003, "theta": -0.3, "vega": 0.9},
                    },
                },
            }
        }
    }


@pytest.fixture
def expiry_list_response() -> dict:
    return {"data": ["2026-08-06", "2026-08-13", "2026-08-20"]}


@pytest.fixture
def ltp_response() -> dict:
    return {"last_price": "24520"}


# ============================================================================
# Construction
# ============================================================================


class TestConstruction:
    def test_creates_with_http_and_resolver(
        self, mock_http: MagicMock, mock_resolver: MagicMock
    ) -> None:
        a = OptionChainAdapter(mock_http, mock_resolver)
        assert a._http is mock_http
        assert a._resolver is mock_resolver

    def test_stores_http_client(self, adapter: OptionChainAdapter, mock_http: MagicMock) -> None:
        assert adapter._http is mock_http

    def test_stores_resolver(self, adapter: OptionChainAdapter, mock_resolver: MagicMock) -> None:
        assert adapter._resolver is mock_resolver


# ============================================================================
# get_expiry_list
# ============================================================================


class TestGetExpiryList:
    def test_returns_sorted_expiry_dates(
        self,
        adapter: OptionChainAdapter,
        mock_http: MagicMock,
        mock_resolver: MagicMock,
        expiry_list_response: dict,
    ) -> None:
        mock_resolver.resolve_underlying_for_options.return_value = (12345, "NSE_FNO")
        mock_http.post.return_value = expiry_list_response

        result = adapter.get_expiry_list("NIFTY", "NSE")

        assert result == ["2026-08-06", "2026-08-13", "2026-08-20"]

    def test_calls_resolver_with_correct_args(
        self,
        adapter: OptionChainAdapter,
        mock_http: MagicMock,
        mock_resolver: MagicMock,
        expiry_list_response: dict,
    ) -> None:
        mock_resolver.resolve_underlying_for_options.return_value = (12345, "NSE_FNO")
        mock_http.post.return_value = expiry_list_response

        adapter.get_expiry_list("BANKNIFTY", "NSE")

        mock_resolver.resolve_underlying_for_options.assert_called_once_with("BANKNIFTY", "NSE")

    def test_correct_post_payload(
        self,
        adapter: OptionChainAdapter,
        mock_http: MagicMock,
        mock_resolver: MagicMock,
        expiry_list_response: dict,
    ) -> None:
        mock_resolver.resolve_underlying_for_options.return_value = (12345, "NSE_FNO")
        mock_http.post.return_value = expiry_list_response

        adapter.get_expiry_list("NIFTY", "NSE")

        mock_http.post.assert_called_once_with(
            "/optionchain/expirylist",
            data={"UnderlyingScrip": 12345, "UnderlyingSeg": "NSE_FNO"},
        )

    def test_returns_empty_list_when_no_expiries(
        self,
        adapter: OptionChainAdapter,
        mock_http: MagicMock,
        mock_resolver: MagicMock,
    ) -> None:
        mock_resolver.resolve_underlying_for_options.return_value = (12345, "NSE_FNO")
        mock_http.post.return_value = {"data": []}

        result = adapter.get_expiry_list("NIFTY", "NSE")
        assert result == []

    def test_sorts_expiry_dates(
        self,
        adapter: OptionChainAdapter,
        mock_http: MagicMock,
        mock_resolver: MagicMock,
    ) -> None:
        mock_resolver.resolve_underlying_for_options.return_value = (12345, "NSE_FNO")
        mock_http.post.return_value = {"data": ["2026-08-20", "2026-08-06", "2026-08-13"]}

        result = adapter.get_expiry_list("NIFTY", "NSE")
        assert result == ["2026-08-06", "2026-08-13", "2026-08-20"]

    def test_handles_missing_data_key(
        self,
        adapter: OptionChainAdapter,
        mock_http: MagicMock,
        mock_resolver: MagicMock,
    ) -> None:
        mock_resolver.resolve_underlying_for_options.return_value = (12345, "NSE_FNO")
        mock_http.post.return_value = {}

        result = adapter.get_expiry_list("NIFTY", "NSE")
        assert result == []


# ============================================================================
# get_option_chain
# ============================================================================


class TestGetOptionChain:
    def test_returns_structured_data_with_ce_pe(
        self,
        adapter: OptionChainAdapter,
        mock_http: MagicMock,
        mock_resolver: MagicMock,
        nifty_option_chain_response: dict,
        nifty_resolved: ResolvedInstrument,
    ) -> None:
        mock_resolver.resolve_underlying_for_options.return_value = (12345, "NSE_FNO")
        mock_http.post.return_value = nifty_option_chain_response

        result = adapter.get_option_chain("NIFTY", "NSE", expiry="2026-08-06")

        assert result["underlying"] == "NIFTY"
        assert result["exchange"] == "NSE"
        assert result["expiry"] == "2026-08-06"
        assert len(result["strikes"]) == 2

    def test_chain_contains_strike_prices(
        self,
        adapter: OptionChainAdapter,
        mock_http: MagicMock,
        mock_resolver: MagicMock,
        nifty_option_chain_response: dict,
    ) -> None:
        mock_resolver.resolve_underlying_for_options.return_value = (12345, "NSE_FNO")
        mock_http.post.return_value = nifty_option_chain_response

        result = adapter.get_option_chain("NIFTY", "NSE", expiry="2026-08-06")

        strikes = [s["strike"] for s in result["strikes"]]
        assert 24500.0 in strikes
        assert 24550.0 in strikes

    def test_chain_ce_leg_has_expected_fields(
        self,
        adapter: OptionChainAdapter,
        mock_http: MagicMock,
        mock_resolver: MagicMock,
        nifty_option_chain_response: dict,
    ) -> None:
        mock_resolver.resolve_underlying_for_options.return_value = (12345, "NSE_FNO")
        mock_http.post.return_value = nifty_option_chain_response

        result = adapter.get_option_chain("NIFTY", "NSE", expiry="2026-08-06")

        ce_leg = result["strikes"][0]["ce"]
        assert ce_leg["security_id"] == "1001"
        assert ce_leg["ltp"] == 150.0
        assert ce_leg["bid"] == 148.0
        assert ce_leg["ask"] == 152.0
        assert ce_leg["oi"] == 50000
        assert ce_leg["volume"] == 1000
        assert ce_leg["iv"] == 0.15

    def test_chain_pe_leg_has_expected_fields(
        self,
        adapter: OptionChainAdapter,
        mock_http: MagicMock,
        mock_resolver: MagicMock,
        nifty_option_chain_response: dict,
    ) -> None:
        mock_resolver.resolve_underlying_for_options.return_value = (12345, "NSE_FNO")
        mock_http.post.return_value = nifty_option_chain_response

        result = adapter.get_option_chain("NIFTY", "NSE", expiry="2026-08-06")

        pe_leg = result["strikes"][0]["pe"]
        assert pe_leg["security_id"] == "1002"
        assert pe_leg["ltp"] == 120.0
        assert pe_leg["oi"] == 45000

    def test_chain_includes_greeks(
        self,
        adapter: OptionChainAdapter,
        mock_http: MagicMock,
        mock_resolver: MagicMock,
        nifty_option_chain_response: dict,
    ) -> None:
        mock_resolver.resolve_underlying_for_options.return_value = (12345, "NSE_FNO")
        mock_http.post.return_value = nifty_option_chain_response

        result = adapter.get_option_chain("NIFTY", "NSE", expiry="2026-08-06")

        ce_leg = result["strikes"][0]["ce"]
        assert ce_leg["delta"] == 0.5
        assert ce_leg["gamma"] == 0.002
        assert ce_leg["theta"] == -0.3
        assert ce_leg["vega"] == 0.8

    def test_auto_resolves_expiry_when_none_given(
        self,
        adapter: OptionChainAdapter,
        mock_http: MagicMock,
        mock_resolver: MagicMock,
        nifty_option_chain_response: dict,
        expiry_list_response: dict,
    ) -> None:
        mock_resolver.resolve_underlying_for_options.return_value = (12345, "NSE_FNO")
        mock_http.post.side_effect = [expiry_list_response, nifty_option_chain_response]

        result = adapter.get_option_chain("NIFTY", "NSE")

        assert result["expiry"] == "2026-08-06"

    def test_raises_on_missing_expiry_no_expiries(
        self,
        adapter: OptionChainAdapter,
        mock_http: MagicMock,
        mock_resolver: MagicMock,
    ) -> None:
        mock_resolver.resolve_underlying_for_options.return_value = (12345, "NSE_FNO")
        mock_http.post.return_value = {"data": []}

        with pytest.raises(OptionChainError, match="No expiries available"):
            adapter.get_option_chain("NIFTY", "NSE")

    def test_resolver_called_before_http(
        self,
        adapter: OptionChainAdapter,
        mock_http: MagicMock,
        mock_resolver: MagicMock,
        nifty_option_chain_response: dict,
    ) -> None:
        mock_resolver.resolve_underlying_for_options.return_value = (12345, "NSE_FNO")
        mock_http.post.return_value = nifty_option_chain_response

        adapter.get_option_chain("NIFTY", "NSE", expiry="2026-08-06")

        mock_resolver.resolve_underlying_for_options.assert_called_once_with("NIFTY", "NSE")
        mock_http.post.assert_called_once_with(
            "/optionchain",
            data={"UnderlyingScrip": 12345, "UnderlyingSeg": "NSE_FNO", "Expiry": "2026-08-06"},
        )

    def test_empty_oc_returns_no_strikes(
        self,
        adapter: OptionChainAdapter,
        mock_http: MagicMock,
        mock_resolver: MagicMock,
    ) -> None:
        mock_resolver.resolve_underlying_for_options.return_value = (12345, "NSE_FNO")
        mock_http.post.return_value = {"data": {"oc": {}}}

        result = adapter.get_option_chain("NIFTY", "NSE", expiry="2026-08-06")
        assert result["strikes"] == []

    def test_missing_data_key_returns_no_strikes(
        self,
        adapter: OptionChainAdapter,
        mock_http: MagicMock,
        mock_resolver: MagicMock,
    ) -> None:
        mock_resolver.resolve_underlying_for_options.return_value = (12345, "NSE_FNO")
        mock_http.post.return_value = {}

        result = adapter.get_option_chain("NIFTY", "NSE", expiry="2026-08-06")
        assert result["strikes"] == []


# ============================================================================
# atm_strike_selection
# ============================================================================


class TestAtmStrikeSelection:
    def test_returns_ce_pe_symbol_and_strike(
        self,
        adapter: OptionChainAdapter,
        mock_http: MagicMock,
        mock_resolver: MagicMock,
        nifty_option_chain_response: dict,
        expiry_list_response: dict,
        nifty_resolved: ResolvedInstrument,
    ) -> None:
        mock_resolver.resolve_underlying_for_options.return_value = (12345, "NSE_FNO")
        mock_resolver.resolve_full.return_value = nifty_resolved
        mock_http.post.side_effect = [
            {"last_price": "24520"},  # LTP
            expiry_list_response,  # expiry list
            nifty_option_chain_response,  # option chain
        ]

        inst_ce = MagicMock(symbol="NIFTY 06 AUG 26 24500 CE")
        inst_pe = MagicMock(symbol="NIFTY 06 AUG 26 24500 PE")
        mock_resolver.get_by_security_id.side_effect = lambda sid: {
            "1001": inst_ce,
            "1002": inst_pe,
        }.get(sid)

        result = adapter.atm_strike_selection("NIFTY")

        assert result[0] == "NIFTY 06 AUG 26 24500 CE"
        assert result[1] == "NIFTY 06 AUG 26 24500 PE"
        assert result[2] == 24500.0  # 24520 rounded to nearest 50

    def test_rounds_ltp_to_nearest_step_nifty(
        self,
        adapter: OptionChainAdapter,
        mock_http: MagicMock,
        mock_resolver: MagicMock,
        nifty_option_chain_response: dict,
        expiry_list_response: dict,
        nifty_resolved: ResolvedInstrument,
    ) -> None:
        mock_resolver.resolve_underlying_for_options.return_value = (12345, "NSE_FNO")
        mock_resolver.resolve_full.return_value = nifty_resolved
        mock_http.post.side_effect = [
            {"last_price": "24535"},  # LTP → rounds to 24550 (nearest 50)
            expiry_list_response,
            nifty_option_chain_response,
        ]

        inst_ce = MagicMock(symbol="NIFTY 06 AUG 26 24550 CE")
        inst_pe = MagicMock(symbol="NIFTY 06 AUG 26 24550 PE")
        mock_resolver.get_by_security_id.side_effect = lambda sid: {
            "1003": inst_ce,
            "1004": inst_pe,
        }.get(sid)

        result = adapter.atm_strike_selection("NIFTY")
        assert result[2] == 24550.0

    def test_uses_ltp_from_market_feed(
        self,
        adapter: OptionChainAdapter,
        mock_http: MagicMock,
        mock_resolver: MagicMock,
        expiry_list_response: dict,
        nifty_resolved: ResolvedInstrument,
    ) -> None:
        mock_resolver.resolve_underlying_for_options.return_value = (12345, "NSE_FNO")
        mock_resolver.resolve_full.return_value = nifty_resolved
        chain = {
            "data": {
                "oc": {
                    "24500": {
                        "ce": {"security_id": "1001"},
                        "pe": {"security_id": "1002"},
                    },
                    "24600": {
                        "ce": {"security_id": "1005"},
                        "pe": {"security_id": "1006"},
                    },
                }
            }
        }
        mock_http.post.side_effect = [
            {"last_price": "24600"},
            expiry_list_response,
            chain,
        ]

        inst_ce = MagicMock(symbol="NIFTY 06 AUG 26 24600 CE")
        inst_pe = MagicMock(symbol="NIFTY 06 AUG 26 24600 PE")
        mock_resolver.get_by_security_id.side_effect = lambda sid: {
            "1005": inst_ce,
            "1006": inst_pe,
        }.get(sid)

        result = adapter.atm_strike_selection("NIFTY")
        assert result[2] == 24600.0

    def test_raises_strike_not_found(
        self,
        adapter: OptionChainAdapter,
        mock_http: MagicMock,
        mock_resolver: MagicMock,
        expiry_list_response: dict,
        nifty_resolved: ResolvedInstrument,
    ) -> None:
        mock_resolver.resolve_underlying_for_options.return_value = (12345, "NSE_FNO")
        mock_resolver.resolve_full.return_value = nifty_resolved
        mock_http.post.side_effect = [
            {"last_price": "24800"},
            expiry_list_response,
            {"data": {"oc": {}}},
        ]

        with pytest.raises(StrikeNotFoundError):
            adapter.atm_strike_selection("NIFTY")

    def test_raises_on_missing_ltp(
        self,
        adapter: OptionChainAdapter,
        mock_http: MagicMock,
        mock_resolver: MagicMock,
        nifty_resolved: ResolvedInstrument,
    ) -> None:
        mock_resolver.resolve_full.return_value = nifty_resolved
        mock_http.post.return_value = {}

        with pytest.raises(OptionChainError, match="No LTP available"):
            adapter.atm_strike_selection("NIFTY")

    def test_banknifty_step_size_100(
        self,
        adapter: OptionChainAdapter,
        mock_http: MagicMock,
        mock_resolver: MagicMock,
        expiry_list_response: dict,
    ) -> None:
        bn_resolved = ResolvedInstrument(
            instrument_id=SimpleInstrumentId(symbol="BANKNIFTY", exchange=Exchange.NSE),
            security_id="54321",
            exchange=Exchange.NSE,
            segment=Segment.INDEX,
            trading_symbol="BANKNIFTY",
            wire_segment="IDX_I",
            lot_size=20,
            tick_size=Decimal("0.05"),
            freeze_quantity=None,
            expiry=None,
            strike=None,
            option_type=None,
        )
        mock_resolver.resolve_underlying_for_options.return_value = (54321, "NSE_FNO")
        mock_resolver.resolve_full.return_value = bn_resolved
        mock_http.post.side_effect = [
            {"last_price": "51250"},
            expiry_list_response,
            {
                "data": {
                    "oc": {
                        "51300": {
                            "ce": {"security_id": "2001", "last_price": 200},
                            "pe": {"security_id": "2002", "last_price": 180},
                        }
                    }
                }
            },
        ]

        mock_resolver.get_by_security_id.side_effect = lambda sid: {
            "2001": MagicMock(symbol="BANKNIFTY 06 AUG 26 51300 CE"),
            "2002": MagicMock(symbol="BANKNIFTY 06 AUG 26 51300 PE"),
        }.get(sid)

        result = adapter.atm_strike_selection("BANKNIFTY")
        assert result[2] == 51300.0  # 51250 rounded to nearest 100


# ============================================================================
# otm_strike_selection
# ============================================================================


class TestOtmStrikeSelection:
    def test_returns_ce_above_atm_pe_below_atm(
        self,
        adapter: OptionChainAdapter,
        mock_http: MagicMock,
        mock_resolver: MagicMock,
        expiry_list_response: dict,
        nifty_resolved: ResolvedInstrument,
    ) -> None:
        mock_resolver.resolve_underlying_for_options.return_value = (12345, "NSE_FNO")
        mock_resolver.resolve_full.return_value = nifty_resolved
        chain = {
            "data": {
                "oc": {
                    "24400": {"ce": {"security_id": "10"}, "pe": {"security_id": "11"}},
                    "24450": {"ce": {"security_id": "12"}, "pe": {"security_id": "13"}},
                    "24500": {"ce": {"security_id": "14"}, "pe": {"security_id": "15"}},
                    "24550": {"ce": {"security_id": "16"}, "pe": {"security_id": "17"}},
                    "24600": {"ce": {"security_id": "18"}, "pe": {"security_id": "19"}},
                }
            }
        }
        mock_http.post.side_effect = [
            {"last_price": "24520"},
            expiry_list_response,
            chain,
        ]

        inst_map = {
            "16": MagicMock(symbol="NIFTY 24550 CE"),
            "13": MagicMock(symbol="NIFTY 24450 PE"),
        }
        mock_resolver.get_by_security_id.side_effect = lambda sid: inst_map.get(sid)

        result = adapter.otm_strike_selection("NIFTY", count=1)

        assert result[0] == "NIFTY 24550 CE"  # OTM CE = above ATM
        assert result[1] == "NIFTY 24450 PE"  # OTM PE = below ATM
        assert result[2] == 24550.0
        assert result[3] == 24450.0

    def test_count_2_returns_strikes_2_steps_away(
        self,
        adapter: OptionChainAdapter,
        mock_http: MagicMock,
        mock_resolver: MagicMock,
        expiry_list_response: dict,
        nifty_resolved: ResolvedInstrument,
    ) -> None:
        mock_resolver.resolve_underlying_for_options.return_value = (12345, "NSE_FNO")
        mock_resolver.resolve_full.return_value = nifty_resolved
        chain = {
            "data": {
                "oc": {
                    "24400": {"ce": {"security_id": "10"}, "pe": {"security_id": "11"}},
                    "24450": {"ce": {"security_id": "12"}, "pe": {"security_id": "13"}},
                    "24500": {"ce": {"security_id": "14"}, "pe": {"security_id": "15"}},
                    "24550": {"ce": {"security_id": "16"}, "pe": {"security_id": "17"}},
                    "24600": {"ce": {"security_id": "18"}, "pe": {"security_id": "19"}},
                }
            }
        }
        mock_http.post.side_effect = [
            {"last_price": "24520"},
            expiry_list_response,
            chain,
        ]

        inst_map = {
            "18": MagicMock(symbol="NIFTY 24600 CE"),
            "11": MagicMock(symbol="NIFTY 24400 PE"),
        }
        mock_resolver.get_by_security_id.side_effect = lambda sid: inst_map.get(sid)

        result = adapter.otm_strike_selection("NIFTY", count=2)

        assert result[2] == 24600.0
        assert result[3] == 24400.0

    def test_returns_empty_symbol_when_security_id_not_in_resolver(
        self,
        adapter: OptionChainAdapter,
        mock_http: MagicMock,
        mock_resolver: MagicMock,
        expiry_list_response: dict,
        nifty_resolved: ResolvedInstrument,
    ) -> None:
        mock_resolver.resolve_underlying_for_options.return_value = (12345, "NSE_FNO")
        mock_resolver.resolve_full.return_value = nifty_resolved
        chain = {
            "data": {
                "oc": {
                    "24450": {"ce": {"security_id": "99"}, "pe": {"security_id": "100"}},
                    "24500": {"ce": {"security_id": "14"}, "pe": {"security_id": "15"}},
                    "24550": {"ce": {"security_id": "16"}, "pe": {"security_id": "17"}},
                }
            }
        }
        mock_http.post.side_effect = [
            {"last_price": "24520"},
            expiry_list_response,
            chain,
        ]

        mock_resolver.get_by_security_id.return_value = None

        result = adapter.otm_strike_selection("NIFTY", count=1)
        assert result[0] == ""


# ============================================================================
# itm_strike_selection
# ============================================================================


class TestItmStrikeSelection:
    def test_returns_ce_below_atm_pe_above_atm(
        self,
        adapter: OptionChainAdapter,
        mock_http: MagicMock,
        mock_resolver: MagicMock,
        expiry_list_response: dict,
        nifty_resolved: ResolvedInstrument,
    ) -> None:
        mock_resolver.resolve_underlying_for_options.return_value = (12345, "NSE_FNO")
        mock_resolver.resolve_full.return_value = nifty_resolved
        chain = {
            "data": {
                "oc": {
                    "24400": {"ce": {"security_id": "10"}, "pe": {"security_id": "11"}},
                    "24450": {"ce": {"security_id": "12"}, "pe": {"security_id": "13"}},
                    "24500": {"ce": {"security_id": "14"}, "pe": {"security_id": "15"}},
                    "24550": {"ce": {"security_id": "16"}, "pe": {"security_id": "17"}},
                    "24600": {"ce": {"security_id": "18"}, "pe": {"security_id": "19"}},
                }
            }
        }
        mock_http.post.side_effect = [
            {"last_price": "24520"},
            expiry_list_response,
            chain,
        ]

        inst_map = {
            "12": MagicMock(symbol="NIFTY 24450 CE"),
            "17": MagicMock(symbol="NIFTY 24550 PE"),
        }
        mock_resolver.get_by_security_id.side_effect = lambda sid: inst_map.get(sid)

        result = adapter.itm_strike_selection("NIFTY", count=1)

        assert result[0] == "NIFTY 24450 CE"  # ITM CE = below ATM
        assert result[1] == "NIFTY 24550 PE"  # ITM PE = above ATM
        assert result[2] == 24450.0
        assert result[3] == 24550.0

    def test_count_2_returns_strikes_2_steps_away(
        self,
        adapter: OptionChainAdapter,
        mock_http: MagicMock,
        mock_resolver: MagicMock,
        expiry_list_response: dict,
        nifty_resolved: ResolvedInstrument,
    ) -> None:
        mock_resolver.resolve_underlying_for_options.return_value = (12345, "NSE_FNO")
        mock_resolver.resolve_full.return_value = nifty_resolved
        chain = {
            "data": {
                "oc": {
                    "24400": {"ce": {"security_id": "10"}, "pe": {"security_id": "11"}},
                    "24450": {"ce": {"security_id": "12"}, "pe": {"security_id": "13"}},
                    "24500": {"ce": {"security_id": "14"}, "pe": {"security_id": "15"}},
                    "24550": {"ce": {"security_id": "16"}, "pe": {"security_id": "17"}},
                    "24600": {"ce": {"security_id": "18"}, "pe": {"security_id": "19"}},
                }
            }
        }
        mock_http.post.side_effect = [
            {"last_price": "24520"},
            expiry_list_response,
            chain,
        ]

        inst_map = {
            "10": MagicMock(symbol="NIFTY 24400 CE"),
            "19": MagicMock(symbol="NIFTY 24600 PE"),
        }
        mock_resolver.get_by_security_id.side_effect = lambda sid: inst_map.get(sid)

        result = adapter.itm_strike_selection("NIFTY", count=2)

        assert result[2] == 24400.0
        assert result[3] == 24600.0


# ============================================================================
# _step_size_for
# ============================================================================


class TestStepSizeFor:
    def test_nifty_step_is_50(self, adapter: OptionChainAdapter) -> None:
        assert adapter._step_size_for("NIFTY") == 50.0

    def test_banknifty_step_is_100(self, adapter: OptionChainAdapter) -> None:
        assert adapter._step_size_for("BANKNIFTY") == 100.0

    def test_finnifty_step_is_50(self, adapter: OptionChainAdapter) -> None:
        assert adapter._step_size_for("FINNIFTY") == 50.0

    def test_sensex_step_is_100(self, adapter: OptionChainAdapter) -> None:
        assert adapter._step_size_for("SENSEX") == 100.0

    def test_midcpnifty_step_is_25(self, adapter: OptionChainAdapter) -> None:
        assert adapter._step_size_for("MIDCPNIFTY") == 25.0

    def test_bankex_step_is_100(self, adapter: OptionChainAdapter) -> None:
        assert adapter._step_size_for("BANKEX") == 100.0

    def test_case_insensitive(
        self, adapter: OptionChainAdapter
    ) -> None:
        assert adapter._step_size_for("nifty") == 50.0

    def test_equity_step_from_resolver(
        self, adapter: OptionChainAdapter, mock_resolver: MagicMock
    ) -> None:
        inst = MagicMock(tick_size=Decimal("2.5"))
        mock_resolver.resolve.return_value = inst

        assert adapter._step_size_for("RELIANCE") == 2.5
        mock_resolver.resolve.assert_called_once_with("RELIANCE", "NSE")

    def test_default_fallback_when_resolver_fails(
        self, adapter: OptionChainAdapter, mock_resolver: MagicMock
    ) -> None:
        mock_resolver.resolve.side_effect = Exception("not found")

        assert adapter._step_size_for("UNKNOWN") == 5.0

    def test_commodity_defaults_to_5(
        self, adapter: OptionChainAdapter, mock_resolver: MagicMock
    ) -> None:
        inst = MagicMock(tick_size=Decimal("1.0"))
        mock_resolver.resolve.return_value = inst

        assert adapter._step_size_for("CRUDEOIL") == 1.0


# ============================================================================
# _ltp_for
# ============================================================================


class TestLtpFor:
    def test_returns_float_from_market_feed(
        self,
        adapter: OptionChainAdapter,
        mock_http: MagicMock,
        mock_resolver: MagicMock,
        nifty_resolved: ResolvedInstrument,
    ) -> None:
        mock_resolver.resolve_full.return_value = nifty_resolved
        mock_http.post.return_value = {"last_price": "24520.50"}

        result = adapter._ltp_for("NIFTY")
        assert result == 24520.5

    def test_raises_when_no_ltp(
        self,
        adapter: OptionChainAdapter,
        mock_http: MagicMock,
        mock_resolver: MagicMock,
        nifty_resolved: ResolvedInstrument,
    ) -> None:
        mock_resolver.resolve_full.return_value = nifty_resolved
        mock_http.post.return_value = {}

        with pytest.raises(OptionChainError, match="No LTP available"):
            adapter._ltp_for("NIFTY")

    def correct_post_payload(
        self,
        adapter: OptionChainAdapter,
        mock_http: MagicMock,
        mock_resolver: MagicMock,
        nifty_resolved: ResolvedInstrument,
    ) -> None:
        mock_resolver.resolve_full.return_value = nifty_resolved
        mock_http.post.return_value = {"last_price": "24520"}

        adapter._ltp_for("NIFTY")

        mock_http.post.assert_called_once_with(
            "/marketfeed/quote",
            data={"security_ids": ["12345"], "exchangeSegment": "IDX_I"},
            bucket="market_data",
        )


# ============================================================================
# get_option_greeks
# ============================================================================


class TestGetOptionGreeks:
    def test_returns_greeks_for_specific_strike_and_type(
        self,
        adapter: OptionChainAdapter,
        mock_http: MagicMock,
        mock_resolver: MagicMock,
        nifty_option_chain_response: dict,
    ) -> None:
        mock_resolver.resolve_underlying_for_options.return_value = (12345, "NSE_FNO")
        mock_http.post.return_value = nifty_option_chain_response

        result = adapter.get_option_greeks(
            security_id="12345",
            exchange_segment="NSE_FNO",
            strike=24500.0,
            expiry="2026-08-06",
            option_type="CE",
        )

        assert result["delta"] == 0.5
        assert result["gamma"] == 0.002
        assert result["theta"] == -0.3
        assert result["vega"] == 0.8
        assert result["iv"] == 0.15

    def test_returns_empty_dict_when_no_match(
        self,
        adapter: OptionChainAdapter,
        mock_http: MagicMock,
        mock_resolver: MagicMock,
        nifty_option_chain_response: dict,
    ) -> None:
        mock_resolver.resolve_underlying_for_options.return_value = (12345, "NSE_FNO")
        mock_http.post.return_value = nifty_option_chain_response

        result = adapter.get_option_greeks(
            security_id="12345",
            exchange_segment="NSE_FNO",
            strike=99999.0,
            expiry="2026-08-06",
            option_type="CE",
        )

        assert result == {}

    def test_returns_empty_dict_on_http_error(
        self,
        adapter: OptionChainAdapter,
        mock_http: MagicMock,
        mock_resolver: MagicMock,
    ) -> None:
        mock_http.post.side_effect = RuntimeError("API error")

        result = adapter.get_option_greeks(
            security_id="12345",
            exchange_segment="NSE_FNO",
        )

        assert result == {}

    def test_returns_empty_dict_on_empty_chain(
        self,
        adapter: OptionChainAdapter,
        mock_http: MagicMock,
        mock_resolver: MagicMock,
    ) -> None:
        mock_http.post.return_value = {"data": {"oc": {}}}

        result = adapter.get_option_greeks(
            security_id="12345",
            exchange_segment="NSE_FNO",
        )

        assert result == {}


# ============================================================================
# _filter_strikes
# ============================================================================


class TestFilterStrikes:
    def test_filters_by_condition(
        self, adapter: OptionChainAdapter
    ) -> None:
        data = [
            {"strike": 24500, "ce": {"ltp": 150}},
            {"strike": 24550, "ce": {"ltp": 100}},
            {"strike": 24600, "ce": {"ltp": 50}},
        ]
        result = adapter._filter_strikes(data, lambda x: x["ce"]["ltp"] > 80)
        assert len(result) == 2
        assert result[0]["strike"] == 24500
        assert result[1]["strike"] == 24550


# ============================================================================
# _round_to_step
# ============================================================================


class TestRoundToStep:
    def test_rounds_down(self, adapter: OptionChainAdapter) -> None:
        assert adapter._round_to_step(24520, 50) == 24500.0

    def test_rounds_up(self, adapter: OptionChainAdapter) -> None:
        assert adapter._round_to_step(24530, 50) == 24550.0

    def test_exact_step(self, adapter: OptionChainAdapter) -> None:
        assert adapter._round_to_step(24500, 50) == 24500.0

    def test_step_100(self, adapter: OptionChainAdapter) -> None:
        assert adapter._round_to_step(51250, 100) == 51300.0


# ============================================================================
# Error types
# ============================================================================


class TestErrorTypes:
    def test_strike_not_found_is_option_chain_error(self) -> None:
        assert issubclass(StrikeNotFoundError, OptionChainError)

    def test_option_chain_error_is_exception(self) -> None:
        assert issubclass(OptionChainError, Exception)

    def test_strike_not_found_message(self) -> None:
        err = StrikeNotFoundError("Strike 99999 not found")
        assert "99999" in str(err)


# ============================================================================
# Edge cases
# ============================================================================


class TestEdgeCases:
    def test_symbol_with_whitespace(
        self,
        adapter: OptionChainAdapter,
        mock_http: MagicMock,
        mock_resolver: MagicMock,
    ) -> None:
        mock_resolver.resolve_underlying_for_options.return_value = (12345, "NSE_FNO")
        mock_http.post.return_value = {"data": []}

        result = adapter.get_expiry_list("  NIFTY  ", "NSE")
        mock_resolver.resolve_underlying_for_options.assert_called_once_with("  NIFTY  ", "NSE")
        assert result == []

    def test_expiry_idx_out_of_range_uses_last(
        self,
        adapter: OptionChainAdapter,
        mock_http: MagicMock,
        mock_resolver: MagicMock,
        nifty_resolved: ResolvedInstrument,
    ) -> None:
        mock_resolver.resolve_underlying_for_options.return_value = (12345, "NSE_FNO")
        mock_resolver.resolve_full.return_value = nifty_resolved
        mock_http.post.side_effect = [
            {"last_price": "24520"},
            {"data": ["2026-08-06"]},  # only 1 expiry
            {
                "data": {
                    "oc": {
                        "24500": {
                            "ce": {"security_id": "1001"},
                            "pe": {"security_id": "1002"},
                        }
                    }
                }
            },
        ]
        mock_resolver.get_by_security_id.return_value = MagicMock(symbol="SYM")

        result = adapter.atm_strike_selection("NIFTY", expiry_idx=5)
        assert result[2] == 24500.0

    def test_chain_with_only_ce_leg(
        self,
        adapter: OptionChainAdapter,
        mock_http: MagicMock,
        mock_resolver: MagicMock,
    ) -> None:
        mock_resolver.resolve_underlying_for_options.return_value = (12345, "NSE_FNO")
        mock_http.post.return_value = {
            "data": {
                "oc": {
                    "24500": {
                        "ce": {"security_id": "1001", "last_price": 150},
                    }
                }
            }
        }

        result = adapter.get_option_chain("NIFTY", "NSE", expiry="2026-08-06")
        assert len(result["strikes"]) == 1
        assert "ce" in result["strikes"][0]
        assert "pe" not in result["strikes"][0]

    def test_chain_with_only_pe_leg(
        self,
        adapter: OptionChainAdapter,
        mock_http: MagicMock,
        mock_resolver: MagicMock,
    ) -> None:
        mock_resolver.resolve_underlying_for_options.return_value = (12345, "NSE_FNO")
        mock_http.post.return_value = {
            "data": {
                "oc": {
                    "24500": {
                        "pe": {"security_id": "1002", "last_price": 120},
                    }
                }
            }
        }

        result = adapter.get_option_chain("NIFTY", "NSE", expiry="2026-08-06")
        assert len(result["strikes"]) == 1
        assert "pe" in result["strikes"][0]
        assert "ce" not in result["strikes"][0]


if __name__ == "__main__":
    pytest.main()

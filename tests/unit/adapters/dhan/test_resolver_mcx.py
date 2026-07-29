"""Comprehensive unit tests for MCX and BSE exchange paths in the Dhan adapter.

Covers:
- MCX: _resolve fallback to near-month futures for CRUDEOIL, GOLD, SILVER, NATURALGAS
- MCX: get_expiry_list, get_option_chain, get_step_size, auto_detect_step_sizes
- BSE: get_expiry_list('SENSEX', 'BSE'), get_step_size, _resolve equity symbols
- Edge cases: invalid symbol, invalid exchange, empty CSV rows
"""

from __future__ import annotations

import csv
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from scalpr.adapters.dhan._option_chain import OptionChainAdapter
from scalpr.adapters.dhan._resolver import (
    COMMODITY_STEP_SIZES,
    INDEX_STEP_SIZES,
    SymbolResolver,
    map_row,
)
from scalpr.adapters.dhan._resolver import DhanInstrumentNotFoundError
from scalpr.domain.instrument import (
    Exchange,
    Instrument,
    OptionType,
    Segment,
)

# ============================================================================
# Helpers — inline CSV fixture builder
# ============================================================================

CSV_COLUMNS = [
    "SEM_EXM_EXCH_ID", "SEM_SEGMENT", "SEM_INSTRUMENT_NAME",
    "SEM_TRADING_SYMBOL", "SEM_SMST_SECURITY_ID", "SEM_LOT_UNITS",
    "SEM_TICK_SIZE", "SEM_EXPIRY_DATE", "SEM_STRIKE_PRICE",
    "SEM_OPTION_TYPE", "SEM_CUSTOM_SYMBOL", "SM_SYMBOL_NAME",
]


def _mcx_future_row(
    underlying: str,
    security_id: str,
    expiry: str,
    symbol: str | None = None,
    lot_size: str = "1",
    tick_size: str = "0.05",
) -> dict[str, str]:
    sym = symbol or f"{underlying}-{expiry.replace('-', '')}-FUT"
    return {
        "SEM_EXM_EXCH_ID": "MCX",
        "SEM_SEGMENT": "M",
        "SEM_INSTRUMENT_NAME": "FUTCOM",
        "SEM_TRADING_SYMBOL": sym,
        "SEM_SMST_SECURITY_ID": security_id,
        "SEM_LOT_UNITS": lot_size,
        "SEM_TICK_SIZE": tick_size,
        "SEM_EXPIRY_DATE": expiry,
        "SEM_STRIKE_PRICE": "",
        "SEM_OPTION_TYPE": "",
        "SEM_CUSTOM_SYMBOL": f"{underlying} {expiry} FUT",
        "SM_SYMBOL_NAME": underlying,
    }


def _mcx_option_row(
    underlying: str,
    security_id: str,
    expiry: str,
    strike: str,
    opt_type: str,
    symbol: str | None = None,
    lot_size: str = "1",
    tick_size: str = "0.05",
) -> dict[str, str]:
    sym = symbol or f"{underlying}-{expiry.replace('-', '')}-{strike}-{opt_type}"
    return {
        "SEM_EXM_EXCH_ID": "MCX",
        "SEM_SEGMENT": "M",
        "SEM_INSTRUMENT_NAME": "OPTCOM",
        "SEM_TRADING_SYMBOL": sym,
        "SEM_SMST_SECURITY_ID": security_id,
        "SEM_LOT_UNITS": lot_size,
        "SEM_TICK_SIZE": tick_size,
        "SEM_EXPIRY_DATE": expiry,
        "SEM_STRIKE_PRICE": strike,
        "SEM_OPTION_TYPE": opt_type,
        "SEM_CUSTOM_SYMBOL": f"{underlying} {expiry} {strike} {opt_type}",
        "SM_SYMBOL_NAME": underlying,
    }


def _bse_equity_row(
    symbol: str,
    security_id: str,
    lot_size: str = "1",
    tick_size: str = "0.05",
) -> dict[str, str]:
    return {
        "SEM_EXM_EXCH_ID": "BSE",
        "SEM_SEGMENT": "E",
        "SEM_INSTRUMENT_NAME": "EQUITY",
        "SEM_TRADING_SYMBOL": f"{symbol}-EQ",
        "SEM_SMST_SECURITY_ID": security_id,
        "SEM_LOT_UNITS": lot_size,
        "SEM_TICK_SIZE": tick_size,
        "SEM_EXPIRY_DATE": "",
        "SEM_STRIKE_PRICE": "",
        "SEM_OPTION_TYPE": "",
        "SEM_CUSTOM_SYMBOL": "",
        "SM_SYMBOL_NAME": "",
    }


def _bse_index_row(
    symbol: str,
    security_id: str,
) -> dict[str, str]:
    return {
        "SEM_EXM_EXCH_ID": "BSE",
        "SEM_SEGMENT": "I",
        "SEM_INSTRUMENT_NAME": "INDEX",
        "SEM_TRADING_SYMBOL": symbol,
        "SEM_SMST_SECURITY_ID": security_id,
        "SEM_LOT_UNITS": "1",
        "SEM_TICK_SIZE": "0.05",
        "SEM_EXPIRY_DATE": "",
        "SEM_STRIKE_PRICE": "",
        "SEM_OPTION_TYPE": "",
        "SEM_CUSTOM_SYMBOL": "",
        "SM_SYMBOL_NAME": "",
    }


def _write_csv(tmp_path: Path, rows: list[dict[str, str]]) -> Path:
    path = tmp_path / "instruments.csv"
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for row in rows:
            full = dict.fromkeys(CSV_COLUMNS, "")
            full.update(row)
            writer.writerow(full)
    return path


# ============================================================================
# Fixtures — MCX instruments
# ============================================================================


@pytest.fixture
def mcx_crudeoil_futures() -> list[dict[str, str]]:
    return [
        _mcx_future_row("CRUDEOIL", "101", "2026-08-19", symbol="CRUDEOIL-19Aug2026-FUT"),
        _mcx_future_row("CRUDEOIL", "102", "2026-09-18", symbol="CRUDEOIL-18Sep2026-FUT"),
    ]


@pytest.fixture
def mcx_gold_futures() -> list[dict[str, str]]:
    return [
        _mcx_future_row("GOLD", "201", "2026-08-05", symbol="GOLD-05Aug2026-FUT"),
        _mcx_future_row("GOLD", "202", "2026-10-05", symbol="GOLD-05Oct2026-FUT"),
    ]


@pytest.fixture
def mcx_silver_futures() -> list[dict[str, str]]:
    return [
        _mcx_future_row("SILVER", "301", "2026-09-05", symbol="SILVER-05Sep2026-FUT"),
        _mcx_future_row("SILVER", "302", "2026-12-05", symbol="SILVER-05Dec2026-FUT"),
    ]


@pytest.fixture
def mcx_naturalgas_futures() -> list[dict[str, str]]:
    return [
        _mcx_future_row("NATURALGAS", "401", "2026-08-26", symbol="NATURALGAS-26Aug2026-FUT"),
        _mcx_future_row("NATURALGAS", "402", "2026-09-25", symbol="NATURALGAS-25Sep2026-FUT"),
    ]


@pytest.fixture
def mcx_all_futures(
    mcx_crudeoil_futures: list[dict[str, str]],
    mcx_gold_futures: list[dict[str, str]],
    mcx_silver_futures: list[dict[str, str]],
    mcx_naturalgas_futures: list[dict[str, str]],
) -> list[dict[str, str]]:
    return mcx_crudeoil_futures + mcx_gold_futures + mcx_silver_futures + mcx_naturalgas_futures


@pytest.fixture
def mcx_option_rows() -> list[dict[str, str]]:
    """OPTCOM rows for auto-detect step sizes."""
    return [
        _mcx_option_row("CRUDEOIL", "501", "2026-08-19", "6000", "CE"),
        _mcx_option_row("CRUDEOIL", "502", "2026-08-19", "6050", "CE"),
        _mcx_option_row("CRUDEOIL", "503", "2026-08-19", "6100", "CE"),
        _mcx_option_row("GOLD", "601", "2026-08-05", "70000", "CE"),
        _mcx_option_row("GOLD", "602", "2026-08-05", "70100", "CE"),
        _mcx_option_row("GOLD", "603", "2026-08-05", "70200", "CE"),
        _mcx_option_row("SILVER", "701", "2026-09-05", "85000", "CE"),
        _mcx_option_row("SILVER", "702", "2026-09-05", "85250", "CE"),
        _mcx_option_row("SILVER", "703", "2026-09-05", "85500", "CE"),
    ]


@pytest.fixture
def bse_equity_rows() -> list[dict[str, str]]:
    return [
        _bse_equity_row("TCS", "801"),
        _bse_equity_row("RELIANCE", "802"),
        _bse_equity_row("INFY", "803"),
    ]


@pytest.fixture
def bse_index_rows() -> list[dict[str, str]]:
    return [
        _bse_index_row("SENSEX", "901"),
        _bse_index_row("BANKEX", "902"),
    ]


# ============================================================================
# Fixtures — mock HTTP & option chain
# ============================================================================


@pytest.fixture
def mock_http() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mcx_chain_response() -> dict:
    return {
        "data": {
            "oc": {
                "6000": {
                    "ce": {
                        "security_id": "501",
                        "last_price": 150.0,
                        "top_bid_price": 148.0,
                        "top_ask_price": 152.0,
                        "oi": 1000,
                        "volume": 200,
                        "implied_volatility": 0.25,
                        "greeks": {"delta": 0.5, "gamma": 0.001, "theta": -0.2, "vega": 0.6},
                    },
                    "pe": {
                        "security_id": "502",
                        "last_price": 120.0,
                        "top_bid_price": 118.0,
                        "top_ask_price": 122.0,
                        "oi": 800,
                        "volume": 150,
                        "implied_volatility": 0.26,
                        "greeks": {"delta": -0.5, "gamma": 0.001, "theta": -0.15, "vega": 0.5},
                    },
                },
                "6050": {
                    "ce": {
                        "security_id": "503",
                        "last_price": 100.0,
                        "top_bid_price": 98.0,
                        "top_ask_price": 102.0,
                        "oi": 500,
                        "volume": 100,
                        "implied_volatility": 0.24,
                        "greeks": {"delta": 0.4, "gamma": 0.002, "theta": -0.3, "vega": 0.7},
                    },
                },
            }
        }
    }


@pytest.fixture
def mcx_expiry_list_response() -> dict:
    return {"data": ["2026-08-19", "2026-09-18", "2026-10-20"]}


@pytest.fixture
def bse_expiry_list_response() -> dict:
    return {"data": ["2026-07-30", "2026-08-27", "2026-09-24"]}


# ============================================================================
# MCX: _resolve fallback to near-month futures
# ============================================================================


class TestMcxResolveFallback:
    """DhanClient._resolve for MCX falls back to nearest futures contract."""

    def _build_resolver_with_futures(self, futures_rows: list[dict[str, str]]) -> SymbolResolver:
        resolver = SymbolResolver()
        resolver.load_from_rows(futures_rows)
        return resolver

    def _resolve(self, resolver: SymbolResolver, symbol: str, exchange: str) -> tuple[str, str]:
        """Simulate DhanClient._resolve logic."""
        from scalpr.adapters.dhan._resolver import DhanInstrumentNotFoundError
        try:
            r = resolver.resolve_full(symbol, exchange)
            return r.security_id, r.wire_segment
        except DhanInstrumentNotFoundError:
            if exchange == "MCX":
                futs = resolver.get_futures_for_underlying(symbol, exchange)
                if futs:
                    r = resolver.resolve_full(futs[0].symbol, exchange)
                    return r.security_id, r.wire_segment
            raise

    def test_crudeoil_falls_back_to_near_month_futures(
        self, mcx_crudeoil_futures: list[dict[str, str]]
    ) -> None:
        resolver = self._build_resolver_with_futures(mcx_crudeoil_futures)
        sid, seg = self._resolve(resolver, "CRUDEOIL", "MCX")
        # Should resolve to near-month: CRUDEOIL-19Aug2026-FUT (security_id "101")
        assert sid == "101"
        assert seg == "MCX_COMM"

    def test_gold_falls_back_to_near_month_futures(
        self, mcx_gold_futures: list[dict[str, str]]
    ) -> None:
        resolver = self._build_resolver_with_futures(mcx_gold_futures)
        sid, seg = self._resolve(resolver, "GOLD", "MCX")
        assert sid == "201"
        assert seg == "MCX_COMM"

    def test_silver_falls_back_to_near_month_futures(
        self, mcx_silver_futures: list[dict[str, str]]
    ) -> None:
        resolver = self._build_resolver_with_futures(mcx_silver_futures)
        sid, seg = self._resolve(resolver, "SILVER", "MCX")
        assert sid == "301"
        assert seg == "MCX_COMM"

    def test_naturalgas_falls_back_to_near_month_futures(
        self, mcx_naturalgas_futures: list[dict[str, str]]
    ) -> None:
        resolver = self._build_resolver_with_futures(mcx_naturalgas_futures)
        sid, seg = self._resolve(resolver, "NATURALGAS", "MCX")
        assert sid == "401"
        assert seg == "MCX_COMM"

    def test_resolve_all_mcx_symbols(
        self, mcx_all_futures: list[dict[str, str]]
    ) -> None:
        resolver = self._build_resolver_with_futures(mcx_all_futures)
        for sym, expected_sid in [
            ("CRUDEOIL", "101"),
            ("GOLD", "201"),
            ("SILVER", "301"),
            ("NATURALGAS", "401"),
        ]:
            sid, seg = self._resolve(resolver, sym, "MCX")
            assert sid == expected_sid, f"{sym} resolved to {sid}, expected {expected_sid}"
            assert seg == "MCX_COMM"

    def test_nearest_expiry_is_first_future(
        self, mcx_crudeoil_futures: list[dict[str, str]]
    ) -> None:
        resolver = self._build_resolver_with_futures(mcx_crudeoil_futures)
        futs = resolver.get_futures_for_underlying("CRUDEOIL", "MCX")
        assert len(futs) == 2
        assert futs[0].security_id == "101"
        assert futs[0].expiry == date(2026, 8, 19)
        assert futs[1].expiry == date(2026, 9, 18)

    def test_get_futures_returns_sorted_by_expiry(
        self, mcx_all_futures: list[dict[str, str]]
    ) -> None:
        resolver = self._build_resolver_with_futures(mcx_all_futures)
        for sym in ["CRUDEOIL", "GOLD", "SILVER", "NATURALGAS"]:
            futs = resolver.get_futures_for_underlying(sym, "MCX")
            assert len(futs) >= 1
            for i in range(len(futs) - 1):
                assert futs[i].expiry <= futs[i + 1].expiry

    def test_fallback_only_for_mcx_not_nse(
        self, mcx_crudeoil_futures: list[dict[str, str]]
    ) -> None:
        resolver = self._build_resolver_with_futures(mcx_crudeoil_futures)
        with pytest.raises(DhanInstrumentNotFoundError):
            self._resolve(resolver, "CRUDEOIL", "NSE")

    def test_fallback_only_for_mcx_not_bse(
        self, mcx_crudeoil_futures: list[dict[str, str]]
    ) -> None:
        resolver = self._build_resolver_with_futures(mcx_crudeoil_futures)
        with pytest.raises(DhanInstrumentNotFoundError):
            self._resolve(resolver, "CRUDEOIL", "BSE")

    def test_no_futures_raises(
        self,
    ) -> None:
        resolver = SymbolResolver()
        with pytest.raises(DhanInstrumentNotFoundError):
            self._resolve(resolver, "CRUDEOIL", "MCX")

    def test_futures_for_underlying_empty_for_unknown(
        self, mcx_crudeoil_futures: list[dict[str, str]]
    ) -> None:
        resolver = self._build_resolver_with_futures(mcx_crudeoil_futures)
        futs = resolver.get_futures_for_underlying("UNKNOWN", "MCX")
        assert futs == []

    def test_wire_segment_is_mcx_comm(
        self, mcx_crudeoil_futures: list[dict[str, str]]
    ) -> None:
        resolver = self._build_resolver_with_futures(mcx_crudeoil_futures)
        _sid, seg = self._resolve(resolver, "CRUDEOIL", "MCX")
        assert seg == "MCX_COMM"

    def test_resolve_full_after_fallback(
        self, mcx_crudeoil_futures: list[dict[str, str]]
    ) -> None:
        resolver = self._build_resolver_with_futures(mcx_crudeoil_futures)
        # Resolve via fallback, then verify resolve_full works on the resolved futures symbol
        r = resolver.resolve_full("CRUDEOIL-19Aug2026-FUT", "MCX")
        assert r.security_id == "101"
        assert r.wire_segment == "MCX_COMM"
        assert r.exchange == Exchange.MCX
        assert r.segment == Segment.FUTURES


# ============================================================================
# MCX: get_expiry_list
# ============================================================================


class TestMcxGetExpiryList:
    def test_returns_sorted_expiries(
        self,
        mock_http: MagicMock,
        mcx_crudeoil_futures: list[dict[str, str]],
        mcx_expiry_list_response: dict,
    ) -> None:
        resolver = SymbolResolver()
        resolver.load_from_rows(mcx_crudeoil_futures)
        adapter = OptionChainAdapter(mock_http, resolver)

        mock_http.post.return_value = mcx_expiry_list_response

        result = adapter.get_expiry_list("CRUDEOIL", "MCX")

        assert result == ["2026-08-19", "2026-09-18", "2026-10-20"]

    def test_resolver_called_with_mcx(
        self,
        mock_http: MagicMock,
        mcx_crudeoil_futures: list[dict[str, str]],
        mcx_expiry_list_response: dict,
    ) -> None:
        resolver = SymbolResolver()
        resolver.load_from_rows(mcx_crudeoil_futures)
        adapter = OptionChainAdapter(mock_http, resolver)

        mock_http.post.return_value = mcx_expiry_list_response
        adapter.get_expiry_list("CRUDEOIL", "MCX")

        # resolve_underlying_for_options should fall back to futures for MCX
        _, seg = resolver.resolve_underlying_for_options("CRUDEOIL", "MCX")
        assert seg == "MCX_COMM"

    def test_expiry_list_post_payload(
        self,
        mock_http: MagicMock,
        mcx_crudeoil_futures: list[dict[str, str]],
        mcx_expiry_list_response: dict,
    ) -> None:
        resolver = SymbolResolver()
        resolver.load_from_rows(mcx_crudeoil_futures)
        adapter = OptionChainAdapter(mock_http, resolver)

        mock_http.post.return_value = mcx_expiry_list_response
        adapter.get_expiry_list("CRUDEOIL", "MCX")

        mock_http.post.assert_called_once()
        call_data = mock_http.post.call_args[1]["data"]
        assert "Expiry" not in call_data  # expiry list has no expiry field
        assert "UnderlyingSeg" in call_data

    def test_empty_expiry_list_mcx(
        self,
        mock_http: MagicMock,
        mcx_crudeoil_futures: list[dict[str, str]],
    ) -> None:
        resolver = SymbolResolver()
        resolver.load_from_rows(mcx_crudeoil_futures)
        adapter = OptionChainAdapter(mock_http, resolver)

        mock_http.post.return_value = {"data": []}
        result = adapter.get_expiry_list("CRUDEOIL", "MCX")
        assert result == []

    def test_gold_expiry_list(
        self,
        mock_http: MagicMock,
        mcx_gold_futures: list[dict[str, str]],
        mcx_expiry_list_response: dict,
    ) -> None:
        resolver = SymbolResolver()
        resolver.load_from_rows(mcx_gold_futures)
        adapter = OptionChainAdapter(mock_http, resolver)

        mock_http.post.return_value = mcx_expiry_list_response
        result = adapter.get_expiry_list("GOLD", "MCX")
        assert result == ["2026-08-19", "2026-09-18", "2026-10-20"]


# ============================================================================
# MCX: get_option_chain
# ============================================================================


class TestMcxGetOptionChain:
    def test_returns_structured_data(
        self,
        mock_http: MagicMock,
        mcx_crudeoil_futures: list[dict[str, str]],
        mcx_chain_response: dict,
    ) -> None:
        resolver = SymbolResolver()
        resolver.load_from_rows(mcx_crudeoil_futures)
        adapter = OptionChainAdapter(mock_http, resolver)

        mock_http.post.return_value = mcx_chain_response

        result = adapter.get_option_chain("CRUDEOIL", "MCX", expiry="2026-08-19")

        assert result["underlying"] == "CRUDEOIL"
        assert result["exchange"] == "MCX"
        assert result["expiry"] == "2026-08-19"
        assert len(result["strikes"]) == 2

    def test_chain_contains_strike_prices(
        self,
        mock_http: MagicMock,
        mcx_crudeoil_futures: list[dict[str, str]],
        mcx_chain_response: dict,
    ) -> None:
        resolver = SymbolResolver()
        resolver.load_from_rows(mcx_crudeoil_futures)
        adapter = OptionChainAdapter(mock_http, resolver)

        mock_http.post.return_value = mcx_chain_response

        result = adapter.get_option_chain("CRUDEOIL", "MCX", expiry="2026-08-19")
        strikes = [s["strike"] for s in result["strikes"]]
        assert 6000.0 in strikes
        assert 6050.0 in strikes

    def test_chain_ce_leg_fields(
        self,
        mock_http: MagicMock,
        mcx_crudeoil_futures: list[dict[str, str]],
        mcx_chain_response: dict,
    ) -> None:
        resolver = SymbolResolver()
        resolver.load_from_rows(mcx_crudeoil_futures)
        adapter = OptionChainAdapter(mock_http, resolver)

        mock_http.post.return_value = mcx_chain_response

        result = adapter.get_option_chain("CRUDEOIL", "MCX", expiry="2026-08-19")
        ce_leg = result["strikes"][0]["ce"]
        assert ce_leg["security_id"] == "501"
        assert ce_leg["ltp"] == 150.0
        assert ce_leg["bid"] == 148.0
        assert ce_leg["oi"] == 1000

    def test_chain_includes_greeks(
        self,
        mock_http: MagicMock,
        mcx_crudeoil_futures: list[dict[str, str]],
        mcx_chain_response: dict,
    ) -> None:
        resolver = SymbolResolver()
        resolver.load_from_rows(mcx_crudeoil_futures)
        adapter = OptionChainAdapter(mock_http, resolver)

        mock_http.post.return_value = mcx_chain_response

        result = adapter.get_option_chain("CRUDEOIL", "MCX", expiry="2026-08-19")
        ce_leg = result["strikes"][0]["ce"]
        assert ce_leg["delta"] == 0.5
        assert ce_leg["gamma"] == 0.001
        assert ce_leg["theta"] == -0.2
        assert ce_leg["vega"] == 0.6

    def test_auto_resolves_expiry_when_none(
        self,
        mock_http: MagicMock,
        mcx_crudeoil_futures: list[dict[str, str]],
        mcx_chain_response: dict,
        mcx_expiry_list_response: dict,
    ) -> None:
        resolver = SymbolResolver()
        resolver.load_from_rows(mcx_crudeoil_futures)
        adapter = OptionChainAdapter(mock_http, resolver)

        mock_http.post.side_effect = [mcx_expiry_list_response, mcx_chain_response]

        result = adapter.get_option_chain("CRUDEOIL", "MCX")
        assert result["expiry"] == "2026-08-19"

    def test_empty_chain_returns_no_strikes(
        self,
        mock_http: MagicMock,
        mcx_crudeoil_futures: list[dict[str, str]],
    ) -> None:
        resolver = SymbolResolver()
        resolver.load_from_rows(mcx_crudeoil_futures)
        adapter = OptionChainAdapter(mock_http, resolver)

        mock_http.post.return_value = {"data": {"oc": {}}}
        result = adapter.get_option_chain("CRUDEOIL", "MCX", expiry="2026-08-19")
        assert result["strikes"] == []

    def test_silver_option_chain(
        self,
        mock_http: MagicMock,
        mcx_silver_futures: list[dict[str, str]],
        mcx_chain_response: dict,
    ) -> None:
        resolver = SymbolResolver()
        resolver.load_from_rows(mcx_silver_futures)
        adapter = OptionChainAdapter(mock_http, resolver)

        mock_http.post.return_value = mcx_chain_response
        result = adapter.get_option_chain("SILVER", "MCX", expiry="2026-09-05")
        assert result["underlying"] == "SILVER"
        assert result["exchange"] == "MCX"

    def test_raises_on_no_expiries(
        self,
        mock_http: MagicMock,
        mcx_crudeoil_futures: list[dict[str, str]],
    ) -> None:
        resolver = SymbolResolver()
        resolver.load_from_rows(mcx_crudeoil_futures)
        adapter = OptionChainAdapter(mock_http, resolver)

        mock_http.post.return_value = {"data": []}
        from scalpr.adapters.dhan._option_chain import OptionChainError
        with pytest.raises(OptionChainError, match="No expiries available"):
            adapter.get_option_chain("CRUDEOIL", "MCX")


# ============================================================================
# MCX: get_step_size
# ============================================================================


class TestMcxGetStepSize:
    def setup_method(self) -> None:
        self.resolver = SymbolResolver()

    def test_crudeoil_step_50(self) -> None:
        assert self.resolver.get_step_size("CRUDEOIL") == 50.0

    def test_gold_step_100(self) -> None:
        assert self.resolver.get_step_size("GOLD") == 100.0

    def test_silver_step_250(self) -> None:
        assert self.resolver.get_step_size("SILVER") == 250.0

    def test_naturalgas_step_5(self) -> None:
        assert self.resolver.get_step_size("NATURALGAS") == 5.0

    def test_aluminium_step_5(self) -> None:
        assert self.resolver.get_step_size("ALUMINIUM") == 5.0

    def test_copper_step_5(self) -> None:
        assert self.resolver.get_step_size("COPPER") == 5.0

    def test_cotton_step_10(self) -> None:
        assert self.resolver.get_step_size("COTTON") == 10.0

    def test_nickel_step_10(self) -> None:
        assert self.resolver.get_step_size("NICKEL") == 10.0

    def test_zinc_step_5(self) -> None:
        assert self.resolver.get_step_size("ZINC") == 5.0

    def test_lead_step_5(self) -> None:
        assert self.resolver.get_step_size("LEAD") == 5.0

    def test_all_commodities_have_positive_step(self) -> None:
        for sym in COMMODITY_STEP_SIZES:
            step = self.resolver.get_step_size(sym)
            assert step > 0, f"{sym} has non-positive step {step}"

    def test_case_insensitive_mcx(self) -> None:
        assert self.resolver.get_step_size("crudeoil") == 50.0
        assert self.resolver.get_step_size("Gold") == 100.0
        assert self.resolver.get_step_size("NATURALGAS") == 5.0

    def test_commodity_precedence_over_fallback(self) -> None:
        assert self.resolver.get_step_size("GOLD") == 100.0
        assert self.resolver.get_step_size("CRUDEOIL") == 50.0


# ============================================================================
# MCX: auto_detect_step_sizes
# ============================================================================


class TestMcxAutoDetectStepSizes:
    def test_detects_crudeoil_step_from_options(
        self, tmp_path: Path, mcx_option_rows: list[dict[str, str]]
    ) -> None:
        csv_path = _write_csv(tmp_path, mcx_option_rows)
        resolver = SymbolResolver()
        result = resolver.auto_detect_step_sizes(csv_path)
        assert result["CRUDEOIL"] == 50.0
        assert result["GOLD"] == 100.0
        assert result["SILVER"] == 250.0

    def test_detects_only_option_commodity_rows(
        self, tmp_path: Path, mcx_all_futures: list[dict[str, str]]
    ) -> None:
        csv_path = _write_csv(tmp_path, mcx_all_futures)
        resolver = SymbolResolver()
        result = resolver.auto_detect_step_sizes(csv_path)
        # No OPTCOM rows — should be empty
        assert result == {}

    def test_mcx_option_uses_nearest_expiry(
        self, tmp_path: Path,
    ) -> None:
        rows = [
            _mcx_option_row("GOLD", "601", "2026-08-05", "70000", "CE"),
            _mcx_option_row("GOLD", "602", "2026-08-05", "70100", "CE"),
            _mcx_option_row("GOLD", "603", "2026-08-05", "70200", "CE"),
            _mcx_option_row("GOLD", "604", "2026-09-05", "71050", "CE"),  # far expiry, diff step
            _mcx_option_row("GOLD", "605", "2026-09-05", "71150", "CE"),
        ]
        csv_path = _write_csv(tmp_path, rows)
        resolver = SymbolResolver()
        result = resolver.auto_detect_step_sizes(csv_path)
        assert result["GOLD"] == 100.0  # nearest expiry dominates

    def test_silver_step_250_detected(
        self, tmp_path: Path,
    ) -> None:
        rows = [
            _mcx_option_row("SILVER", "701", "2026-09-05", "85000", "CE"),
            _mcx_option_row("SILVER", "702", "2026-09-05", "85250", "CE"),
            _mcx_option_row("SILVER", "703", "2026-09-05", "85500", "CE"),
        ]
        csv_path = _write_csv(tmp_path, rows)
        resolver = SymbolResolver()
        result = resolver.auto_detect_step_sizes(csv_path)
        assert result["SILVER"] == 250.0


# ============================================================================
# BSE Exchange
# ============================================================================


class TestBseExchange:
    def test_bse_get_expiry_list_sensex(
        self,
        mock_http: MagicMock,
        bse_index_rows: list[dict[str, str]],
        bse_expiry_list_response: dict,
    ) -> None:
        resolver = SymbolResolver()
        resolver.load_from_rows(bse_index_rows)
        adapter = OptionChainAdapter(mock_http, resolver)

        mock_http.post.return_value = bse_expiry_list_response
        result = adapter.get_expiry_list("SENSEX", "BSE")
        assert result == ["2026-07-30", "2026-08-27", "2026-09-24"]

    def test_bse_get_expiry_list_bankex(
        self,
        mock_http: MagicMock,
        bse_index_rows: list[dict[str, str]],
        bse_expiry_list_response: dict,
    ) -> None:
        resolver = SymbolResolver()
        resolver.load_from_rows(bse_index_rows)
        adapter = OptionChainAdapter(mock_http, resolver)

        mock_http.post.return_value = bse_expiry_list_response
        result = adapter.get_expiry_list("BANKEX", "BSE")
        assert result == ["2026-07-30", "2026-08-27", "2026-09-24"]

    def test_bse_sensex_step_size_100(self) -> None:
        resolver = SymbolResolver()
        assert resolver.get_step_size("SENSEX") == 100.0

    def test_bse_bankex_step_size_100(self) -> None:
        resolver = SymbolResolver()
        assert resolver.get_step_size("BANKEX") == 100.0

    def test_bse_step_sizes_in_index_sizes(self) -> None:
        assert "SENSEX" in INDEX_STEP_SIZES
        assert "BANKEX" in INDEX_STEP_SIZES
        assert INDEX_STEP_SIZES["SENSEX"] == 100.0
        assert INDEX_STEP_SIZES["BANKEX"] == 100.0

    def test_bse_resolve_equity_symbol(
        self, bse_equity_rows: list[dict[str, str]]
    ) -> None:
        resolver = SymbolResolver()
        resolver.load_from_rows(bse_equity_rows)
        inst = resolver.resolve("TCS", "BSE")
        assert inst.security_id == "801"
        assert inst.exchange == Exchange.BSE
        assert inst.segment == Segment.EQUITY

    def test_bse_resolve_full_equity(
        self, bse_equity_rows: list[dict[str, str]]
    ) -> None:
        resolver = SymbolResolver()
        resolver.load_from_rows(bse_equity_rows)
        r = resolver.resolve_full("TCS", "BSE")
        assert r.security_id == "801"
        assert r.wire_segment == "BSE_EQ"
        assert r.exchange == Exchange.BSE
        assert r.segment == Segment.EQUITY

    def test_bse_resolve_multiple_equities(
        self, bse_equity_rows: list[dict[str, str]]
    ) -> None:
        resolver = SymbolResolver()
        resolver.load_from_rows(bse_equity_rows)
        for sym, expected_sid in [("TCS", "801"), ("RELIANCE", "802"), ("INFY", "803")]:
            inst = resolver.resolve(sym, "BSE")
            assert inst.security_id == expected_sid
            assert inst.exchange == Exchange.BSE

    def test_bse_resolve_unknown_symbol_raises(
        self, bse_equity_rows: list[dict[str, str]]
    ) -> None:
        resolver = SymbolResolver()
        resolver.load_from_rows(bse_equity_rows)
        with pytest.raises(DhanInstrumentNotFoundError):
            resolver.resolve("UNKNOWN", "BSE")

    def test_bse_sensex_resolve_underlying_for_options(
        self,
        mock_http: MagicMock,
        bse_index_rows: list[dict[str, str]],
    ) -> None:
        resolver = SymbolResolver()
        resolver.load_from_rows(bse_index_rows)
        OptionChainAdapter(mock_http, resolver)

        sid, seg = resolver.resolve_underlying_for_options("SENSEX", "BSE")
        assert sid == 901
        assert seg == "IDX_I"

    def test_bse_bankex_resolve_underlying_for_options(
        self,
        mock_http: MagicMock,
        bse_index_rows: list[dict[str, str]],
    ) -> None:
        resolver = SymbolResolver()
        resolver.load_from_rows(bse_index_rows)
        OptionChainAdapter(mock_http, resolver)

        sid, seg = resolver.resolve_underlying_for_options("BANKEX", "BSE")
        assert sid == 902
        assert seg == "IDX_I"

    def test_bse_sensex_expiry_list_post_payload(
        self,
        mock_http: MagicMock,
        bse_index_rows: list[dict[str, str]],
        bse_expiry_list_response: dict,
    ) -> None:
        resolver = SymbolResolver()
        resolver.load_from_rows(bse_index_rows)
        adapter = OptionChainAdapter(mock_http, resolver)

        mock_http.post.return_value = bse_expiry_list_response
        adapter.get_expiry_list("SENSEX", "BSE")

        mock_http.post.assert_called_once_with(
            "/optionchain/expirylist",
            data={"UnderlyingScrip": 901, "UnderlyingSeg": "IDX_I"},
        )

    def test_bse_empty_expiry_list(
        self,
        mock_http: MagicMock,
        bse_index_rows: list[dict[str, str]],
    ) -> None:
        resolver = SymbolResolver()
        resolver.load_from_rows(bse_index_rows)
        adapter = OptionChainAdapter(mock_http, resolver)

        mock_http.post.return_value = {"data": []}
        result = adapter.get_expiry_list("SENSEX", "BSE")
        assert result == []


# ============================================================================
# BSE: _resolve fallback (no fallback for BSE — direct lookup)
# ============================================================================


class TestBseResolve:
    def _resolve(self, resolver: SymbolResolver, symbol: str, exchange: str) -> tuple[str, str]:
        from scalpr.adapters.dhan._resolver import DhanInstrumentNotFoundError
        try:
            r = resolver.resolve_full(symbol, exchange)
            return r.security_id, r.wire_segment
        except DhanInstrumentNotFoundError:
            # BSE has no commodity fallback — re-raise
            raise

    def test_resolve_bse_equity_direct(
        self, bse_equity_rows: list[dict[str, str]]
    ) -> None:
        resolver = SymbolResolver()
        resolver.load_from_rows(bse_equity_rows)
        sid, seg = self._resolve(resolver, "TCS", "BSE")
        assert sid == "801"
        assert seg == "BSE_EQ"

    def test_resolve_bse_index_direct(
        self, bse_index_rows: list[dict[str, str]]
    ) -> None:
        resolver = SymbolResolver()
        resolver.load_from_rows(bse_index_rows)
        sid, seg = self._resolve(resolver, "SENSEX", "BSE")
        assert sid == "901"
        assert seg == "IDX_I"

    def test_bse_no_fallback_for_unknown(
        self,
    ) -> None:
        resolver = SymbolResolver()
        with pytest.raises(DhanInstrumentNotFoundError):
            self._resolve(resolver, "SENSEX", "BSE")

    def test_bse_equity_wire_segment(
        self, bse_equity_rows: list[dict[str, str]]
    ) -> None:
        resolver = SymbolResolver()
        resolver.load_from_rows(bse_equity_rows)
        resolver.resolve("TCS", "BSE")
        seg = resolver.wire_segment_of("TCS", "BSE")
        assert seg == "BSE_EQ"

    def test_bse_fno_not_applicable(
        self, bse_equity_rows: list[dict[str, str]]
    ) -> None:
        resolver = SymbolResolver()
        resolver.load_from_rows(bse_equity_rows)
        # BSE equity should not give FNO segment
        seg = resolver.wire_segment_of("TCS", "BSE")
        assert seg != "BSE_FNO"


# ============================================================================
# Edge cases: invalid symbol, invalid exchange, empty CSV
# ============================================================================


class TestEdgeCases:
    def test_invalid_symbol_on_mcx(
        self, mcx_crudeoil_futures: list[dict[str, str]]
    ) -> None:
        resolver = SymbolResolver()
        resolver.load_from_rows(mcx_crudeoil_futures)
        with pytest.raises(DhanInstrumentNotFoundError):
            resolver.resolve("ZZZZZZ", "MCX")

    def test_invalid_symbol_on_bse(
        self, bse_equity_rows: list[dict[str, str]]
    ) -> None:
        resolver = SymbolResolver()
        resolver.load_from_rows(bse_equity_rows)
        with pytest.raises(DhanInstrumentNotFoundError):
            resolver.resolve("ZZZZZZ", "BSE")

    def test_invalid_exchange_raises(
        self, mcx_crudeoil_futures: list[dict[str, str]]
    ) -> None:
        resolver = SymbolResolver()
        resolver.load_from_rows(mcx_crudeoil_futures)
        with pytest.raises(Exception):
            resolver.resolve("CRUDEOIL", "INVALID_EXCHANGE")

    def test_empty_csv_rows_returns_empty(self) -> None:
        resolver = SymbolResolver()
        result = resolver.load_from_rows([])
        assert result["total"] == 0
        assert resolver.stats()["loaded"] is True

    def test_empty_csv_no_instruments_found(self) -> None:
        resolver = SymbolResolver()
        resolver.load_from_rows([])
        with pytest.raises(DhanInstrumentNotFoundError):
            resolver.resolve("ANYTHING", "MCX")

    def test_no_futures_for_mcx_underlying_returns_empty_list(
        self, mcx_crudeoil_futures: list[dict[str, str]]
    ) -> None:
        resolver = SymbolResolver()
        resolver.load_from_rows(mcx_crudeoil_futures)
        futs = resolver.get_futures_for_underlying("UNKNOWN", "MCX")
        assert futs == []

    def test_mcx_resolve_with_different_exchange_strings(self) -> None:
        resolver = SymbolResolver()
        row = _mcx_future_row("CRUDEOIL", "101", "2026-08-19")
        resolver.load_from_rows([row])

        r = resolver.resolve_full("CRUDEOIL-20260819-FUT", "MCX")
        assert r.security_id == "101"

    def test_bse_equity_symbol_normalization(
        self, bse_equity_rows: list[dict[str, str]]
    ) -> None:
        resolver = SymbolResolver()
        resolver.load_from_rows(bse_equity_rows)
        # Equity rows have -EQ suffix stripped
        inst = resolver.resolve("TCS", "BSE")
        assert inst.symbol == "TCS"  # -EQ stripped

    def test_step_size_unknown_commodity_returns_1(self) -> None:
        resolver = SymbolResolver()
        assert resolver.get_step_size("UNKNOWN_COMMODITY") == 1.0

    def test_resolver_stats_after_loading(
        self, mcx_all_futures: list[dict[str, str]]
    ) -> None:
        resolver = SymbolResolver()
        resolver.load_from_rows(mcx_all_futures)
        stats = resolver.stats()
        assert stats["loaded"] is True
        assert stats["total"] == 8  # 4 commodities × 2 futures each

    def test_all_instruments_returns_list(
        self, mcx_all_futures: list[dict[str, str]]
    ) -> None:
        resolver = SymbolResolver()
        resolver.load_from_rows(mcx_all_futures)
        all_inst = resolver.all_instruments()
        assert len(all_inst) == 8
        for inst in all_inst:
            assert isinstance(inst, Instrument)

    def test_get_by_symbol_returns_none_for_missing(
        self, mcx_crudeoil_futures: list[dict[str, str]]
    ) -> None:
        resolver = SymbolResolver()
        resolver.load_from_rows(mcx_crudeoil_futures)
        result = resolver.get_by_symbol("ZZZZZZ", "MCX")
        assert result is None

    def test_get_by_security_id(
        self, mcx_crudeoil_futures: list[dict[str, str]]
    ) -> None:
        resolver = SymbolResolver()
        resolver.load_from_rows(mcx_crudeoil_futures)
        inst = resolver.get_by_security_id("101")
        assert inst is not None
        assert inst.security_id == "101"

    def test_get_by_security_id_missing(
        self, mcx_crudeoil_futures: list[dict[str, str]]
    ) -> None:
        resolver = SymbolResolver()
        resolver.load_from_rows(mcx_crudeoil_futures)
        result = resolver.get_by_security_id("99999")
        assert result is None

    def test_get_lot_size_on_future(
        self, mcx_crudeoil_futures: list[dict[str, str]]
    ) -> None:
        resolver = SymbolResolver()
        resolver.load_from_rows(mcx_crudeoil_futures)
        ls = resolver.get_lot_size("CRUDEOIL-19Aug2026-FUT", "MCX")
        assert ls == 1

    def test_instrument_kind_of_mcx_future(
        self, mcx_crudeoil_futures: list[dict[str, str]]
    ) -> None:
        resolver = SymbolResolver()
        resolver.load_from_rows(mcx_crudeoil_futures)
        kind = resolver.instrument_kind_of("CRUDEOIL-19Aug2026-FUT", "MCX")
        assert kind == "FUTCOM"

    def test_wire_segment_of(
        self, mcx_crudeoil_futures: list[dict[str, str]]
    ) -> None:
        resolver = SymbolResolver()
        resolver.load_from_rows(mcx_crudeoil_futures)
        seg = resolver.wire_segment_of("CRUDEOIL-19Aug2026-FUT", "MCX")
        assert seg == "MCX_COMM"


# ============================================================================
# MCX: map_row validation
# ============================================================================


class TestMcxMapRow:
    def test_maps_future_row(self) -> None:
        row = _mcx_future_row("CRUDEOIL", "101", "2026-08-19")
        mapped = map_row(row)
        assert mapped is not None
        inst = mapped.instrument
        assert inst.symbol == "CRUDEOIL-20260819-FUT"
        assert inst.exchange == Exchange.MCX
        assert inst.segment == Segment.FUTURES
        assert inst.security_id == "101"
        assert mapped.wire_segment == "MCX_COMM"
        assert mapped.underlying == "CRUDEOIL"

    def test_maps_option_row(self) -> None:
        row = _mcx_option_row("CRUDEOIL", "501", "2026-08-19", "6000", "CE")
        mapped = map_row(row)
        assert mapped is not None
        inst = mapped.instrument
        assert inst.exchange == Exchange.MCX
        assert inst.segment == Segment.OPTIONS
        assert inst.option_type == OptionType.CE
        assert inst.strike == Decimal("6000")
        assert mapped.underlying == "CRUDEOIL"

    def test_maps_option_row_pe(self) -> None:
        row = _mcx_option_row("CRUDEOIL", "502", "2026-08-19", "6000", "PE")
        mapped = map_row(row)
        assert mapped is not None
        assert mapped.instrument.option_type == OptionType.PE
        assert mapped.instrument.strike == Decimal("6000")

    def test_gold_future_map(self) -> None:
        row = _mcx_future_row("GOLD", "201", "2026-08-05")
        mapped = map_row(row)
        assert mapped is not None
        assert mapped.instrument.exchange == Exchange.MCX
        assert mapped.instrument.segment == Segment.FUTURES

    def test_naturalgas_future_map(self) -> None:
        row = _mcx_future_row("NATURALGAS", "401", "2026-08-26")
        mapped = map_row(row)
        assert mapped is not None
        assert mapped.instrument.exchange == Exchange.MCX
        assert mapped.instrument.segment == Segment.FUTURES

    def test_skips_row_without_symbol(self) -> None:
        row = _mcx_future_row("CRUDEOIL", "101", "2026-08-19")
        row["SEM_TRADING_SYMBOL"] = ""
        mapped = map_row(row)
        assert mapped is None

    def test_skips_row_without_security_id(self) -> None:
        row = _mcx_future_row("CRUDEOIL", "", "2026-08-19")
        mapped = map_row(row)
        assert mapped is None

    def test_skips_unknown_instrument_name(self) -> None:
        row = _mcx_future_row("CRUDEOIL", "101", "2026-08-19")
        row["SEM_INSTRUMENT_NAME"] = "UNKNOWN"
        mapped = map_row(row)
        assert mapped is None

    def test_mcx_future_lot_size(self) -> None:
        row = _mcx_future_row("CRUDEOIL", "101", "2026-08-19", lot_size="10")
        mapped = map_row(row)
        assert mapped is not None
        assert mapped.instrument.lot_size == 10

    def test_mcx_option_tick_size(self) -> None:
        row = _mcx_option_row("CRUDEOIL", "501", "2026-08-19", "6000", "CE", tick_size="0.10")
        mapped = map_row(row)
        assert mapped is not None
        assert mapped.instrument.tick_size == Decimal("0.10")

    def test_mcx_future_has_no_option_type(self) -> None:
        row = _mcx_future_row("CRUDEOIL", "101", "2026-08-19")
        mapped = map_row(row)
        assert mapped is not None
        assert mapped.instrument.option_type is None
        assert mapped.instrument.strike is None

    def test_mcx_option_has_expiry(self) -> None:
        row = _mcx_option_row("CRUDEOIL", "501", "2026-08-19", "6000", "CE")
        mapped = map_row(row)
        assert mapped is not None
        assert mapped.instrument.expiry == date(2026, 8, 19)

    def test_mcx_future_has_expiry(self) -> None:
        row = _mcx_future_row("CRUDEOIL", "101", "2026-08-19")
        mapped = map_row(row)
        assert mapped is not None
        assert mapped.instrument.expiry == date(2026, 8, 19)


# ============================================================================
# BSE: map_row validation
# ============================================================================


class TestBseMapRow:
    def test_maps_equity_row(self) -> None:
        row = _bse_equity_row("TCS", "801")
        mapped = map_row(row)
        assert mapped is not None
        inst = mapped.instrument
        assert inst.symbol == "TCS"  # -EQ stripped
        assert inst.exchange == Exchange.BSE
        assert inst.segment == Segment.EQUITY
        assert inst.security_id == "801"
        assert mapped.wire_segment == "BSE_EQ"

    def test_maps_bse_index_row(self) -> None:
        row = _bse_index_row("SENSEX", "901")
        mapped = map_row(row)
        assert mapped is not None
        inst = mapped.instrument
        assert inst.symbol == "SENSEX"
        assert inst.exchange == Exchange.BSE
        assert inst.segment == Segment.EQUITY  # INDEX -> EQUITY segment
        assert mapped.wire_segment == "IDX_I"

    def test_bse_equity_lot_size(self) -> None:
        row = _bse_equity_row("TCS", "801", lot_size="5")
        mapped = map_row(row)
        assert mapped is not None
        assert mapped.instrument.lot_size == 5

    def test_bse_equity_tick_size(self) -> None:
        row = _bse_equity_row("TCS", "801", tick_size="0.25")
        mapped = map_row(row)
        assert mapped is not None
        assert mapped.instrument.tick_size == Decimal("0.25")

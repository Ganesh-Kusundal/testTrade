"""Tests for automatic option step size detection in SymbolResolver."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from scalpr.adapters.dhan._resolver import (
    COMMODITY_STEP_SIZES,
    INDEX_STEP_SIZES,
    SymbolResolver,
)

# ============================================================================
# Helpers
# ============================================================================

SAMPLE_COLUMNS = [
    "SEM_EXM_EXCH_ID", "SEM_SEGMENT", "SEM_INSTRUMENT_NAME",
    "SEM_CUSTOM_SYMBOL", "SEM_STRIKE_PRICE", "SEM_EXPIRY_DATE",
    "SEM_TRADING_SYMBOL", "SEM_SMST_SECURITY_ID", "SEM_LOT_UNITS",
    "SEM_TICK_SIZE", "SEM_OPTION_TYPE", "SM_SYMBOL_NAME",
]


def _write_csv(tmp_path: Path, rows: list[dict[str, str]]) -> Path:
    path = tmp_path / "instruments.csv"
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=SAMPLE_COLUMNS)
        writer.writeheader()
        for row in rows:
            # Ensure all columns present
            full = dict.fromkeys(SAMPLE_COLUMNS, "")
            full.update(row)
            writer.writerow(full)
    return path


# ============================================================================
# auto_detect_step_sizes
# ============================================================================


class TestAutoDetectStepSizes:
    def test_detects_nifty_step_50(self, tmp_path: Path) -> None:
        rows = [
            {
                "SEM_EXM_EXCH_ID": "NSE", "SEM_SEGMENT": "D",
                "SEM_INSTRUMENT_NAME": "OPTIDX",
                "SEM_CUSTOM_SYMBOL": "NIFTY 06 AUG 26 24500 CE",
                "SEM_STRIKE_PRICE": "24500", "SEM_EXPIRY_DATE": "2026-08-06",
                "SEM_OPTION_TYPE": "CE", "SM_SYMBOL_NAME": "NIFTY",
            },
            {
                "SEM_EXM_EXCH_ID": "NSE", "SEM_SEGMENT": "D",
                "SEM_INSTRUMENT_NAME": "OPTIDX",
                "SEM_CUSTOM_SYMBOL": "NIFTY 06 AUG 26 24550 CE",
                "SEM_STRIKE_PRICE": "24550", "SEM_EXPIRY_DATE": "2026-08-06",
                "SEM_OPTION_TYPE": "CE", "SM_SYMBOL_NAME": "NIFTY",
            },
            {
                "SEM_EXM_EXCH_ID": "NSE", "SEM_SEGMENT": "D",
                "SEM_INSTRUMENT_NAME": "OPTIDX",
                "SEM_CUSTOM_SYMBOL": "NIFTY 06 AUG 26 24600 CE",
                "SEM_STRIKE_PRICE": "24600", "SEM_EXPIRY_DATE": "2026-08-06",
                "SEM_OPTION_TYPE": "CE", "SM_SYMBOL_NAME": "NIFTY",
            },
        ]
        csv_path = _write_csv(tmp_path, rows)
        resolver = SymbolResolver()
        result = resolver.auto_detect_step_sizes(csv_path)
        assert result == {"NIFTY": 50.0}

    def test_detects_banknifty_step_100(self, tmp_path: Path) -> None:
        rows = [
            {
                "SEM_EXM_EXCH_ID": "NSE", "SEM_SEGMENT": "D",
                "SEM_INSTRUMENT_NAME": "OPTIDX",
                "SEM_CUSTOM_SYMBOL": "BANKNIFTY 06 AUG 26 51000 CE",
                "SEM_STRIKE_PRICE": "51000", "SEM_EXPIRY_DATE": "2026-08-06",
                "SEM_OPTION_TYPE": "CE", "SM_SYMBOL_NAME": "BANKNIFTY",
            },
            {
                "SEM_EXM_EXCH_ID": "NSE", "SEM_SEGMENT": "D",
                "SEM_INSTRUMENT_NAME": "OPTIDX",
                "SEM_CUSTOM_SYMBOL": "BANKNIFTY 06 AUG 26 51100 CE",
                "SEM_STRIKE_PRICE": "51100", "SEM_EXPIRY_DATE": "2026-08-06",
                "SEM_OPTION_TYPE": "CE", "SM_SYMBOL_NAME": "BANKNIFTY",
            },
            {
                "SEM_EXM_EXCH_ID": "NSE", "SEM_SEGMENT": "D",
                "SEM_INSTRUMENT_NAME": "OPTIDX",
                "SEM_CUSTOM_SYMBOL": "BANKNIFTY 06 AUG 26 51200 CE",
                "SEM_STRIKE_PRICE": "51200", "SEM_EXPIRY_DATE": "2026-08-06",
                "SEM_OPTION_TYPE": "CE", "SM_SYMBOL_NAME": "BANKNIFTY",
            },
        ]
        csv_path = _write_csv(tmp_path, rows)
        resolver = SymbolResolver()
        result = resolver.auto_detect_step_sizes(csv_path)
        assert result == {"BANKNIFTY": 100.0}

    def test_detects_stock_step_25(self, tmp_path: Path) -> None:
        rows = [
            {
                "SEM_EXM_EXCH_ID": "NSE", "SEM_SEGMENT": "D",
                "SEM_INSTRUMENT_NAME": "OPTSTK",
                "SEM_CUSTOM_SYMBOL": "RELIANCE 06 AUG 26 2500 CE",
                "SEM_STRIKE_PRICE": "2500", "SEM_EXPIRY_DATE": "2026-08-06",
                "SEM_OPTION_TYPE": "CE", "SM_SYMBOL_NAME": "RELIANCE",
            },
            {
                "SEM_EXM_EXCH_ID": "NSE", "SEM_SEGMENT": "D",
                "SEM_INSTRUMENT_NAME": "OPTSTK",
                "SEM_CUSTOM_SYMBOL": "RELIANCE 06 AUG 26 2525 CE",
                "SEM_STRIKE_PRICE": "2525", "SEM_EXPIRY_DATE": "2026-08-06",
                "SEM_OPTION_TYPE": "CE", "SM_SYMBOL_NAME": "RELIANCE",
            },
            {
                "SEM_EXM_EXCH_ID": "NSE", "SEM_SEGMENT": "D",
                "SEM_INSTRUMENT_NAME": "OPTSTK",
                "SEM_CUSTOM_SYMBOL": "RELIANCE 06 AUG 26 2550 CE",
                "SEM_STRIKE_PRICE": "2550", "SEM_EXPIRY_DATE": "2026-08-06",
                "SEM_OPTION_TYPE": "CE", "SM_SYMBOL_NAME": "RELIANCE",
            },
        ]
        csv_path = _write_csv(tmp_path, rows)
        resolver = SymbolResolver()
        result = resolver.auto_detect_step_sizes(csv_path)
        assert result == {"RELIANCE": 25.0}

    def test_most_common_difference_is_step_size(self, tmp_path: Path) -> None:
        rows = [
            {
                "SEM_EXM_EXCH_ID": "NSE", "SEM_SEGMENT": "D",
                "SEM_INSTRUMENT_NAME": "OPTSTK",
                "SEM_CUSTOM_SYMBOL": "TCS 06 AUG 26 3000 CE",
                "SEM_STRIKE_PRICE": "3000", "SEM_EXPIRY_DATE": "2026-08-06",
                "SEM_OPTION_TYPE": "CE", "SM_SYMBOL_NAME": "TCS",
            },
            {
                "SEM_EXM_EXCH_ID": "NSE", "SEM_SEGMENT": "D",
                "SEM_INSTRUMENT_NAME": "OPTSTK",
                "SEM_CUSTOM_SYMBOL": "TCS 06 AUG 26 3050 CE",
                "SEM_STRIKE_PRICE": "3050", "SEM_EXPIRY_DATE": "2026-08-06",
                "SEM_OPTION_TYPE": "CE", "SM_SYMBOL_NAME": "TCS",
            },
            # Irregular gap of 75 — should be ignored as most common
            {
                "SEM_EXM_EXCH_ID": "NSE", "SEM_SEGMENT": "D",
                "SEM_INSTRUMENT_NAME": "OPTSTK",
                "SEM_CUSTOM_SYMBOL": "TCS 06 AUG 26 3125 PE",
                "SEM_STRIKE_PRICE": "3125", "SEM_EXPIRY_DATE": "2026-08-06",
                "SEM_OPTION_TYPE": "PE", "SM_SYMBOL_NAME": "TCS",
            },
            {
                "SEM_EXM_EXCH_ID": "NSE", "SEM_SEGMENT": "D",
                "SEM_INSTRUMENT_NAME": "OPTSTK",
                "SEM_CUSTOM_SYMBOL": "TCS 06 AUG 26 3175 CE",
                "SEM_STRIKE_PRICE": "3175", "SEM_EXPIRY_DATE": "2026-08-06",
                "SEM_OPTION_TYPE": "CE", "SM_SYMBOL_NAME": "TCS",
            },
        ]
        csv_path = _write_csv(tmp_path, rows)
        resolver = SymbolResolver()
        result = resolver.auto_detect_step_sizes(csv_path)
        assert result == {"TCS": 50.0}

    def test_multiple_underlyings(self, tmp_path: Path) -> None:
        rows = [
            {
                "SEM_EXM_EXCH_ID": "NSE", "SEM_SEGMENT": "D",
                "SEM_INSTRUMENT_NAME": "OPTIDX",
                "SEM_CUSTOM_SYMBOL": "NIFTY 06 AUG 26 24500 CE",
                "SEM_STRIKE_PRICE": "24500", "SEM_EXPIRY_DATE": "2026-08-06",
                "SEM_OPTION_TYPE": "CE", "SM_SYMBOL_NAME": "NIFTY",
            },
            {
                "SEM_EXM_EXCH_ID": "NSE", "SEM_SEGMENT": "D",
                "SEM_INSTRUMENT_NAME": "OPTIDX",
                "SEM_CUSTOM_SYMBOL": "NIFTY 06 AUG 26 24550 CE",
                "SEM_STRIKE_PRICE": "24550", "SEM_EXPIRY_DATE": "2026-08-06",
                "SEM_OPTION_TYPE": "CE", "SM_SYMBOL_NAME": "NIFTY",
            },
            {
                "SEM_EXM_EXCH_ID": "NSE", "SEM_SEGMENT": "D",
                "SEM_INSTRUMENT_NAME": "OPTSTK",
                "SEM_CUSTOM_SYMBOL": "RELIANCE 06 AUG 26 2500 CE",
                "SEM_STRIKE_PRICE": "2500", "SEM_EXPIRY_DATE": "2026-08-06",
                "SEM_OPTION_TYPE": "CE", "SM_SYMBOL_NAME": "RELIANCE",
            },
            {
                "SEM_EXM_EXCH_ID": "NSE", "SEM_SEGMENT": "D",
                "SEM_INSTRUMENT_NAME": "OPTSTK",
                "SEM_CUSTOM_SYMBOL": "RELIANCE 06 AUG 26 2525 CE",
                "SEM_STRIKE_PRICE": "2525", "SEM_EXPIRY_DATE": "2026-08-06",
                "SEM_OPTION_TYPE": "CE", "SM_SYMBOL_NAME": "RELIANCE",
            },
        ]
        csv_path = _write_csv(tmp_path, rows)
        resolver = SymbolResolver()
        result = resolver.auto_detect_step_sizes(csv_path)
        assert result == {"NIFTY": 50.0, "RELIANCE": 25.0}

    def test_uses_nearest_expiry_only(self, tmp_path: Path) -> None:
        rows = [
            # Nearest expiry
            {
                "SEM_EXM_EXCH_ID": "NSE", "SEM_SEGMENT": "D",
                "SEM_INSTRUMENT_NAME": "OPTIDX",
                "SEM_CUSTOM_SYMBOL": "NIFTY 06 AUG 26 24500 CE",
                "SEM_STRIKE_PRICE": "24500", "SEM_EXPIRY_DATE": "2026-08-06",
                "SEM_OPTION_TYPE": "CE", "SM_SYMBOL_NAME": "NIFTY",
            },
            {
                "SEM_EXM_EXCH_ID": "NSE", "SEM_SEGMENT": "D",
                "SEM_INSTRUMENT_NAME": "OPTIDX",
                "SEM_CUSTOM_SYMBOL": "NIFTY 06 AUG 26 24600 CE",
                "SEM_STRIKE_PRICE": "24600", "SEM_EXPIRY_DATE": "2026-08-06",
                "SEM_OPTION_TYPE": "CE", "SM_SYMBOL_NAME": "NIFTY",
            },
            # Far expiry — different step, should NOT affect result
            {
                "SEM_EXM_EXCH_ID": "NSE", "SEM_SEGMENT": "D",
                "SEM_INSTRUMENT_NAME": "OPTIDX",
                "SEM_CUSTOM_SYMBOL": "NIFTY 13 AUG 26 24520 CE",
                "SEM_STRIKE_PRICE": "24520", "SEM_EXPIRY_DATE": "2026-08-13",
                "SEM_OPTION_TYPE": "CE", "SM_SYMBOL_NAME": "NIFTY",
            },
            {
                "SEM_EXM_EXCH_ID": "NSE", "SEM_SEGMENT": "D",
                "SEM_INSTRUMENT_NAME": "OPTIDX",
                "SEM_CUSTOM_SYMBOL": "NIFTY 13 AUG 26 24570 CE",
                "SEM_STRIKE_PRICE": "24570", "SEM_EXPIRY_DATE": "2026-08-13",
                "SEM_OPTION_TYPE": "CE", "SM_SYMBOL_NAME": "NIFTY",
            },
        ]
        csv_path = _write_csv(tmp_path, rows)
        resolver = SymbolResolver()
        result = resolver.auto_detect_step_sizes(csv_path)
        assert result == {"NIFTY": 100.0}

    def test_filters_out_futures_rows(self, tmp_path: Path) -> None:
        rows = [
            {
                "SEM_EXM_EXCH_ID": "NSE", "SEM_SEGMENT": "D",
                "SEM_INSTRUMENT_NAME": "FUTIDX",
                "SEM_CUSTOM_SYMBOL": "NIFTY 06 AUG 26 FUT",
                "SEM_STRIKE_PRICE": "0", "SEM_EXPIRY_DATE": "2026-08-06",
                "SEM_OPTION_TYPE": "", "SM_SYMBOL_NAME": "NIFTY",
            },
            {
                "SEM_EXM_EXCH_ID": "NSE", "SEM_SEGMENT": "D",
                "SEM_INSTRUMENT_NAME": "FUTSTK",
                "SEM_CUSTOM_SYMBOL": "RELIANCE 06 AUG 26 FUT",
                "SEM_STRIKE_PRICE": "0", "SEM_EXPIRY_DATE": "2026-08-06",
                "SEM_OPTION_TYPE": "", "SM_SYMBOL_NAME": "RELIANCE",
            },
        ]
        csv_path = _write_csv(tmp_path, rows)
        resolver = SymbolResolver()
        result = resolver.auto_detect_step_sizes(csv_path)
        assert result == {}

    def test_handles_option_commodity_rows(self, tmp_path: Path) -> None:
        rows = [
            {
                "SEM_EXM_EXCH_ID": "MCX", "SEM_SEGMENT": "M",
                "SEM_INSTRUMENT_NAME": "OPTCOM",
                "SEM_CUSTOM_SYMBOL": "SILVER 28 JUL 26 85000 CE",
                "SEM_STRIKE_PRICE": "85000", "SEM_EXPIRY_DATE": "2026-07-28",
                "SEM_OPTION_TYPE": "CE", "SM_SYMBOL_NAME": "SILVER",
            },
            {
                "SEM_EXM_EXCH_ID": "MCX", "SEM_SEGMENT": "M",
                "SEM_INSTRUMENT_NAME": "OPTCOM",
                "SEM_CUSTOM_SYMBOL": "SILVER 28 JUL 26 85250 CE",
                "SEM_STRIKE_PRICE": "85250", "SEM_EXPIRY_DATE": "2026-07-28",
                "SEM_OPTION_TYPE": "CE", "SM_SYMBOL_NAME": "SILVER",
            },
        ]
        csv_path = _write_csv(tmp_path, rows)
        resolver = SymbolResolver()
        result = resolver.auto_detect_step_sizes(csv_path)
        assert result == {"SILVER": 250.0}

    def test_skips_nan_custom_symbol(self, tmp_path: Path) -> None:
        rows = [
            {
                "SEM_EXM_EXCH_ID": "NSE", "SEM_SEGMENT": "D",
                "SEM_INSTRUMENT_NAME": "OPTIDX",
                "SEM_CUSTOM_SYMBOL": "nan",
                "SEM_STRIKE_PRICE": "24500", "SEM_EXPIRY_DATE": "2026-08-06",
                "SEM_OPTION_TYPE": "CE", "SM_SYMBOL_NAME": "NIFTY",
            },
        ]
        csv_path = _write_csv(tmp_path, rows)
        resolver = SymbolResolver()
        result = resolver.auto_detect_step_sizes(csv_path)
        assert result == {}

    def test_skips_invalid_strike_price(self, tmp_path: Path) -> None:
        rows = [
            {
                "SEM_EXM_EXCH_ID": "NSE", "SEM_SEGMENT": "D",
                "SEM_INSTRUMENT_NAME": "OPTIDX",
                "SEM_CUSTOM_SYMBOL": "NIFTY 06 AUG 26 24500 CE",
                "SEM_STRIKE_PRICE": "INVALID", "SEM_EXPIRY_DATE": "2026-08-06",
                "SEM_OPTION_TYPE": "CE", "SM_SYMBOL_NAME": "NIFTY",
            },
        ]
        csv_path = _write_csv(tmp_path, rows)
        resolver = SymbolResolver()
        result = resolver.auto_detect_step_sizes(csv_path)
        assert result == {}

    def test_skips_zero_strike(self, tmp_path: Path) -> None:
        rows = [
            {
                "SEM_EXM_EXCH_ID": "NSE", "SEM_SEGMENT": "D",
                "SEM_INSTRUMENT_NAME": "OPTIDX",
                "SEM_CUSTOM_SYMBOL": "NIFTY 06 AUG 26 0 CE",
                "SEM_STRIKE_PRICE": "0", "SEM_EXPIRY_DATE": "2026-08-06",
                "SEM_OPTION_TYPE": "CE", "SM_SYMBOL_NAME": "NIFTY",
            },
        ]
        csv_path = _write_csv(tmp_path, rows)
        resolver = SymbolResolver()
        result = resolver.auto_detect_step_sizes(csv_path)
        assert result == {}

    def test_skips_empty_expiry(self, tmp_path: Path) -> None:
        rows = [
            {
                "SEM_EXM_EXCH_ID": "NSE", "SEM_SEGMENT": "D",
                "SEM_INSTRUMENT_NAME": "OPTIDX",
                "SEM_CUSTOM_SYMBOL": "NIFTY 06 AUG 26 24500 CE",
                "SEM_STRIKE_PRICE": "24500", "SEM_EXPIRY_DATE": "",
                "SEM_OPTION_TYPE": "CE", "SM_SYMBOL_NAME": "NIFTY",
            },
        ]
        csv_path = _write_csv(tmp_path, rows)
        resolver = SymbolResolver()
        result = resolver.auto_detect_step_sizes(csv_path)
        assert result == {}

    def test_single_strike_no_step_detected(self, tmp_path: Path) -> None:
        rows = [
            {
                "SEM_EXM_EXCH_ID": "NSE", "SEM_SEGMENT": "D",
                "SEM_INSTRUMENT_NAME": "OPTIDX",
                "SEM_CUSTOM_SYMBOL": "NIFTY 06 AUG 26 24500 CE",
                "SEM_STRIKE_PRICE": "24500", "SEM_EXPIRY_DATE": "2026-08-06",
                "SEM_OPTION_TYPE": "CE", "SM_SYMBOL_NAME": "NIFTY",
            },
        ]
        csv_path = _write_csv(tmp_path, rows)
        resolver = SymbolResolver()
        result = resolver.auto_detect_step_sizes(csv_path)
        assert result == {}


# ============================================================================
# get_step_size
# ============================================================================


class TestGetStepSize:
    def test_nifty_returns_50(self) -> None:
        resolver = SymbolResolver()
        assert resolver.get_step_size("NIFTY") == 50.0

    def test_banknifty_returns_100(self) -> None:
        resolver = SymbolResolver()
        assert resolver.get_step_size("BANKNIFTY") == 100.0

    def test_finnifty_returns_50(self) -> None:
        resolver = SymbolResolver()
        assert resolver.get_step_size("FINNIFTY") == 50.0

    def test_midcpnifty_returns_25(self) -> None:
        resolver = SymbolResolver()
        assert resolver.get_step_size("MIDCPNIFTY") == 25.0

    def test_sensex_returns_100(self) -> None:
        resolver = SymbolResolver()
        assert resolver.get_step_size("SENSEX") == 100.0

    def test_bankex_returns_100(self) -> None:
        resolver = SymbolResolver()
        assert resolver.get_step_size("BANKEX") == 100.0

    def test_alternate_index_name_nifty_50(self) -> None:
        resolver = SymbolResolver()
        assert resolver.get_step_size("NIFTY 50") == 50.0

    def test_alternate_index_name_nifty_bank(self) -> None:
        resolver = SymbolResolver()
        assert resolver.get_step_size("NIFTY BANK") == 100.0

    def test_alternate_index_name_nifty_fin_service(self) -> None:
        resolver = SymbolResolver()
        assert resolver.get_step_size("NIFTY FIN SERVICE") == 50.0

    def test_alternate_index_name_nifty_mid_select(self) -> None:
        resolver = SymbolResolver()
        assert resolver.get_step_size("NIFTY MID SELECT") == 25.0

    def test_case_insensitive_index(self) -> None:
        resolver = SymbolResolver()
        assert resolver.get_step_size("nifty") == 50.0
        assert resolver.get_step_size("BankNifty") == 100.0
        assert resolver.get_step_size("sensex") == 100.0

    def test_gold_commodity_returns_100(self) -> None:
        resolver = SymbolResolver()
        assert resolver.get_step_size("GOLD") == 100.0

    def test_silver_commodity_returns_250(self) -> None:
        resolver = SymbolResolver()
        assert resolver.get_step_size("SILVER") == 250.0

    def test_crudeoil_commodity_returns_50(self) -> None:
        resolver = SymbolResolver()
        assert resolver.get_step_size("CRUDEOIL") == 50.0

    def test_naturalgas_commodity_returns_5(self) -> None:
        resolver = SymbolResolver()
        assert resolver.get_step_size("NATURALGAS") == 5.0

    def test_copper_commodity_returns_5(self) -> None:
        resolver = SymbolResolver()
        assert resolver.get_step_size("COPPER") == 5.0

    def test_all_commodities_have_positive_step(self) -> None:
        resolver = SymbolResolver()
        for sym in COMMODITY_STEP_SIZES:
            step = resolver.get_step_size(sym)
            assert step > 0, f"{sym} has non-positive step {step}"

    def test_all_indices_have_positive_step(self) -> None:
        resolver = SymbolResolver()
        for sym in INDEX_STEP_SIZES:
            step = resolver.get_step_size(sym)
            assert step > 0, f"{sym} has non-positive step {step}"

    def test_prefers_index_over_commodity(self) -> None:
        resolver = SymbolResolver()
        assert resolver.get_step_size("GOLD") == 100.0
        assert "GOLD" not in INDEX_STEP_SIZES  # commodity only

    def test_auto_detected_stock_step(self, tmp_path: Path) -> None:
        rows = [
            {
                "SEM_EXM_EXCH_ID": "NSE", "SEM_SEGMENT": "D",
                "SEM_INSTRUMENT_NAME": "OPTSTK",
                "SEM_CUSTOM_SYMBOL": "RELIANCE 06 AUG 26 2500 CE",
                "SEM_STRIKE_PRICE": "2500", "SEM_EXPIRY_DATE": "2026-08-06",
                "SEM_OPTION_TYPE": "CE", "SM_SYMBOL_NAME": "RELIANCE",
            },
            {
                "SEM_EXM_EXCH_ID": "NSE", "SEM_SEGMENT": "D",
                "SEM_INSTRUMENT_NAME": "OPTSTK",
                "SEM_CUSTOM_SYMBOL": "RELIANCE 06 AUG 26 2525 CE",
                "SEM_STRIKE_PRICE": "2525", "SEM_EXPIRY_DATE": "2026-08-06",
                "SEM_OPTION_TYPE": "CE", "SM_SYMBOL_NAME": "RELIANCE",
            },
        ]
        csv_path = _write_csv(tmp_path, rows)
        resolver = SymbolResolver()
        resolver.load_step_sizes(csv_path)
        assert resolver.get_step_size("RELIANCE") == 25.0

    def test_unknown_symbol_returns_1(self) -> None:
        resolver = SymbolResolver()
        assert resolver.get_step_size("ZZZZZZ") == 1.0

    def test_unknown_symbol_case_insensitive(self) -> None:
        resolver = SymbolResolver()
        assert resolver.get_step_size("unknown_stock_xyz") == 1.0


# ============================================================================
# load_step_sizes
# ============================================================================


class TestLoadStepSizes:
    def test_loads_from_csv(self, tmp_path: Path) -> None:
        rows = [
            {
                "SEM_EXM_EXCH_ID": "NSE", "SEM_SEGMENT": "D",
                "SEM_INSTRUMENT_NAME": "OPTSTK",
                "SEM_CUSTOM_SYMBOL": "TCS 06 AUG 26 3000 CE",
                "SEM_STRIKE_PRICE": "3000", "SEM_EXPIRY_DATE": "2026-08-06",
                "SEM_OPTION_TYPE": "CE", "SM_SYMBOL_NAME": "TCS",
            },
            {
                "SEM_EXM_EXCH_ID": "NSE", "SEM_SEGMENT": "D",
                "SEM_INSTRUMENT_NAME": "OPTSTK",
                "SEM_CUSTOM_SYMBOL": "TCS 06 AUG 26 3050 CE",
                "SEM_STRIKE_PRICE": "3050", "SEM_EXPIRY_DATE": "2026-08-06",
                "SEM_OPTION_TYPE": "CE", "SM_SYMBOL_NAME": "TCS",
            },
        ]
        csv_path = _write_csv(tmp_path, rows)
        resolver = SymbolResolver()
        resolver.load_step_sizes(csv_path)
        assert resolver.get_step_size("TCS") == 50.0

    def test_loads_empty_without_path(self) -> None:
        resolver = SymbolResolver()
        resolver.load_step_sizes()
        assert resolver._stock_step_sizes == {}
        assert resolver._step_sizes_loaded is True

    def test_sets_loaded_flag(self, tmp_path: Path) -> None:
        csv_path = _write_csv(tmp_path, [])
        resolver = SymbolResolver()
        assert resolver._step_sizes_loaded is False
        resolver.load_step_sizes(csv_path)
        assert resolver._step_sizes_loaded is True


# ============================================================================
# Edge cases
# ============================================================================


class TestEdgeCases:
    def test_empty_csv(self, tmp_path: Path) -> None:
        csv_path = _write_csv(tmp_path, [])
        resolver = SymbolResolver()
        result = resolver.auto_detect_step_sizes(csv_path)
        assert result == {}

    def test_csv_with_only_equity_rows(self, tmp_path: Path) -> None:
        rows = [
            {
                "SEM_EXM_EXCH_ID": "NSE", "SEM_SEGMENT": "E",
                "SEM_INSTRUMENT_NAME": "EQUITY",
                "SEM_CUSTOM_SYMBOL": "RELIANCE",
                "SEM_STRIKE_PRICE": "", "SEM_EXPIRY_DATE": "",
                "SEM_OPTION_TYPE": "", "SM_SYMBOL_NAME": "",
            },
        ]
        csv_path = _write_csv(tmp_path, rows)
        resolver = SymbolResolver()
        result = resolver.auto_detect_step_sizes(csv_path)
        assert result == {}

    def test_duplicate_strikes_deduped_implicitly(self, tmp_path: Path) -> None:
        rows = [
            {
                "SEM_EXM_EXCH_ID": "NSE", "SEM_SEGMENT": "D",
                "SEM_INSTRUMENT_NAME": "OPTIDX",
                "SEM_CUSTOM_SYMBOL": "NIFTY 06 AUG 26 24500 CE",
                "SEM_STRIKE_PRICE": "24500", "SEM_EXPIRY_DATE": "2026-08-06",
                "SEM_OPTION_TYPE": "CE", "SM_SYMBOL_NAME": "NIFTY",
            },
            {
                "SEM_EXM_EXCH_ID": "NSE", "SEM_SEGMENT": "D",
                "SEM_INSTRUMENT_NAME": "OPTIDX",
                "SEM_CUSTOM_SYMBOL": "NIFTY 06 AUG 26 24500 PE",
                "SEM_STRIKE_PRICE": "24500", "SEM_EXPIRY_DATE": "2026-08-06",
                "SEM_OPTION_TYPE": "PE", "SM_SYMBOL_NAME": "NIFTY",
            },
            {
                "SEM_EXM_EXCH_ID": "NSE", "SEM_SEGMENT": "D",
                "SEM_INSTRUMENT_NAME": "OPTIDX",
                "SEM_CUSTOM_SYMBOL": "NIFTY 06 AUG 26 24550 CE",
                "SEM_STRIKE_PRICE": "24550", "SEM_EXPIRY_DATE": "2026-08-06",
                "SEM_OPTION_TYPE": "CE", "SM_SYMBOL_NAME": "NIFTY",
            },
        ]
        csv_path = _write_csv(tmp_path, rows)
        resolver = SymbolResolver()
        result = resolver.auto_detect_step_sizes(csv_path)
        assert result == {"NIFTY": 50.0}

    def test_irregular_gaps_most_common_wins(self, tmp_path: Path) -> None:
        rows = [
            {
                "SEM_EXM_EXCH_ID": "NSE", "SEM_SEGMENT": "D",
                "SEM_INSTRUMENT_NAME": "OPTIDX",
                "SEM_CUSTOM_SYMBOL": "NIFTY 06 AUG 26 24000 CE",
                "SEM_STRIKE_PRICE": "24000", "SEM_EXPIRY_DATE": "2026-08-06",
                "SEM_OPTION_TYPE": "CE", "SM_SYMBOL_NAME": "NIFTY",
            },
            {
                "SEM_EXM_EXCH_ID": "NSE", "SEM_SEGMENT": "D",
                "SEM_INSTRUMENT_NAME": "OPTIDX",
                "SEM_CUSTOM_SYMBOL": "NIFTY 06 AUG 26 24050 CE",
                "SEM_STRIKE_PRICE": "24050", "SEM_EXPIRY_DATE": "2026-08-06",
                "SEM_OPTION_TYPE": "CE", "SM_SYMBOL_NAME": "NIFTY",
            },
            {
                "SEM_EXM_EXCH_ID": "NSE", "SEM_SEGMENT": "D",
                "SEM_INSTRUMENT_NAME": "OPTIDX",
                "SEM_CUSTOM_SYMBOL": "NIFTY 06 AUG 26 24100 CE",
                "SEM_STRIKE_PRICE": "24100", "SEM_EXPIRY_DATE": "2026-08-06",
                "SEM_OPTION_TYPE": "CE", "SM_SYMBOL_NAME": "NIFTY",
            },
            # One-off gap of 75 to test most-common logic
            {
                "SEM_EXM_EXCH_ID": "NSE", "SEM_SEGMENT": "D",
                "SEM_INSTRUMENT_NAME": "OPTIDX",
                "SEM_CUSTOM_SYMBOL": "NIFTY 06 AUG 26 24175 CE",
                "SEM_STRIKE_PRICE": "24175", "SEM_EXPIRY_DATE": "2026-08-06",
                "SEM_OPTION_TYPE": "CE", "SM_SYMBOL_NAME": "NIFTY",
            },
            {
                "SEM_EXM_EXCH_ID": "NSE", "SEM_SEGMENT": "D",
                "SEM_INSTRUMENT_NAME": "OPTIDX",
                "SEM_CUSTOM_SYMBOL": "NIFTY 06 AUG 26 24225 CE",
                "SEM_STRIKE_PRICE": "24225", "SEM_EXPIRY_DATE": "2026-08-06",
                "SEM_OPTION_TYPE": "CE", "SM_SYMBOL_NAME": "NIFTY",
            },
        ]
        csv_path = _write_csv(tmp_path, rows)
        resolver = SymbolResolver()
        result = resolver.auto_detect_step_sizes(csv_path)
        # Diffs: 50, 50, 75, 50 → most common = 50
        assert result == {"NIFTY": 50.0}

    def test_load_then_unknown_falls_back(self, tmp_path: Path) -> None:
        rows = [
            {
                "SEM_EXM_EXCH_ID": "NSE", "SEM_SEGMENT": "D",
                "SEM_INSTRUMENT_NAME": "OPTSTK",
                "SEM_CUSTOM_SYMBOL": "TCS 06 AUG 26 3000 CE",
                "SEM_STRIKE_PRICE": "3000", "SEM_EXPIRY_DATE": "2026-08-06",
                "SEM_OPTION_TYPE": "CE", "SM_SYMBOL_NAME": "TCS",
            },
            {
                "SEM_EXM_EXCH_ID": "NSE", "SEM_SEGMENT": "D",
                "SEM_INSTRUMENT_NAME": "OPTSTK",
                "SEM_CUSTOM_SYMBOL": "TCS 06 AUG 26 3050 CE",
                "SEM_STRIKE_PRICE": "3050", "SEM_EXPIRY_DATE": "2026-08-06",
                "SEM_OPTION_TYPE": "CE", "SM_SYMBOL_NAME": "TCS",
            },
        ]
        csv_path = _write_csv(tmp_path, rows)
        resolver = SymbolResolver()
        resolver.load_step_sizes(csv_path)
        assert resolver.get_step_size("TCS") == 50.0
        assert resolver.get_step_size("ZZZZZZ") == 1.0


if __name__ == "__main__":
    pytest.main()

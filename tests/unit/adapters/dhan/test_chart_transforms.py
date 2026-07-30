from __future__ import annotations

import pandas as pd
import pytest

from scalpr.adapters.dhan.client import DhanClient


# ── Helpers ──────────────────────────────────────────────────────────────

def _ohlc_rows(n: int = 5) -> list[dict]:
    rows = []
    for i in range(n):
        rows.append({
            "timestamp": f"2025-07-30 09:{15 + i:02d}:00",
            "open": 100.0 + i * 2,
            "high": 102.0 + i * 2,
            "low": 99.0 + i * 2,
            "close": 101.0 + i * 2,
        })
    return rows


def _df_from_rows(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


# ── renko_bricks ─────────────────────────────────────────────────────────

class TestRenkoBricks:
    def test_creates_up_brick_when_price_exceeds_box_size(self) -> None:
        data = [
            {"timestamp": "2025-07-30 09:15:00", "open": 100, "high": 101, "low": 99, "close": 100},
            {"timestamp": "2025-07-30 09:16:00", "open": 101, "high": 108, "low": 100, "close": 108},
        ]
        result = DhanClient.renko_bricks(data, box_size=7)
        assert len(result) == 1
        assert result.iloc[0]["direction"] == 1
        assert result.iloc[0]["low"] == 100
        assert result.iloc[0]["high"] == 107

    def test_creates_down_brick_when_price_falls_below_box_size(self) -> None:
        data = [
            {"timestamp": "2025-07-30 09:15:00", "open": 100, "high": 101, "low": 99, "close": 100},
            {"timestamp": "2025-07-30 09:16:00", "open": 99, "high": 100, "low": 92, "close": 92},
        ]
        result = DhanClient.renko_bricks(data, box_size=7)
        assert len(result) == 1
        assert result.iloc[0]["direction"] == -1
        assert result.iloc[0]["high"] == 100
        assert result.iloc[0]["low"] == 93

    def test_returns_correct_number_of_bricks(self) -> None:
        data = [
            {"timestamp": "2025-07-30 09:15:00", "open": 100, "high": 101, "low": 99, "close": 100},
            {"timestamp": "2025-07-30 09:16:00", "open": 110, "high": 125, "low": 110, "close": 120},
        ]
        result = DhanClient.renko_bricks(data, box_size=7)
        assert len(result) == 2  # 100→107, 107→114
        assert list(result["direction"]) == [1, 1]

    def test_handles_box_size_one(self) -> None:
        data = [
            {"timestamp": "2025-07-30 09:15:00", "open": 100, "high": 100, "low": 100, "close": 100},
            {"timestamp": "2025-07-30 09:16:00", "open": 101, "high": 105, "low": 101, "close": 104},
        ]
        result = DhanClient.renko_bricks(data, box_size=1)
        assert len(result) == 4  # 100→101, 101→102, 102→103, 103→104

    def test_empty_input_returns_empty_dataframe(self) -> None:
        result = DhanClient.renko_bricks([])
        assert isinstance(result, pd.DataFrame)
        assert result.empty
        assert list(result.columns) == ["date", "direction", "high", "low"]

    def test_empty_dataframe_returns_empty_dataframe(self) -> None:
        result = DhanClient.renko_bricks(pd.DataFrame())
        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_accepts_list_of_dicts(self) -> None:
        data = _ohlc_rows(3)
        result = DhanClient.renko_bricks(data)
        assert isinstance(result, pd.DataFrame)

    def test_accepts_dataframe(self) -> None:
        data = _df_from_rows(_ohlc_rows(3))
        result = DhanClient.renko_bricks(data)
        assert isinstance(result, pd.DataFrame)

    def test_uses_close_price_for_brick_calculation(self) -> None:
        data = [
            {"timestamp": "2025-07-30 09:15:00", "open": 50, "high": 60, "low": 40, "close": 100},
            {"timestamp": "2025-07-30 09:16:00", "open": 110, "high": 120, "low": 105, "close": 115},
        ]
        result = DhanClient.renko_bricks(data, box_size=10)
        assert len(result) >= 1
        assert result.iloc[0]["low"] == 100
        assert result.iloc[0]["high"] == 110

    def test_default_box_size_is_seven(self) -> None:
        data = [
            {"timestamp": "2025-07-30 09:15:00", "open": 100, "high": 101, "low": 99, "close": 100},
            {"timestamp": "2025-07-30 09:16:00", "open": 101, "high": 108, "low": 100, "close": 108},
        ]
        result = DhanClient.renko_bricks(data)
        assert len(result) == 1
        assert result.iloc[0]["high"] - result.iloc[0]["low"] == 7

    def test_no_bricks_when_price_within_box_size(self) -> None:
        data = [
            {"timestamp": "2025-07-30 09:15:00", "open": 100, "high": 101, "low": 99, "close": 100},
            {"timestamp": "2025-07-30 09:16:00", "open": 100, "high": 103, "low": 99, "close": 103},
        ]
        result = DhanClient.renko_bricks(data, box_size=7)
        assert len(result) == 0  # 103 - 100 = 3 < 7

    def test_handle_reversal_multiple_bricks(self) -> None:
        data = [
            {"timestamp": "2025-07-30 09:15:00", "open": 100, "high": 100, "low": 100, "close": 100},
            {"timestamp": "2025-07-30 09:16:00", "open": 110, "high": 115, "low": 110, "close": 115},
            {"timestamp": "2025-07-30 09:17:00", "open": 90, "high": 95, "low": 85, "close": 85},
        ]
        result = DhanClient.renko_bricks(data, box_size=7)
        assert len(result) == 6  # two up (100→107, 107→114), four down (114→107, 107→100, 100→93, 93→86)

    def test_output_columns_match_spec(self) -> None:
        data = [
            {"timestamp": "2025-07-30 09:15:00", "open": 100, "high": 100, "low": 100, "close": 100},
            {"timestamp": "2025-07-30 09:16:00", "open": 120, "high": 125, "low": 120, "close": 125},
        ]
        result = DhanClient.renko_bricks(data, box_size=10)
        assert list(result.columns) == ["date", "direction", "high", "low"]
        assert result["direction"].dtype == int or result["direction"].dtype == "int64"

    def test_preserves_timestamp_column_name(self) -> None:
        data = [
            {"date": "2025-07-30 09:15:00", "open": 100, "high": 101, "low": 99, "close": 100},
            {"date": "2025-07-30 09:16:00", "open": 110, "high": 115, "low": 108, "close": 115},
        ]
        result = DhanClient.renko_bricks(data, box_size=7)
        assert "date" in result.columns

    def test_sorting_before_processing(self) -> None:
        data = [
            {"timestamp": "2025-07-30 09:16:00", "open": 110, "high": 115, "low": 108, "close": 115},
            {"timestamp": "2025-07-30 09:15:00", "open": 100, "high": 101, "low": 99, "close": 100},
        ]
        result = DhanClient.renko_bricks(data, box_size=7)
        assert len(result) >= 1


# ── heikin_ashi ──────────────────────────────────────────────────────────

class TestHeikinAshi:
    def test_ha_close_is_average_of_ohlc(self) -> None:
        data = [{"timestamp": "2025-07-30 09:15:00", "open": 100, "high": 110, "low": 90, "close": 105}]
        result = DhanClient.heikin_ashi(data)
        expected_close = (100 + 110 + 90 + 105) / 4
        assert result.iloc[0]["close"] == expected_close

    def test_first_ha_open_equals_regular_open(self) -> None:
        data = [{"timestamp": "2025-07-30 09:15:00", "open": 100, "high": 110, "low": 90, "close": 105}]
        result = DhanClient.heikin_ashi(data)
        assert result.iloc[0]["open"] == 100

    def test_second_ha_open_is_mid_of_prev_ha(self) -> None:
        data = [
            {"timestamp": "2025-07-30 09:15:00", "open": 100, "high": 110, "low": 90, "close": 106},
            {"timestamp": "2025-07-30 09:16:00", "open": 110, "high": 120, "low": 105, "close": 115},
        ]
        result = DhanClient.heikin_ashi(data)
        ha0_close = (100 + 110 + 90 + 106) / 4
        expected_open = (100 + ha0_close) / 2
        assert result.iloc[1]["open"] == expected_open

    def test_ha_high_is_max_of_high_ha_open_ha_close(self) -> None:
        data = [{"timestamp": "2025-07-30 09:15:00", "open": 100, "high": 200, "low": 50, "close": 60}]
        result = DhanClient.heikin_ashi(data)
        ha_close = (100 + 200 + 50 + 60) / 4
        expected_high = max(200, 100, ha_close)
        assert result.iloc[0]["high"] == expected_high

    def test_ha_low_is_min_of_low_ha_open_ha_close(self) -> None:
        data = [{"timestamp": "2025-07-30 09:15:00", "open": 100, "high": 200, "low": 1, "close": 200}]
        result = DhanClient.heikin_ashi(data)
        ha_close = (100 + 200 + 1 + 200) / 4
        expected_low = min(1, 100, ha_close)
        assert result.iloc[0]["low"] == expected_low

    def test_preserves_number_of_rows(self) -> None:
        rows = _ohlc_rows(7)
        data = _df_from_rows(rows)
        result = DhanClient.heikin_ashi(data)
        assert len(result) == 7

    def test_preserves_timestamp_column(self) -> None:
        rows = _ohlc_rows(3)
        result = DhanClient.heikin_ashi(rows)
        assert "timestamp" in result.columns
        assert result.iloc[0]["timestamp"] == rows[0]["timestamp"]

    def test_accepts_list_of_dicts(self) -> None:
        rows = _ohlc_rows(3)
        result = DhanClient.heikin_ashi(rows)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 3

    def test_accepts_dataframe(self) -> None:
        rows = _df_from_rows(_ohlc_rows(3))
        result = DhanClient.heikin_ashi(rows)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 3

    def test_empty_input_returns_empty_dataframe(self) -> None:
        result = DhanClient.heikin_ashi([])
        assert isinstance(result, pd.DataFrame)
        assert result.empty
        assert list(result.columns) == ["timestamp", "open", "high", "low", "close"]

    def test_empty_dataframe_returns_empty_dataframe(self) -> None:
        result = DhanClient.heikin_ashi(pd.DataFrame())
        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_ha_high_never_below_ha_close_or_ha_open(self) -> None:
        rows = _ohlc_rows(10)
        result = DhanClient.heikin_ashi(rows)
        for _, r in result.iterrows():
            assert r["high"] >= r["close"]
            assert r["high"] >= r["open"]

    def test_ha_low_never_above_ha_close_or_ha_open(self) -> None:
        rows = _ohlc_rows(10)
        result = DhanClient.heikin_ashi(rows)
        for _, r in result.iterrows():
            assert r["low"] <= r["close"]
            assert r["low"] <= r["open"]

    def test_preserves_ordering(self) -> None:
        rows = [
            {"date": "2025-07-30 09:16:00", "open": 110, "high": 115, "low": 108, "close": 112},
            {"date": "2025-07-30 09:15:00", "open": 100, "high": 105, "low": 98, "close": 102},
        ]
        result = DhanClient.heikin_ashi(rows)
        assert list(result["timestamp"]) == [
            "2025-07-30 09:15:00",
            "2025-07-30 09:16:00",
        ]

    def test_output_columns_match(self) -> None:
        rows = _ohlc_rows(3)
        result = DhanClient.heikin_ashi(rows)
        assert list(result.columns) == ["timestamp", "open", "high", "low", "close"]

    def test_handles_date_column_as_timestamp_alias(self) -> None:
        rows = [
            {"date": "2025-07-30 09:15:00", "open": 100, "high": 105, "low": 98, "close": 102},
        ]
        result = DhanClient.heikin_ashi(rows)
        assert "timestamp" in result.columns

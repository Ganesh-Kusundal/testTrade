from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd

from scalpr.adapters.dhan.client import DhanClient


def _1min_data() -> pd.DataFrame:
    rows = []
    base = datetime(2025, 7, 30, 9, 15)
    for i in range(76):
        t = base + timedelta(minutes=i)
        rows.append({
            "timestamp": t,
            "open": 100.0 + i * 0.1,
            "high": 100.0 + i * 0.1 + 0.5,
            "low": 100.0 + i * 0.1 - 0.3,
            "close": 100.0 + i * 0.1 + 0.2,
            "volume": 1000 + i * 10,
        })
    return pd.DataFrame(rows)


def test_resamples_1min_to_5min() -> None:
    df = _1min_data()
    result = DhanClient.resample_timeframe(df, "5min")
    assert len(result) == 16, f"expected 16 candles, got {len(result)}"
    assert list(result.columns) == ["timestamp", "open", "high", "low", "close", "volume"]


def test_filters_pre_market_data() -> None:
    rows = [
        {"timestamp": "2025-07-30 09:00:00", "open": 99, "high": 99, "low": 99, "close": 99, "volume": 100},
        {"timestamp": "2025-07-30 09:15:00", "open": 100, "high": 101, "low": 99, "close": 100, "volume": 200},
    ]
    result = DhanClient.resample_timeframe(pd.DataFrame(rows), "5min")
    assert len(result) == 1
    assert result.iloc[0]["open"] == 100


def test_filters_post_market_data() -> None:
    rows = [
        {"timestamp": "2025-07-30 15:30:00", "open": 100, "high": 101, "low": 99, "close": 100, "volume": 200},
        {"timestamp": "2025-07-30 15:45:00", "open": 101, "high": 102, "low": 100, "close": 101, "volume": 100},
    ]
    result = DhanClient.resample_timeframe(pd.DataFrame(rows), "5min")
    assert len(result) == 1
    assert result.iloc[0]["open"] == 100


def test_handles_empty_dataframe() -> None:
    df = pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])
    result = DhanClient.resample_timeframe(df)
    assert isinstance(result, pd.DataFrame)
    assert result.empty


def test_handles_empty_list() -> None:
    result = DhanClient.resample_timeframe([])
    assert isinstance(result, pd.DataFrame)
    assert result.empty


def test_handles_list_of_dicts() -> None:
    data = [
        {"timestamp": "2025-07-30 09:15:00", "open": 100, "high": 101, "low": 99, "close": 100, "volume": 200},
        {"timestamp": "2025-07-30 09:16:00", "open": 101, "high": 102, "low": 100, "close": 101, "volume": 150},
    ]
    result = DhanClient.resample_timeframe(data, "5min")
    assert len(result) == 1
    assert result.iloc[0]["open"] == 100
    assert result.iloc[0]["close"] == 101
    assert result.iloc[0]["volume"] == 350


def test_correct_ohlc_aggregation() -> None:
    rows = [
        {"timestamp": "2025-07-30 09:15:00", "open": 100, "high": 105, "low": 99, "close": 102, "volume": 500},
        {"timestamp": "2025-07-30 09:16:00", "open": 102, "high": 108, "low": 101, "close": 107, "volume": 300},
    ]
    result = DhanClient.resample_timeframe(pd.DataFrame(rows), "5min")
    r = result.iloc[0]
    assert r["open"] == 100
    assert r["high"] == 108
    assert r["low"] == 99
    assert r["close"] == 107
    assert r["volume"] == 800


def test_works_across_multiple_days() -> None:
    rows = []
    for day in (28, 29, 30):
        for minute in (15, 20, 25):
            rows.append({
                "timestamp": f"2025-07-{day} 09:{minute}:00",
                "open": 100 + day, "high": 101 + day, "low": 99 + day,
                "close": 100 + day, "volume": 100,
            })
    result = DhanClient.resample_timeframe(pd.DataFrame(rows), "5min")
    assert len(result) == 9
    assert set(result["timestamp"].dt.date) == {
        pd.Timestamp("2025-07-28").date(),
        pd.Timestamp("2025-07-29").date(),
        pd.Timestamp("2025-07-30").date(),
    }


def test_default_timeframe_is_5min() -> None:
    df = _1min_data()
    result = DhanClient.resample_timeframe(df)
    assert len(result) == 16
    result2 = DhanClient.resample_timeframe(df, "5min")
    assert result.equals(result2)


def test_resamples_to_15min() -> None:
    df = _1min_data()
    result = DhanClient.resample_timeframe(df, "15min")
    assert len(result) == 6


def test_resamples_1H() -> None:  # noqa: N802
    rows = []
    base = datetime(2025, 7, 30, 9, 15)
    for i in range(76):
        t = base + timedelta(minutes=i)
        rows.append({
            "timestamp": t,
            "open": 100.0 + i * 0.1,
            "high": 100.0 + i * 0.1 + 0.5,
            "low": 100.0 + i * 0.1 - 0.3,
            "close": 100.0 + i * 0.1 + 0.2,
            "volume": 1000 + i * 10,
        })
    result = DhanClient.resample_timeframe(pd.DataFrame(rows), "1h")
    assert len(result) == 2
    assert result.iloc[0]["open"] == 100.0


def test_resamples_1D() -> None:  # noqa: N802
    rows = []
    for day in (28, 29):
        for hour in (9, 10, 11, 12):
            rows.append({
                "timestamp": f"2025-07-{day} {hour}:15:00",
                "open": 100, "high": 110, "low": 90, "close": 105,
                "volume": 1000,
            })
    result = DhanClient.resample_timeframe(pd.DataFrame(rows), "1D")
    assert len(result) == 2


def test_single_candle() -> None:
    data = [{"timestamp": "2025-07-30 09:15:00", "open": 100, "high": 101,
             "low": 99, "close": 100, "volume": 500}]
    result = DhanClient.resample_timeframe(data, "5min")
    assert len(result) == 1
    assert result.iloc[0]["volume"] == 500


def test_index_reset() -> None:
    df = _1min_data()
    result = DhanClient.resample_timeframe(df)
    assert "timestamp" in result.columns
    assert result.index.name is None or result.index.name != "timestamp"


def test_no_day_cross_contamination() -> None:
    rows = [
        {"timestamp": "2025-07-30 15:25:00", "open": 100, "high": 101,
         "low": 99, "close": 100, "volume": 100},
        {"timestamp": "2025-07-30 15:29:00", "open": 101, "high": 102,
         "low": 100, "close": 101, "volume": 200},
        {"timestamp": "2025-07-31 09:15:00", "open": 200, "high": 201,
         "low": 199, "close": 200, "volume": 300},
    ]
    result = DhanClient.resample_timeframe(pd.DataFrame(rows), "5min")
    assert len(result) == 2
    assert result.iloc[0]["open"] == 100
    assert result.iloc[1]["open"] == 200

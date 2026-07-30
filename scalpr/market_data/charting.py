"""Chart transform utilities — resample, Renko, Heikin-Ashi.

Extracted from Dhan MarketDataClient (REF-06) — pure data transforms with no broker dependency.
"""
from __future__ import annotations

import pandas as pd
import pytz


def resample_timeframe(data: list[dict] | pd.DataFrame, timeframe: str = "5T") -> pd.DataFrame:
    """Resample OHLCV data to a higher timeframe, respecting IST market hours."""
    if isinstance(data, list):
        df = pd.DataFrame(data)
    else:
        df = data.copy()

    if df.empty:
        return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df.set_index("timestamp", inplace=True)

    tz = pytz.timezone("Asia/Kolkata")
    df.index = df.index.tz_localize(tz, ambiguous="infer")

    market_start = pd.to_datetime("09:15:00").time()
    market_end = pd.to_datetime("15:30:00").time()

    freq = timeframe.replace("T", "min").replace("H", "h")

    resampled = []
    for date, group in df.groupby(df.index.date):
        origin = tz.localize(pd.Timestamp(f"{date} 09:15:00"))
        daily = group.between_time(market_start, market_end)
        if not daily.empty:
            r = daily.resample(freq, origin=origin).agg({
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum",
            }).dropna(how="all")
            resampled.append(r)

    if resampled:
        result = pd.concat(resampled)
    else:
        result = pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

    result.reset_index(inplace=True)
    return result


def renko_bricks(data: list[dict] | pd.DataFrame, box_size: int = 7) -> pd.DataFrame:
    """Generate Renko brick data from OHLCV."""
    if isinstance(data, list):
        df = pd.DataFrame(data)
    else:
        df = data.copy()

    if df.empty:
        return pd.DataFrame(columns=["date", "direction", "high", "low"])

    if "timestamp" in df.columns:
        df = df.rename(columns={"timestamp": "date"})

    df = df.sort_values("date").reset_index(drop=True)

    closes = df["close"].to_numpy(dtype=float)
    dates = df["date"].to_numpy()

    bricks: list[dict] = []
    brick_edge = closes[0]

    for i in range(1, len(closes)):
        close = closes[i]
        ts = dates[i]

        while close >= brick_edge + box_size:
            bricks.append({
                "date": ts,
                "direction": 1,
                "high": brick_edge + box_size,
                "low": brick_edge,
            })
            brick_edge += box_size

        while close <= brick_edge - box_size:
            bricks.append({
                "date": ts,
                "direction": -1,
                "high": brick_edge,
                "low": brick_edge - box_size,
            })
            brick_edge -= box_size

    return pd.DataFrame(bricks)


def heikin_ashi(data: list[dict] | pd.DataFrame) -> pd.DataFrame:
    """Compute Heikin-Ashi candles from OHLCV."""
    if isinstance(data, list):
        df = pd.DataFrame(data)
    else:
        df = data.copy()

    if df.empty:
        return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close"])

    if "date" in df.columns:
        df = df.rename(columns={"date": "timestamp"})

    df = df.sort_values("timestamp").reset_index(drop=True)

    ha = df[["timestamp"]].copy().astype({"timestamp": "object"})
    ha["open"] = 0.0
    ha["high"] = 0.0
    ha["low"] = 0.0
    ha["close"] = 0.0

    for i in range(len(df)):
        o = float(df.loc[i, "open"])
        h = float(df.loc[i, "high"])
        l = float(df.loc[i, "low"])
        c = float(df.loc[i, "close"])

        ha_close = (o + h + l + c) / 4.0

        if i == 0:
            ha_open = o
        else:
            ha_open = (ha.loc[i - 1, "open"] + ha.loc[i - 1, "close"]) / 2.0

        ha_high = max(h, ha_open, ha_close)
        ha_low = min(l, ha_open, ha_close)

        ha.loc[i, "open"] = ha_open
        ha.loc[i, "high"] = ha_high
        ha.loc[i, "low"] = ha_low
        ha.loc[i, "close"] = ha_close

    return ha

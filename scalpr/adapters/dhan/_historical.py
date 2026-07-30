from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from scalpr.adapters.dhan._http import DhanHttpClient
from scalpr.adapters.dhan._resolver import SymbolResolver

logger = logging.getLogger(__name__)

_VALID_INTERVALS: frozenset[int] = frozenset({1, 2, 3, 4, 5, 10, 15, 25, 60})


class HistoricalDataError(Exception):
    ...


class InvalidTimeframeError(HistoricalDataError):
    ...


class HistoricalDataAdapter:
    def __init__(self, http_client: DhanHttpClient, resolver: SymbolResolver) -> None:
        self._http = http_client
        self._resolver = resolver

    def get_intraday(
        self,
        symbol: str,
        exchange: str,
        interval: int = 5,
        from_date: str | None = None,
        to_date: str | None = None,
        as_df: bool = False,
    ) -> list[dict[str, Any]] | pd.DataFrame:
        if interval not in _VALID_INTERVALS:
            raise InvalidTimeframeError(
                f"Invalid interval: {interval!r}. Valid intervals: {sorted(_VALID_INTERVALS)}"
            )
        security_id, segment, instrument, _ = self._resolve_security(symbol, exchange)
        body: dict[str, Any] = {
            "securityId": security_id,
            "exchangeSegment": segment,
            "instrument": instrument,
            "interval": str(interval),
        }
        if from_date:
            body["fromDate"] = from_date
        if to_date:
            body["toDate"] = to_date
        data = self._http.post("/charts/intraday", data=body, bucket="history")
        candles = self._parse_candle(data)
        if as_df:
            return self._to_df(candles)
        return candles

    def get_daily(
        self,
        symbol: str,
        exchange: str,
        from_date: str | None = None,
        to_date: str | None = None,
        as_df: bool = False,
    ) -> list[dict[str, Any]] | pd.DataFrame:
        security_id, segment, instrument, expiry_code = self._resolve_security(symbol, exchange)
        body: dict[str, Any] = {
            "securityId": security_id,
            "exchangeSegment": segment,
            "instrument": instrument,
            "expiryCode": expiry_code,
        }
        if from_date:
            body["fromDate"] = from_date
        if to_date:
            body["toDate"] = to_date
        data = self._http.post("/charts/historical", data=body, bucket="history")
        candles = self._parse_candle(data)
        if as_df:
            return self._to_df(candles)
        return candles

    def get_historical(
        self,
        symbol: str,
        exchange: str,
        timeframe: str = "DAY",
        interval: int = 5,
        from_date: str | None = None,
        to_date: str | None = None,
        as_df: bool = False,
    ) -> list[dict[str, Any]] | pd.DataFrame:
        if timeframe == "DAY":
            return self.get_daily(symbol, exchange, from_date, to_date, as_df=as_df)
        return self.get_intraday(symbol, exchange, interval, from_date, to_date, as_df=as_df)

    def get_historical_batch(
        self,
        symbols: list[tuple[str, str]],
        timeframe: str = "DAY",
        interval: int = 5,
        from_date: str | None = None,
        to_date: str | None = None,
        max_workers: int = 5,
    ) -> dict[str, pd.DataFrame | list[dict] | Exception]:
        from concurrent.futures import ThreadPoolExecutor, as_completed

        def _fetch_one(sym: str, exch: str) -> tuple[str, pd.DataFrame | list[dict]]:
            key = f"{sym}:{exch}"
            result = self.get_historical(sym, exch, timeframe, interval, from_date, to_date)
            return key, result

        results: dict[str, pd.DataFrame | list[dict] | Exception] = {}
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(_fetch_one, sym, exch): (sym, exch) for sym, exch in symbols}
            for future in as_completed(futures):
                sym, exch = futures[future]
                key = f"{sym}:{exch}"
                try:
                    _, result = future.result()
                    results[key] = result
                except Exception as exc:
                    results[key] = exc
        return results

    def get_ltp(self, symbol: str, exchange: str) -> float:
        security_id, segment, _, _ = self._resolve_security(symbol, exchange)
        data = self._http.post(
            "/marketfeed/ltp",
            data={"securityIds": [security_id], "exchangeSegment": segment},
            bucket="market_data",
        )
        return float(data.get("ltp") or data.get("last_price") or 0.0)

    @staticmethod
    def _normalize_timestamp(value: Any) -> Any:
        """Normalize Dhan epoch seconds/ms or ISO strings for pandas."""
        if isinstance(value, (int, float)):
            ts = float(value)
            if ts > 1e12:
                ts /= 1000.0
            return ts
        return value

    @staticmethod
    def _to_df(data: list[dict[str, Any]]) -> pd.DataFrame:
        if not data:
            return pd.DataFrame()
        df = pd.DataFrame(data)
        if "start" in df.columns:
            df.rename(columns={"start": "timestamp"}, inplace=True)
        if "timestamp" in df.columns:
            col = df["timestamp"].map(HistoricalDataAdapter._normalize_timestamp)
            if pd.api.types.is_numeric_dtype(col):
                df["timestamp"] = pd.to_datetime(col, unit="s")
            else:
                df["timestamp"] = pd.to_datetime(col)
        return df

    def _resolve_security(self, symbol: str, exchange: str) -> tuple[str, str, str, int]:
        inst = self._resolver.resolve(symbol, exchange)
        segment = self._resolver.wire_segment_of(symbol, exchange)
        instrument = self._resolver.instrument_kind_of(symbol, exchange)
        return inst.security_id, segment, instrument, 0

    def _parse_candle(self, response: dict[str, Any]) -> list[dict[str, Any]]:
        timestamps = response.get("timestamp") or []
        if not timestamps:
            return []
        oi_values = response.get("oi")
        candles: list[dict[str, Any]] = []
        for i, ts in enumerate(timestamps):
            candle: dict[str, Any] = {
                "timestamp": self._normalize_timestamp(ts),
                "open": float(response.get("open", [])[i]),
                "high": float(response.get("high", [])[i]),
                "low": float(response.get("low", [])[i]),
                "close": float(response.get("close", [])[i]),
                "volume": int(float(response.get("volume", [])[i])),
            }
            if oi_values is not None and i < len(oi_values):
                candle["oi"] = int(float(oi_values[i]))
            candles.append(candle)
        return candles

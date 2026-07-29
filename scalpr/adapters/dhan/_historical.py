from __future__ import annotations

import logging
from typing import Any

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
    ) -> list[dict[str, Any]]:
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
        return self._parse_candle(data)

    def get_daily(
        self,
        symbol: str,
        exchange: str,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> list[dict[str, Any]]:
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
        return self._parse_candle(data)

    def get_historical(
        self,
        symbol: str,
        exchange: str,
        timeframe: str = "DAY",
        interval: int = 5,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> list[dict[str, Any]]:
        if timeframe == "DAY":
            return self.get_daily(symbol, exchange, from_date, to_date)
        return self.get_intraday(symbol, exchange, interval, from_date, to_date)

    def get_ltp(self, symbol: str, exchange: str) -> float:
        security_id, segment, _, _ = self._resolve_security(symbol, exchange)
        data = self._http.post(
            "/marketfeed/ltp",
            data={"securityIds": [security_id], "exchangeSegment": segment},
            bucket="market_data",
        )
        return float(data.get("ltp") or data.get("last_price") or 0.0)

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
                "timestamp": ts,
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

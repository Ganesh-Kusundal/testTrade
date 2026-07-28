"""Historical data adapter for Dhan REST API.

Provides methods for fetching historical OHLCV candlestick data from Dhan's
charts endpoints, normalised to the SCALPR domain OHLCV format.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from scalpr.brokers.dhan.http_client import DhanHttpClient
from scalpr.brokers.dhan.resolver import SymbolResolver

logger = logging.getLogger(__name__)

# Indian Standard Time — all timestamps returned to users in IST
_IST = ZoneInfo("Asia/Kolkata")

# Dhan v2 intraday intervals (minutes). Verified live 2026-07-27:
# the API serves 1/3/5/15/25/60 only — no 2/10/30/120/240, no weekly/monthly.
_INTRADAY_INTERVALS: dict[str, str] = {
    "1m": "1",
    "3m": "3",
    "5m": "5",
    "15m": "15",
    "25m": "25",
    "60m": "60",
    "1H": "60",
}

_DAILY_TIMEFRAMES: frozenset[str] = frozenset({"1D"})

_VALID_TIMEFRAMES: frozenset[str] = frozenset(_INTRADAY_INTERVALS) | _DAILY_TIMEFRAMES


class HistoricalDataAdapter:
    """Adapter for fetching historical OHLCV data from Dhan API.

    Responsibilities:
    - Resolve symbol to security_id via SymbolResolver
    - Map SCALPR timeframe strings to Dhan API format
    - Call Dhan charts/historical or charts/intraday endpoints
    - Parse API response into domain OHLCV objects
    - Validate all inputs before API calls

    Usage::

        adapter = HistoricalDataAdapter(http_client, resolver)
        candles = adapter.get_ohlcv(
            symbol="RELIANCE",
            exchange=DEFAULT_EXCHANGE,
            timeframe="5m",
            from_date=date(2024, 1, 1),
            to_date=date(2024, 1, 31),
        )
    """

    def __init__(self, client: DhanHttpClient, resolver: SymbolResolver) -> None:
        self._client = client
        self._resolver = resolver

    # ── Public API ──────────────────────────────────────────────────────

    def get_ohlcv(
        self,
        symbol: str,
        exchange: str,
        timeframe: str,
        from_date: date,
        to_date: date,
    ) -> list[dict[str, Any]]:
        """Fetch historical candlestick data for a date range.

        Args:
            symbol: Trading symbol (e.g., "RELIANCE", "NIFTY")
            exchange: Exchange code (e.g., "NSE", "MCX", "NFO")
            timeframe: Candle interval (e.g., "1m", "5m", "15m", "1H", "1D")
            from_date: Start date (inclusive)
            to_date: End date (inclusive)

        Returns:
            List of candle dicts with keys:
                timestamp (datetime), open (Decimal), high (Decimal),
                low (Decimal), close (Decimal), volume (int)

        Raises:
            ValueError: If inputs are invalid
            InstrumentNotFoundError: If symbol cannot be resolved
        """
        self._validate_inputs(symbol, exchange, timeframe, from_date, to_date)

        security_id, segment = self._resolve_segment(symbol, exchange)

        # Dhan v2 charts endpoints require POST + JSON body with a mandatory
        # "instrument" name (EQUITY/INDEX/FUTSTK/...). Verified live 2026-07-27.
        body: dict[str, Any] = {
            "securityId": security_id,
            "exchangeSegment": segment,
            "instrument": self._resolver.instrument_kind_of(symbol, exchange),
            "oi": False,
            "fromDate": from_date.isoformat(),
            "toDate": to_date.isoformat(),
        }
        if timeframe in _DAILY_TIMEFRAMES:
            endpoint = "/charts/historical"
            body["expiryCode"] = 0
        else:
            endpoint = "/charts/intraday"
            body["interval"] = _INTRADAY_INTERVALS[timeframe]

        logger.debug(
            "historical_ohlcv_request",
            extra={"symbol": symbol, "exchange": exchange, "endpoint": endpoint, "body": body},
        )

        data = self._client.post(endpoint, json=body)
        return self._parse_candles(data)

    def get_ohlcv_latest(
        self,
        symbol: str,
        exchange: str,
        timeframe: str,
        count: int,
    ) -> list[dict[str, Any]]:
        """Fetch the latest N candles for a symbol.

        Computes a date range that should contain at least ``count`` candles
        and returns the most recent ``count`` candles from the result.

        Args:
            symbol: Trading symbol
            exchange: Exchange code
            timeframe: Candle interval
            count: Number of candles to fetch

        Returns:
            List of the latest ``count`` candle dicts
        """
        if count <= 0:
            raise ValueError(f"count must be positive, got {count}")

        self._validate_timeframe(timeframe)

        # Estimate lookback days based on timeframe
        lookback_days = self._estimate_lookback_days(timeframe, count)

        to_date = date.today()
        from_date = to_date - timedelta(days=lookback_days)

        candles = self.get_ohlcv(symbol, exchange, timeframe, from_date, to_date)

        # Return the last `count` candles
        return candles[-count:] if len(candles) > count else candles

    def validate_timeframe(self, timeframe: str) -> bool:
        """Validate that a timeframe string is supported.

        Args:
            timeframe: Timeframe string (e.g., "1m", "5m", "1H", "1D")

        Returns:
            True if valid, False otherwise
        """
        return timeframe in _VALID_TIMEFRAMES

    # ── Input validation ────────────────────────────────────────────────

    def _validate_inputs(
        self,
        symbol: str,
        exchange: str,
        timeframe: str,
        from_date: date,
        to_date: date,
    ) -> None:
        """Validate all inputs before making an API call."""
        if not symbol or not symbol.strip():
            raise ValueError("symbol must not be empty")

        if not exchange or not exchange.strip():
            raise ValueError("exchange must not be empty")

        self._validate_timeframe(timeframe)

        if from_date > to_date:
            raise ValueError(
                f"from_date ({from_date}) must be <= to_date ({to_date})"
            )

        if to_date > date.today():
            raise ValueError(f"to_date ({to_date}) cannot be in the future")

    def _validate_timeframe(self, timeframe: str) -> None:
        """Validate timeframe format."""
        if timeframe not in _VALID_TIMEFRAMES:
            raise ValueError(
                f"Invalid timeframe: {timeframe!r}. "
                f"Valid timeframes: {sorted(_VALID_TIMEFRAMES)}"
            )

    # ── Resolution ──────────────────────────────────────────────────────

    def _resolve_segment(self, symbol: str, exchange: str) -> tuple[str, str]:
        """Resolve symbol to (security_id, segment) tuple.

        Returns:
            (security_id, dhan_segment_string)
        """
        inst = self._resolver.resolve(symbol, exchange)
        segment = self._resolver.wire_segment_of(symbol, exchange)
        security_id = inst.security_id
        return security_id, segment

    # ── Parsing ─────────────────────────────────────────────────────────

    def _parse_candles(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """Parse Dhan v2 column-array response into candle dicts.

        Dhan returns parallel arrays with epoch-second timestamps::

            {"open": [...], "high": [...], "low": [...], "close": [...],
             "volume": [...], "timestamp": [1784485800.0, ...]}
        """
        timestamps = data.get("timestamp") or []
        if not timestamps:
            logger.debug("historical_ohlcv_empty_response")
            return []

        candles = [
            {
                "timestamp": datetime.fromtimestamp(float(ts), tz=timezone.utc).astimezone(_IST),
                "open": Decimal(str(o)),
                "high": Decimal(str(h)),
                "low": Decimal(str(low)),
                "close": Decimal(str(c)),
                "volume": int(float(v)),
            }
            for ts, o, h, low, c, v in zip(
                timestamps,
                data.get("open", []),
                data.get("high", []),
                data.get("low", []),
                data.get("close", []),
                data.get("volume", []), strict=False,
            )
        ]

        logger.debug("historical_ohlcv_parsed", extra={"total_candles": len(candles)})
        return candles

    # ── Utilities ───────────────────────────────────────────────────────

    def _estimate_lookback_days(self, timeframe: str, count: int) -> int:
        """Estimate how many calendar days are needed to get ``count`` candles.

        Accounts for:
        - Trading days per week (~5 for NSE/MCX)
        - Trading hours per day (6.5 hours = 390 minutes)
        - Holidays and non-trading days buffer
        """
        # Trading minutes per day
        trading_minutes_per_day = 390  # 9:15 AM to 3:30 PM IST

        # Extract minute equivalent of timeframe
        tf_minutes = self._timeframe_to_minutes(timeframe)
        if tf_minutes is None:
            # Daily or longer — assume 1 candle per trading day
            trading_days_needed = count
        else:
            candles_per_day = trading_minutes_per_day / tf_minutes
            if candles_per_day <= 0:
                candles_per_day = 1
            trading_days_needed = int(count / candles_per_day) + 1

        # Convert trading days to calendar days (5 trading days per week)
        calendar_days = int(trading_days_needed * 7 / 5) + 2  # +2 buffer

        # Minimum 1 day, cap at 365 days
        return max(1, min(calendar_days, 365))

    def _timeframe_to_minutes(self, timeframe: str) -> int | None:
        """Convert timeframe string to minutes, or None for daily+."""
        minute_map = {
            "1m": 1, "3m": 3, "5m": 5, "15m": 15, "25m": 25,
            "60m": 60, "1H": 60,
        }
        return minute_map.get(timeframe)

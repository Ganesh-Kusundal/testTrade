"""Historical data adapter for Dhan REST API.

Provides methods for fetching historical OHLCV candlestick data from Dhan's
charts endpoints, normalised to the SCALPR domain OHLCV format.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from scalpr.brokers.dhan.http_client import DhanHttpClient
from scalpr.brokers.dhan.resolver import SymbolResolver
from scalpr.brokers.dhan.segments import EXCHANGE_TO_SEGMENT
from scalpr.domain.tick import OHLCV

logger = logging.getLogger(__name__)

# Valid timeframe patterns
_VALID_TIMEFRAMES: frozenset[str] = frozenset({
    "1m", "2m", "3m", "5m", "10m", "15m", "30m", "60m",
    "1H", "2H", "4H",
    "1D", "1W", "1M",
})

# Dhan API timeframe mapping
# Dhan accepts: 1, 3, 5, 10, 15, 30, 60 (minutes), 1D, 1W, 1M
_DHAN_TIMEFRAME_MAP: dict[str, str] = {
    "1m": "1",
    "2m": "2",
    "3m": "3",
    "5m": "5",
    "10m": "10",
    "15m": "15",
    "30m": "30",
    "60m": "60",
    "1H": "60",
    "2H": "120",
    "4H": "240",
    "1D": "1D",
    "1W": "1W",
    "1M": "1M",
}

# IST timezone (Dhan returns timestamps in IST)
_IST = timezone(timedelta(hours=5, minutes=30))


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
            exchange="NSE",
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
        dhan_tf = self._map_timeframe(timeframe)

        # Use intraday for sub-daily, historical for daily+
        if timeframe in ("1D", "1W", "1M"):
            endpoint = "/charts/historical"
        else:
            endpoint = "/charts/intraday"

        params = {
            "securityId": security_id,
            "exchangeSegment": segment,
            "interval": dhan_tf,
            "fromDate": from_date.isoformat(),
            "toDate": to_date.isoformat(),
        }

        logger.debug(
            "historical_ohlcv_request",
            extra={
                "symbol": symbol,
                "exchange": exchange,
                "segment": segment,
                "security_id": security_id,
                "timeframe": timeframe,
                "dhan_timeframe": dhan_tf,
                "from_date": from_date.isoformat(),
                "to_date": to_date.isoformat(),
                "endpoint": endpoint,
            },
        )

        data = self._client.get(f"{endpoint}?{self._encode_params(params)}")
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

    # ── Resolution & mapping ────────────────────────────────────────────

    def _resolve_segment(self, symbol: str, exchange: str) -> tuple[str, str]:
        """Resolve symbol to (security_id, segment) tuple.

        Returns:
            (security_id, dhan_segment_string)
        """
        inst = self._resolver.resolve(symbol, exchange)
        segment = EXCHANGE_TO_SEGMENT.get(inst.exchange.value, "NSE_EQ")
        security_id = inst.security_id
        return security_id, segment

    def _map_timeframe(self, timeframe: str) -> str:
        """Map SCALPR timeframe string to Dhan API interval value."""
        dhan_tf = _DHAN_TIMEFRAME_MAP.get(timeframe)
        if dhan_tf is None:
            raise ValueError(f"No Dhan mapping for timeframe: {timeframe!r}")
        return dhan_tf

    # ── Parsing ─────────────────────────────────────────────────────────

    def _parse_candles(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """Parse Dhan API response into standard candle dicts.

        Expected Dhan response structure::

            {
                "data": [
                    {
                        "timestamp": "2024-01-15T09:15:00+05:30",
                        "open": 2456.50,
                        "high": 2460.00,
                        "low": 2455.00,
                        "close": 2458.75,
                        "volume": 12345
                    },
                    ...
                ]
            }

        Returns:
            List of dicts with: timestamp, open, high, low, close, volume
        """
        candles_data = data.get("data", [])
        if not candles_data:
            logger.debug("historical_ohlcv_empty_response")
            return []

        candles: list[dict[str, Any]] = []
        for raw in candles_data:
            try:
                candle = self._parse_single_candle(raw)
                candles.append(candle)
            except Exception as exc:
                logger.warning(
                    "historical_ohlcv_parse_error",
                    extra={"raw_candle": raw, "error": str(exc)},
                )
                continue

        logger.debug(
            "historical_ohlcv_parsed",
            extra={"total_candles": len(candles)},
        )
        return candles

    def _parse_single_candle(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Parse a single raw candle dict from the API response."""
        ts = self._parse_timestamp(raw.get("timestamp", ""))
        return {
            "timestamp": ts,
            "open": Decimal(str(raw.get("open", 0))),
            "high": Decimal(str(raw.get("high", 0))),
            "low": Decimal(str(raw.get("low", 0))),
            "close": Decimal(str(raw.get("close", 0))),
            "volume": int(raw.get("volume", 0)),
        }

    def _parse_timestamp(self, ts_str: str) -> datetime:
        """Parse timestamp string to timezone-aware datetime (UTC).

        Handles formats:
        - ISO 8601 with timezone: "2024-01-15T09:15:00+05:30"
        - ISO 8601 without timezone: "2024-01-15T09:15:00"
        - Unix timestamp (seconds): 1705292700
        """
        if not ts_str:
            raise ValueError("Empty timestamp")

        # Try Unix timestamp (int or float string)
        try:
            ts_float = float(ts_str)
            if ts_float > 1e9:  # Likely a Unix timestamp in seconds
                return datetime.fromtimestamp(ts_float, tz=timezone.utc)
        except (ValueError, TypeError, OSError):
            pass

        # Try ISO 8601 parsing
        # Python 3.7+ fromisoformat handles most ISO formats
        try:
            dt = datetime.fromisoformat(ts_str)
            if dt.tzinfo is None:
                # Assume IST if no timezone (Dhan's default)
                dt = dt.replace(tzinfo=_IST)
            # Convert to UTC for consistency with SCALPR domain model
            return dt.astimezone(timezone.utc)
        except (ValueError, TypeError) as exc:
            raise ValueError(
                f"Cannot parse timestamp: {ts_str!r}"
            ) from exc

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
            "1m": 1, "2m": 2, "3m": 3, "5m": 5, "10m": 10,
            "15m": 15, "30m": 30, "60m": 60, "1H": 60,
            "2H": 120, "4H": 240,
        }
        return minute_map.get(timeframe)

    @staticmethod
    def _encode_params(params: dict[str, str]) -> str:
        """URL-encode query parameters."""
        from urllib.parse import urlencode
        return urlencode(params)

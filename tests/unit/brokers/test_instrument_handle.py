"""Tests for InstrumentHandle."""
from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from scalpr.brokers.instrument_handle import InstrumentHandle
from scalpr.domain.instrument import (
    Exchange,
    ResolvedInstrument,
    Segment,
    SimpleInstrumentId,
)


def _make_resolved():
    return ResolvedInstrument(
        instrument_id=SimpleInstrumentId(symbol="TCS", exchange=Exchange.NSE),
        security_id="2885",
        exchange=Exchange.NSE,
        segment=Segment.EQUITY,
        trading_symbol="TCS",
        wire_segment="NSE_EQ",
        lot_size=1,
        tick_size=Decimal("0.05"),
        freeze_quantity=1000,
        expiry=None,
        strike=None,
        option_type=None,
    )


class TestInstrumentHandleProperties:
    """InstrumentHandle exposes resolved instrument data."""

    def test_symbol_property(self):
        handle = InstrumentHandle(
            resolved=_make_resolved(),
            market_data_adapter=MagicMock(),
            historical_adapter=MagicMock(),
        )
        assert handle.symbol == "TCS"

    def test_exchange_property(self):
        handle = InstrumentHandle(
            resolved=_make_resolved(),
            market_data_adapter=MagicMock(),
            historical_adapter=MagicMock(),
        )
        assert handle.exchange == "NSE"

    def test_resolved_property(self):
        resolved = _make_resolved()
        handle = InstrumentHandle(
            resolved=resolved,
            market_data_adapter=MagicMock(),
            historical_adapter=MagicMock(),
        )
        assert handle.resolved == resolved
        assert handle.resolved.security_id == "2885"


class TestInstrumentHandleLtp:
    """InstrumentHandle.ltp() delegates to market_data adapter."""

    def test_ltp_returns_decimal(self):
        mock_market = MagicMock()
        mock_market.get_ltp_by_id.return_value = Decimal("3500.50")
        handle = InstrumentHandle(
            resolved=_make_resolved(),
            market_data_adapter=mock_market,
            historical_adapter=MagicMock(),
        )
        result = handle.ltp()
        assert result == Decimal("3500.50")
        mock_market.get_ltp_by_id.assert_called_once_with("2885", "NSE_EQ", symbol="TCS")


class TestInstrumentHandleQuote:
    """InstrumentHandle.quote() delegates to market_data adapter."""

    def test_quote_returns_dict(self):
        mock_market = MagicMock()
        mock_market.get_quote_by_id.return_value = {
            "symbol": "TCS",
            "exchange": "NSE",
            "ltp": Decimal("3500"),
        }
        handle = InstrumentHandle(
            resolved=_make_resolved(),
            market_data_adapter=mock_market,
            historical_adapter=MagicMock(),
        )
        result = handle.quote()
        assert result["symbol"] == "TCS"
        assert result["ltp"] == Decimal("3500")
        mock_market.get_quote_by_id.assert_called_once_with("2885", "NSE_EQ", symbol="TCS")


class TestInstrumentHandleDepth:
    """InstrumentHandle.depth() delegates to market_data adapter."""

    def test_depth_returns_dict(self):
        mock_market = MagicMock()
        mock_market.get_depth_by_id.return_value = {
            "symbol": "TCS",
            "exchange": "NSE",
            "bid_levels": [],
            "ask_levels": [],
        }
        handle = InstrumentHandle(
            resolved=_make_resolved(),
            market_data_adapter=mock_market,
            historical_adapter=MagicMock(),
        )
        result = handle.depth()
        assert result["symbol"] == "TCS"
        mock_market.get_depth_by_id.assert_called_once_with("2885", "NSE_EQ", symbol="TCS")


class TestInstrumentHandleHistorical:
    """InstrumentHandle.historical() delegates to historical adapter."""

    def test_historical_returns_candles(self):
        mock_hist = MagicMock()
        mock_hist.get_ohlcv.return_value = [
            {
                "timestamp": "2025-01-01T00:00:00",
                "open": Decimal("3400"),
                "high": Decimal("3450"),
                "low": Decimal("3380"),
                "close": Decimal("3420"),
                "volume": 1000000,
            }
        ]
        handle = InstrumentHandle(
            resolved=_make_resolved(),
            market_data_adapter=MagicMock(),
            historical_adapter=mock_hist,
        )
        result = handle.historical(interval="1D", as_json=True)
        assert len(result) == 1
        assert result[0]["open"] == Decimal("3400")
        mock_hist.get_ohlcv.assert_called_once()

    def test_historical_default_date_range(self):
        mock_hist = MagicMock()
        mock_hist.get_ohlcv.return_value = []
        handle = InstrumentHandle(
            resolved=_make_resolved(),
            market_data_adapter=MagicMock(),
            historical_adapter=mock_hist,
        )
        handle.historical()
        # Should call with default 365-day range (matches Tradehull)
        call_args = mock_hist.get_ohlcv.call_args
        assert call_args[0][0] == "TCS"
        assert call_args[0][1] == "NSE"
        assert call_args[0][2] == "1D"
        start_arg, end_arg = call_args[0][3], call_args[0][4]
        assert end_arg == date.today()
        assert start_arg == date.today() - timedelta(days=365)


class TestInstrumentHandleParamHonesty:
    """W6: no silently-ignored parameters, no inverted date ranges."""

    def test_historical_string_end_without_start_gives_valid_range(self):
        # Regression: string `end` used to be parsed AFTER defaults were
        # computed, producing start=today-90d > end for past dates.
        mock_hist = MagicMock()
        mock_hist.get_ohlcv.return_value = []
        handle = InstrumentHandle(
            resolved=_make_resolved(),
            market_data_adapter=MagicMock(),
            historical_adapter=mock_hist,
        )
        handle.historical(interval="1D", end="2025-01-10")
        call = mock_hist.get_ohlcv.call_args
        start_arg, end_arg = call[0][3], call[0][4]
        assert end_arg == date(2025, 1, 10)
        assert start_arg == date(2025, 1, 10) - timedelta(days=365)
        assert start_arg < end_arg

    def test_depth_rejects_unsupported_levels(self):
        handle = InstrumentHandle(
            resolved=_make_resolved(),
            market_data_adapter=MagicMock(),
            historical_adapter=MagicMock(),
        )
        with pytest.raises(ValueError, match="5 levels"):
            handle.depth(levels=20)


class TestInstrumentHandleTodayCandle:
    """historical() appends today's partial candle from live quote."""

    def test_today_candle_appended_when_last_candle_is_yesterday(self):
        yesterday = date.today() - timedelta(days=1)
        mock_hist = MagicMock()
        mock_hist.get_ohlcv.return_value = [
            {
                "timestamp": datetime(yesterday.year, yesterday.month, yesterday.day, 9, 15),
                "open": Decimal("3400"),
                "high": Decimal("3450"),
                "low": Decimal("3380"),
                "close": Decimal("3420"),
                "volume": 1000000,
            }
        ]
        mock_market = MagicMock()
        mock_market.get_quote_by_id.return_value = {
            "open": Decimal("3425"),
            "high": Decimal("3460"),
            "low": Decimal("3410"),
            "ltp": Decimal("3445"),
            "volume": 500000,
        }
        handle = InstrumentHandle(
            resolved=_make_resolved(),
            market_data_adapter=mock_market,
            historical_adapter=mock_hist,
        )
        result = handle.historical(interval="1D", as_json=True)
        assert len(result) == 2
        # Today's candle should have quote data
        today_candle = result[-1]
        assert today_candle["open"] == Decimal("3425")
        assert today_candle["close"] == Decimal("3445")
        assert today_candle["volume"] == 500000

    def test_no_today_candle_when_explicit_end(self):
        yesterday = date.today() - timedelta(days=1)
        mock_hist = MagicMock()
        mock_hist.get_ohlcv.return_value = [
            {
                "timestamp": datetime(yesterday.year, yesterday.month, yesterday.day),
                "open": Decimal("3400"),
                "high": Decimal("3450"),
                "low": Decimal("3380"),
                "close": Decimal("3420"),
                "volume": 1000000,
            }
        ]
        mock_market = MagicMock()
        handle = InstrumentHandle(
            resolved=_make_resolved(),
            market_data_adapter=mock_market,
            historical_adapter=mock_hist,
        )
        result = handle.historical(interval="1D", end=str(yesterday), as_json=True)
        assert len(result) == 1
        # get_quote_by_id should NOT be called for today's candle
        mock_market.get_quote_by_id.assert_not_called()

    def test_no_today_candle_for_intraday(self):
        yesterday = date.today() - timedelta(days=1)
        mock_hist = MagicMock()
        mock_hist.get_ohlcv.return_value = [
            {
                "timestamp": datetime(yesterday.year, yesterday.month, yesterday.day, 15, 30),
                "open": Decimal("3400"),
                "high": Decimal("3450"),
                "low": Decimal("3380"),
                "close": Decimal("3420"),
                "volume": 1000000,
            }
        ]
        mock_market = MagicMock()
        handle = InstrumentHandle(
            resolved=_make_resolved(),
            market_data_adapter=mock_market,
            historical_adapter=mock_hist,
        )
        result = handle.historical(interval="5m", as_json=True)
        assert len(result) == 1
        mock_market.get_quote_by_id.assert_not_called()

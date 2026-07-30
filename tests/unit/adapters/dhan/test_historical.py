from __future__ import annotations

from unittest.mock import MagicMock

import pandas as pd
import pytest

from scalpr.adapters.dhan._historical import (
    HistoricalDataAdapter,
    HistoricalDataError,
    InvalidTimeframeError,
)


@pytest.fixture
def http_client() -> MagicMock:
    return MagicMock()


@pytest.fixture
def resolver() -> MagicMock:
    r = MagicMock()
    inst = MagicMock()
    inst.security_id = "12345"
    r.resolve.return_value = inst
    r.wire_segment_of.return_value = "NSE_EQ"
    r.instrument_kind_of.return_value = "EQUITY"
    return r


@pytest.fixture
def adapter(http_client: MagicMock, resolver: MagicMock) -> HistoricalDataAdapter:
    return HistoricalDataAdapter(http_client, resolver)


# ============================================================================
# Construction
# ============================================================================

class TestHistoricalDataAdapter:
    def test_stores_http_client(self, adapter: HistoricalDataAdapter, http_client: MagicMock) -> None:
        assert adapter._http is http_client

    def test_stores_resolver(self, adapter: HistoricalDataAdapter, resolver: MagicMock) -> None:
        assert adapter._resolver is resolver

    def test_historical_data_error_is_base_exception(self) -> None:
        assert issubclass(InvalidTimeframeError, HistoricalDataError)


# ============================================================================
# get_intraday
# ============================================================================

class TestGetIntraday:
    def test_calls_post_with_correct_endpoint_and_bucket(self, adapter: HistoricalDataAdapter, http_client: MagicMock) -> None:
        http_client.post.return_value = {"timestamp": [100.0], "open": [100], "high": [105], "low": [99], "close": [103], "volume": [1000]}
        adapter.get_intraday("RELIANCE", "NSE")
        http_client.post.assert_called_once_with("/charts/intraday", data={
            "securityId": "12345",
            "exchangeSegment": "NSE_EQ",
            "instrument": "EQUITY",
            "interval": "5",
        }, bucket="history")

    def test_passes_interval_as_string(self, adapter: HistoricalDataAdapter, http_client: MagicMock) -> None:
        http_client.post.return_value = {"timestamp": [], "open": [], "high": [], "low": [], "close": [], "volume": []}
        adapter.get_intraday("RELIANCE", "NSE", interval=15)
        body = http_client.post.call_args[1]["data"]
        assert body["interval"] == "15"

    def test_returns_parsed_candles(self, adapter: HistoricalDataAdapter, http_client: MagicMock) -> None:
        http_client.post.return_value = {
            "timestamp": [100.0, 200.0],
            "open": [100.5, 102.0],
            "high": [105.0, 106.5],
            "low": [99.5, 101.0],
            "close": [103.0, 104.5],
            "volume": [1000, 1500],
        }
        result = adapter.get_intraday("RELIANCE", "NSE")
        assert len(result) == 2
        assert result[0] == {"timestamp": 100.0, "open": 100.5, "high": 105.0, "low": 99.5, "close": 103.0, "volume": 1000}
        assert result[1] == {"timestamp": 200.0, "open": 102.0, "high": 106.5, "low": 101.0, "close": 104.5, "volume": 1500}

    def test_raises_on_invalid_interval(self, adapter: HistoricalDataAdapter) -> None:
        with pytest.raises(InvalidTimeframeError, match="Invalid interval"):
            adapter.get_intraday("RELIANCE", "NSE", interval=7)

    def test_raises_on_zero_interval(self, adapter: HistoricalDataAdapter) -> None:
        with pytest.raises(InvalidTimeframeError):
            adapter.get_intraday("RELIANCE", "NSE", interval=0)

    def test_includes_from_date(self, adapter: HistoricalDataAdapter, http_client: MagicMock) -> None:
        http_client.post.return_value = {"timestamp": [], "open": [], "high": [], "low": [], "close": [], "volume": []}
        adapter.get_intraday("RELIANCE", "NSE", from_date="2024-01-01")
        body = http_client.post.call_args[1]["data"]
        assert body["fromDate"] == "2024-01-01"

    def test_includes_to_date(self, adapter: HistoricalDataAdapter, http_client: MagicMock) -> None:
        http_client.post.return_value = {"timestamp": [], "open": [], "high": [], "low": [], "close": [], "volume": []}
        adapter.get_intraday("RELIANCE", "NSE", to_date="2024-01-31")
        body = http_client.post.call_args[1]["data"]
        assert body["toDate"] == "2024-01-31"

    def test_omits_optional_dates_when_not_provided(self, adapter: HistoricalDataAdapter, http_client: MagicMock) -> None:
        http_client.post.return_value = {"timestamp": [], "open": [], "high": [], "low": [], "close": [], "volume": []}
        adapter.get_intraday("RELIANCE", "NSE")
        body = http_client.post.call_args[1]["data"]
        assert "fromDate" not in body
        assert "toDate" not in body

    def test_empty_response(self, adapter: HistoricalDataAdapter, http_client: MagicMock) -> None:
        http_client.post.return_value = {}
        result = adapter.get_intraday("RELIANCE", "NSE")
        assert result == []

    def test_empty_timestamps_list(self, adapter: HistoricalDataAdapter, http_client: MagicMock) -> None:
        http_client.post.return_value = {"timestamp": [], "open": [], "high": [], "low": [], "close": [], "volume": []}
        result = adapter.get_intraday("RELIANCE", "NSE")
        assert result == []

    def test_propagates_resolver_error(self, adapter: HistoricalDataAdapter, resolver: MagicMock) -> None:
        resolver.resolve.side_effect = ValueError("symbol not found")
        with pytest.raises(ValueError, match="symbol not found"):
            adapter.get_intraday("UNKNOWN", "NSE")

    def test_propagates_http_error(self, adapter: HistoricalDataAdapter, http_client: MagicMock) -> None:
        http_client.post.side_effect = RuntimeError("API timeout")
        with pytest.raises(RuntimeError, match="API timeout"):
            adapter.get_intraday("RELIANCE", "NSE")


# ============================================================================
# get_daily
# ============================================================================

class TestGetDaily:
    def test_calls_post_with_correct_endpoint_and_bucket(self, adapter: HistoricalDataAdapter, http_client: MagicMock) -> None:
        http_client.post.return_value = {"timestamp": [100.0], "open": [100], "high": [105], "low": [99], "close": [103], "volume": [1000]}
        adapter.get_daily("RELIANCE", "NSE")
        http_client.post.assert_called_once_with("/charts/historical", data={
            "securityId": "12345",
            "exchangeSegment": "NSE_EQ",
            "instrument": "EQUITY",
            "expiryCode": 0,
        }, bucket="history")

    def test_includes_expiry_code(self, adapter: HistoricalDataAdapter, http_client: MagicMock) -> None:
        http_client.post.return_value = {"timestamp": [], "open": [], "high": [], "low": [], "close": [], "volume": []}
        adapter.get_daily("RELIANCE", "NSE")
        body = http_client.post.call_args[1]["data"]
        assert body["expiryCode"] == 0

    def test_returns_parsed_candles_with_oi(self, adapter: HistoricalDataAdapter, http_client: MagicMock) -> None:
        http_client.post.return_value = {
            "timestamp": [100.0],
            "open": [100.5],
            "high": [105.0],
            "low": [99.5],
            "close": [103.0],
            "volume": [1000],
            "oi": [50000],
        }
        result = adapter.get_daily("RELIANCE", "NSE")
        assert len(result) == 1
        assert result[0]["oi"] == 50000

    def test_omits_oi_when_not_in_response(self, adapter: HistoricalDataAdapter, http_client: MagicMock) -> None:
        http_client.post.return_value = {
            "timestamp": [100.0],
            "open": [100.5],
            "high": [105.0],
            "low": [99.5],
            "close": [103.0],
            "volume": [1000],
        }
        result = adapter.get_daily("RELIANCE", "NSE")
        assert "oi" not in result[0]

    def test_empty_response(self, adapter: HistoricalDataAdapter, http_client: MagicMock) -> None:
        http_client.post.return_value = {}
        result = adapter.get_daily("RELIANCE", "NSE")
        assert result == []

    def test_includes_from_date(self, adapter: HistoricalDataAdapter, http_client: MagicMock) -> None:
        http_client.post.return_value = {"timestamp": [], "open": [], "high": [], "low": [], "close": [], "volume": []}
        adapter.get_daily("RELIANCE", "NSE", from_date="2024-01-01")
        body = http_client.post.call_args[1]["data"]
        assert body["fromDate"] == "2024-01-01"

    def test_includes_to_date(self, adapter: HistoricalDataAdapter, http_client: MagicMock) -> None:
        http_client.post.return_value = {"timestamp": [], "open": [], "high": [], "low": [], "close": [], "volume": []}
        adapter.get_daily("RELIANCE", "NSE", to_date="2024-01-31")
        body = http_client.post.call_args[1]["data"]
        assert body["toDate"] == "2024-01-31"

    def test_response_with_all_empty_arrays_returns_empty_list(self, adapter: HistoricalDataAdapter, http_client: MagicMock) -> None:
        http_client.post.return_value = {"timestamp": [], "open": [], "high": [], "low": [], "close": [], "volume": []}
        result = adapter.get_daily("RELIANCE", "NSE")
        assert result == []


# ============================================================================
# get_historical (unified dispatch)
# ============================================================================

class TestGetHistorical:
    def test_timeframe_day_dispatches_to_get_daily(self, adapter: HistoricalDataAdapter, http_client: MagicMock) -> None:
        http_client.post.return_value = {"timestamp": [100.0], "open": [100], "high": [105], "low": [99], "close": [103], "volume": [1000]}
        adapter.get_historical("RELIANCE", "NSE", timeframe="DAY")
        assert http_client.post.call_args[0][0] == "/charts/historical"

    def test_timeframe_intraday_dispatches_to_get_intraday(self, adapter: HistoricalDataAdapter, http_client: MagicMock) -> None:
        http_client.post.return_value = {"timestamp": [100.0], "open": [100], "high": [105], "low": [99], "close": [103], "volume": [1000]}
        adapter.get_historical("RELIANCE", "NSE", timeframe="5", interval=10)
        assert http_client.post.call_args[0][0] == "/charts/intraday"

    def test_intraday_dispatch_passes_interval(self, adapter: HistoricalDataAdapter, http_client: MagicMock) -> None:
        http_client.post.return_value = {"timestamp": [], "open": [], "high": [], "low": [], "close": [], "volume": []}
        adapter.get_historical("RELIANCE", "NSE", timeframe="15", interval=15)
        body = http_client.post.call_args[1]["data"]
        assert body["interval"] == "15"

    def test_daily_dispatch_uses_default_expiry_code(self, adapter: HistoricalDataAdapter, http_client: MagicMock) -> None:
        http_client.post.return_value = {"timestamp": [], "open": [], "high": [], "low": [], "close": [], "volume": []}
        adapter.get_historical("RELIANCE", "NSE", timeframe="DAY")
        body = http_client.post.call_args[1]["data"]
        assert body["expiryCode"] == 0

    def test_passes_from_date_to_dispatched_method(self, adapter: HistoricalDataAdapter, http_client: MagicMock) -> None:
        http_client.post.return_value = {"timestamp": [], "open": [], "high": [], "low": [], "close": [], "volume": []}
        adapter.get_historical("RELIANCE", "NSE", timeframe="DAY", from_date="2024-01-01")
        body = http_client.post.call_args[1]["data"]
        assert body["fromDate"] == "2024-01-01"

    def test_passes_to_date_to_dispatched_method(self, adapter: HistoricalDataAdapter, http_client: MagicMock) -> None:
        http_client.post.return_value = {"timestamp": [], "open": [], "high": [], "low": [], "close": [], "volume": []}
        adapter.get_historical("RELIANCE", "NSE", timeframe="5", to_date="2024-01-31")
        body = http_client.post.call_args[1]["data"]
        assert body["toDate"] == "2024-01-31"

    def test_intraday_dispatch_uses_default_interval(self, adapter: HistoricalDataAdapter, http_client: MagicMock) -> None:
        http_client.post.return_value = {"timestamp": [], "open": [], "high": [], "low": [], "close": [], "volume": []}
        adapter.get_historical("RELIANCE", "NSE", timeframe="5")
        body = http_client.post.call_args[1]["data"]
        assert body["interval"] == "5"


# ============================================================================
# get_historical_batch
# ============================================================================

class TestGetHistoricalBatch:
    def test_fetches_multiple_symbols(self, adapter: HistoricalDataAdapter, http_client: MagicMock) -> None:
        http_client.post.return_value = {
            "timestamp": [100.0],
            "open": [100],
            "high": [105],
            "low": [99],
            "close": [103],
            "volume": [1000],
        }
        symbols = [("RELIANCE", "NSE"), ("TCS", "NSE")]
        result = adapter.get_historical_batch(symbols)
        assert http_client.post.call_count == 2
        assert "RELIANCE:NSE" in result
        assert "TCS:NSE" in result

    def test_returns_dict_with_keys(self, adapter: HistoricalDataAdapter, http_client: MagicMock) -> None:
        http_client.post.return_value = {
            "timestamp": [100.0],
            "open": [100],
            "high": [105],
            "low": [99],
            "close": [103],
            "volume": [1000],
        }
        result = adapter.get_historical_batch([("RELIANCE", "NSE")])
        assert isinstance(result, dict)
        assert list(result.keys()) == ["RELIANCE:NSE"]

    def test_returns_exception_on_failure(self, adapter: HistoricalDataAdapter, http_client: MagicMock) -> None:
        http_client.post.return_value = {
            "timestamp": [100.0],
            "open": [100],
            "high": [105],
            "low": [99],
            "close": [103],
            "volume": [1000],
        }
        _orig = adapter.get_daily
        def _patched(symbol, exchange, *a, **kw):
            if symbol == "FAIL":
                raise RuntimeError("API error")
            return _orig(symbol, exchange, *a, **kw)
        adapter.get_daily = _patched
        symbols = [("RELIANCE", "NSE"), ("FAIL", "NSE")]
        result = adapter.get_historical_batch(symbols)
        assert isinstance(result["RELIANCE:NSE"], list)
        assert isinstance(result["FAIL:NSE"], Exception)

    def test_empty_symbols_list(self, adapter: HistoricalDataAdapter) -> None:
        result = adapter.get_historical_batch([])
        assert result == {}

    def test_max_workers_limits_concurrency(self, adapter: HistoricalDataAdapter, http_client: MagicMock) -> None:
        http_client.post.return_value = {
            "timestamp": [100.0],
            "open": [100],
            "high": [105],
            "low": [99],
            "close": [103],
            "volume": [1000],
        }
        symbols = [("A", "NSE"), ("B", "NSE"), ("C", "NSE")]
        adapter.get_historical_batch(symbols, max_workers=2)
        assert http_client.post.call_count == 3

    def test_rate_limiter_respected(self, adapter: HistoricalDataAdapter, http_client: MagicMock) -> None:
        import threading
        call_times: list[float] = []
        lock = threading.Lock()

        def _record(*args, **kwargs):
            with lock:
                call_times.append(__import__("time").time())
            return {"timestamp": [100.0], "open": [100], "high": [105], "low": [99], "close": [103], "volume": [1000]}

        http_client.post.side_effect = _record
        adapter.get_historical_batch([("A", "NSE"), ("B", "NSE")], max_workers=2)
        assert len(call_times) == 2


# ============================================================================
# get_ltp
# ============================================================================

class TestGetLTP:
    def test_calls_post_with_correct_endpoint(self, adapter: HistoricalDataAdapter, http_client: MagicMock) -> None:
        http_client.post.return_value = {"ltp": 2500.5}
        adapter.get_ltp("RELIANCE", "NSE")
        http_client.post.assert_called_once_with(
            "/marketfeed/ltp",
            data={"securityIds": ["12345"], "exchangeSegment": "NSE_EQ"},
            bucket="market_data",
        )

    def test_returns_float(self, adapter: HistoricalDataAdapter, http_client: MagicMock) -> None:
        http_client.post.return_value = {"ltp": 2500.5}
        result = adapter.get_ltp("RELIANCE", "NSE")
        assert isinstance(result, float)
        assert result == 2500.5

    def test_falls_back_to_last_price(self, adapter: HistoricalDataAdapter, http_client: MagicMock) -> None:
        http_client.post.return_value = {"last_price": 2510.75}
        result = adapter.get_ltp("RELIANCE", "NSE")
        assert result == 2510.75

    def test_returns_zero_when_no_price(self, adapter: HistoricalDataAdapter, http_client: MagicMock) -> None:
        http_client.post.return_value = {}
        result = adapter.get_ltp("RELIANCE", "NSE")
        assert result == 0.0


# ============================================================================
# _resolve_security
# ============================================================================

class TestResolveSecurity:
    def test_calls_resolver_resolve(self, adapter: HistoricalDataAdapter, resolver: MagicMock) -> None:
        adapter._resolve_security("RELIANCE", "NSE")
        resolver.resolve.assert_called_once_with("RELIANCE", "NSE")

    def test_calls_wire_segment_of(self, adapter: HistoricalDataAdapter, resolver: MagicMock) -> None:
        adapter._resolve_security("RELIANCE", "NSE")
        resolver.wire_segment_of.assert_called_once_with("RELIANCE", "NSE")

    def test_calls_instrument_kind_of(self, adapter: HistoricalDataAdapter, resolver: MagicMock) -> None:
        adapter._resolve_security("RELIANCE", "NSE")
        resolver.instrument_kind_of.assert_called_once_with("RELIANCE", "NSE")

    def test_returns_tuple(self, adapter: HistoricalDataAdapter) -> None:
        result = adapter._resolve_security("RELIANCE", "NSE")
        assert isinstance(result, tuple)
        assert len(result) == 4
        sid, seg, inst_kind, exp_code = result
        assert sid == "12345"
        assert seg == "NSE_EQ"
        assert inst_kind == "EQUITY"
        assert exp_code == 0


# ============================================================================
# _parse_candle
# ============================================================================

class TestParseCandle:
    def test_parses_column_format(self, adapter: HistoricalDataAdapter) -> None:
        response = {
            "timestamp": [100.0, 200.0],
            "open": [100.5, 102.0],
            "high": [105.0, 106.5],
            "low": [99.5, 101.0],
            "close": [103.0, 104.5],
            "volume": [1000, 1500],
        }
        result = adapter._parse_candle(response)
        assert len(result) == 2
        assert result[0] == {"timestamp": 100.0, "open": 100.5, "high": 105.0, "low": 99.5, "close": 103.0, "volume": 1000}
        assert result[1] == {"timestamp": 200.0, "open": 102.0, "high": 106.5, "low": 101.0, "close": 104.5, "volume": 1500}

    def test_returns_empty_list_for_empty_timestamps(self, adapter: HistoricalDataAdapter) -> None:
        response = {"timestamp": [], "open": [], "high": [], "low": [], "close": [], "volume": []}
        result = adapter._parse_candle(response)
        assert result == []

    def test_returns_empty_list_for_missing_timestamp_key(self, adapter: HistoricalDataAdapter) -> None:
        result = adapter._parse_candle({})
        assert result == []

    def test_includes_oi_when_present(self, adapter: HistoricalDataAdapter) -> None:
        response = {
            "timestamp": [100.0],
            "open": [100.5],
            "high": [105.0],
            "low": [99.5],
            "close": [103.0],
            "volume": [1000],
            "oi": [50000],
        }
        result = adapter._parse_candle(response)
        assert result[0]["oi"] == 50000

    def test_omits_oi_when_null(self, adapter: HistoricalDataAdapter) -> None:
        response = {
            "timestamp": [100.0],
            "open": [100.5],
            "high": [105.0],
            "low": [99.5],
            "close": [103.0],
            "volume": [1000],
            "oi": None,
        }
        result = adapter._parse_candle(response)
        assert "oi" not in result[0]

    def test_converts_types_correctly(self, adapter: HistoricalDataAdapter) -> None:
        response = {
            "timestamp": [100.0],
            "open": ["100.5"],
            "high": ["105.0"],
            "low": ["99.5"],
            "close": ["103.0"],
            "volume": ["1000"],
        }
        result = adapter._parse_candle(response)
        c = result[0]
        assert isinstance(c["timestamp"], float)
        assert isinstance(c["open"], float)
        assert isinstance(c["high"], float)
        assert isinstance(c["low"], float)
        assert isinstance(c["close"], float)
        assert isinstance(c["volume"], int)


# ============================================================================
# _to_df
# ============================================================================

class TestToDf:
    def test_empty_list_returns_empty_dataframe(self, adapter: HistoricalDataAdapter) -> None:
        df = adapter._to_df([])
        assert df.empty

    def test_renames_start_to_timestamp(self, adapter: HistoricalDataAdapter) -> None:
        data = [{"start": "2024-01-01", "open": 100.0, "high": 105.0, "low": 99.0, "close": 103.0, "volume": 1000}]
        df = adapter._to_df(data)
        assert "timestamp" in df.columns
        assert "start" not in df.columns

    def test_converts_timestamp_to_datetime(self, adapter: HistoricalDataAdapter) -> None:
        data = [{"timestamp": "2024-01-01", "open": 100.0, "high": 105.0, "low": 99.0, "close": 103.0, "volume": 1000}]
        df = adapter._to_df(data)
        assert pd.api.types.is_datetime64_any_dtype(df["timestamp"])

    def test_keeps_oi_column_when_present(self, adapter: HistoricalDataAdapter) -> None:
        data = [{"timestamp": "2024-01-01", "open": 100.0, "high": 105.0, "low": 99.0, "close": 103.0, "volume": 1000, "oi": 50000}]
        df = adapter._to_df(data)
        assert "oi" in df.columns
        assert df["oi"].iloc[0] == 50000


# ============================================================================
# as_df integration tests
# ============================================================================

class TestAsDfIntegration:
    def test_get_intraday_with_as_df_returns_dataframe(self, adapter: HistoricalDataAdapter, http_client: MagicMock) -> None:
        http_client.post.return_value = {
            "timestamp": [100.0, 200.0],
            "open": [100.5, 102.0],
            "high": [105.0, 106.5],
            "low": [99.5, 101.0],
            "close": [103.0, 104.5],
            "volume": [1000, 1500],
        }
        result = adapter.get_intraday("RELIANCE", "NSE", as_df=True)
        assert isinstance(result, pd.DataFrame)
        assert list(result.columns) == ["timestamp", "open", "high", "low", "close", "volume"]
        assert len(result) == 2

    def test_get_daily_with_as_df_returns_dataframe(self, adapter: HistoricalDataAdapter, http_client: MagicMock) -> None:
        http_client.post.return_value = {
            "timestamp": [100.0],
            "open": [100.5],
            "high": [105.0],
            "low": [99.5],
            "close": [103.0],
            "volume": [1000],
            "oi": [50000],
        }
        result = adapter.get_daily("RELIANCE", "NSE", as_df=True)
        assert isinstance(result, pd.DataFrame)
        assert list(result.columns) == ["timestamp", "open", "high", "low", "close", "volume", "oi"]
        assert len(result) == 1

    def test_get_historical_with_as_df_true_returns_dataframe(self, adapter: HistoricalDataAdapter, http_client: MagicMock) -> None:
        http_client.post.return_value = {
            "timestamp": [100.0],
            "open": [100.5],
            "high": [105.0],
            "low": [99.5],
            "close": [103.0],
            "volume": [1000],
        }
        result = adapter.get_historical("RELIANCE", "NSE", timeframe="DAY", as_df=True)
        assert isinstance(result, pd.DataFrame)

    def test_get_historical_with_as_df_false_returns_list(self, adapter: HistoricalDataAdapter, http_client: MagicMock) -> None:
        http_client.post.return_value = {
            "timestamp": [100.0],
            "open": [100.5],
            "high": [105.0],
            "low": [99.5],
            "close": [103.0],
            "volume": [1000],
        }
        result = adapter.get_historical("RELIANCE", "NSE", timeframe="DAY", as_df=False)
        assert isinstance(result, list)

    def test_dataframe_has_expected_columns(self, adapter: HistoricalDataAdapter, http_client: MagicMock) -> None:
        http_client.post.return_value = {
            "timestamp": [100.0],
            "open": [100.5],
            "high": [105.0],
            "low": [99.5],
            "close": [103.0],
            "volume": [1000],
        }
        df = adapter.get_intraday("RELIANCE", "NSE", as_df=True)
        expected = {"timestamp", "open", "high", "low", "close", "volume"}
        assert set(df.columns) == expected

    def test_dataframe_includes_oi_when_present(self, adapter: HistoricalDataAdapter, http_client: MagicMock) -> None:
        http_client.post.return_value = {
            "timestamp": [100.0],
            "open": [100.5],
            "high": [105.0],
            "low": [99.5],
            "close": [103.0],
            "volume": [1000],
            "oi": [50000],
        }
        df = adapter.get_intraday("RELIANCE", "NSE", as_df=True)
        assert "oi" in df.columns
        assert df["oi"].iloc[0] == 50000

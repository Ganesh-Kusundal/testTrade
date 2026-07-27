---
type: community
cohesion: 0.05
members: 42
---

# Tests: Unit/Brokers

**Cohesion:** 0.05 - loosely connected
**Members:** 42 nodes

## Members
- [[.test_should_accept_all_valid_hour_timeframes()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_accept_all_valid_minute_timeframes()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_cap_lookback_at_365_days()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_convert_minute_timeframes_to_minutes()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_encode_params_correctly()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_estimate_larger_lookback_for_daily_timeframe()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_estimate_lookback_for_minute_timeframe()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_fetch_latest_candles()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_fetch_ohlcv_and_return_parsed_candles()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_map_daily_weekly_monthly_timeframes_correctly()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_map_hour_timeframes_correctly()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_map_minute_timeframes_correctly()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_parse_iso_timestamp_with_timezone_to_utc()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_parse_iso_timestamp_without_timezone_as_ist()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_parse_single_candle_with_decimal_types()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_parse_unix_timestamp()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_raise_error_for_empty_timestamp()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_raise_error_for_negative_count_in_ohlcv_latest()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_raise_error_for_unmappable_timeframe()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_raise_error_for_unparseable_timestamp()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_raise_error_for_zero_count_in_ohlcv_latest()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_raise_value_error_for_empty_exchange()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_raise_value_error_for_empty_symbol()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_raise_value_error_for_invalid_timeframe_in_get_ohlcv()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_raise_value_error_for_whitespace_symbol()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_raise_value_error_when_from_date_after_to_date()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_raise_value_error_when_to_date_in_future()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_reject_unsupported_timeframe()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_resolve_segment_via_resolver()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_return_all_candles_when_fewer_than_requested()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_return_empty_list_for_empty_response()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_return_empty_list_for_missing_data_key()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_return_minimum_1_day()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_return_none_for_daily_timeframe()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_skip_malformed_candles_and_continue()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_use_historical_endpoint_for_daily_timeframe()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_use_historical_endpoint_for_monthly_timeframe()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_use_historical_endpoint_for_weekly_timeframe()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_use_intraday_endpoint_for_sub_daily_timeframe()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_validate_supported_timeframe()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[TestHistoricalDataAdapter]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[Tests for HistoricalDataAdapter covering OHLCV fetching,     timeframe validatio]] - rationale - tests/unit/brokers/dhan/test_adapters.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Tests_Unit/Brokers
SORT file.name ASC
```

## Connections to other communities
- 6 edges to [[_COMMUNITY_Tests UnitBrokers]]
- 3 edges to [[_COMMUNITY_Dhan Broker Integration_2]]
- 2 edges to [[_COMMUNITY_Tests UnitBrokers_8]]
- 2 edges to [[_COMMUNITY_Oms - Order]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers_1]]
- 1 edge to [[_COMMUNITY_Tests UnitTesting]]
- 1 edge to [[_COMMUNITY_Dhan Broker Integration_5]]
- 1 edge to [[_COMMUNITY_Dhan Broker Integration_9]]
- 1 edge to [[_COMMUNITY_Domain Events]]

## Top bridge nodes
- [[TestHistoricalDataAdapter]] - degree 59, connects to 9 communities
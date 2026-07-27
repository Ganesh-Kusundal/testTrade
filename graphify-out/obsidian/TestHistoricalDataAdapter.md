---
source_file: "tests/unit/brokers/dhan/test_adapters.py"
type: "code"
community: "Tests: Unit/Brokers"
location: "L836"
tags:
  - graphify/code
  - graphify/EXTRACTED
  - community/Tests_Unit/Brokers
---

# TestHistoricalDataAdapter

## Connections
- [[.test_should_accept_all_valid_hour_timeframes()]] - `method` [EXTRACTED]
- [[.test_should_accept_all_valid_minute_timeframes()]] - `method` [EXTRACTED]
- [[.test_should_cap_lookback_at_365_days()]] - `method` [EXTRACTED]
- [[.test_should_convert_minute_timeframes_to_minutes()]] - `method` [EXTRACTED]
- [[.test_should_encode_params_correctly()]] - `method` [EXTRACTED]
- [[.test_should_estimate_larger_lookback_for_daily_timeframe()]] - `method` [EXTRACTED]
- [[.test_should_estimate_lookback_for_minute_timeframe()]] - `method` [EXTRACTED]
- [[.test_should_fetch_latest_candles()]] - `method` [EXTRACTED]
- [[.test_should_fetch_ohlcv_and_return_parsed_candles()]] - `method` [EXTRACTED]
- [[.test_should_map_daily_weekly_monthly_timeframes_correctly()]] - `method` [EXTRACTED]
- [[.test_should_map_hour_timeframes_correctly()]] - `method` [EXTRACTED]
- [[.test_should_map_minute_timeframes_correctly()]] - `method` [EXTRACTED]
- [[.test_should_parse_iso_timestamp_with_timezone_to_utc()]] - `method` [EXTRACTED]
- [[.test_should_parse_iso_timestamp_without_timezone_as_ist()]] - `method` [EXTRACTED]
- [[.test_should_parse_single_candle_with_decimal_types()]] - `method` [EXTRACTED]
- [[.test_should_parse_unix_timestamp()]] - `method` [EXTRACTED]
- [[.test_should_raise_error_for_empty_timestamp()]] - `method` [EXTRACTED]
- [[.test_should_raise_error_for_negative_count_in_ohlcv_latest()]] - `method` [EXTRACTED]
- [[.test_should_raise_error_for_unmappable_timeframe()]] - `method` [EXTRACTED]
- [[.test_should_raise_error_for_unparseable_timestamp()]] - `method` [EXTRACTED]
- [[.test_should_raise_error_for_zero_count_in_ohlcv_latest()]] - `method` [EXTRACTED]
- [[.test_should_raise_instrument_not_found_when_resolver_fails()]] - `method` [EXTRACTED]
- [[.test_should_raise_value_error_for_empty_exchange()]] - `method` [EXTRACTED]
- [[.test_should_raise_value_error_for_empty_symbol()]] - `method` [EXTRACTED]
- [[.test_should_raise_value_error_for_invalid_timeframe_in_get_ohlcv()]] - `method` [EXTRACTED]
- [[.test_should_raise_value_error_for_whitespace_symbol()]] - `method` [EXTRACTED]
- [[.test_should_raise_value_error_when_from_date_after_to_date()]] - `method` [EXTRACTED]
- [[.test_should_raise_value_error_when_to_date_in_future()]] - `method` [EXTRACTED]
- [[.test_should_reject_unsupported_timeframe()]] - `method` [EXTRACTED]
- [[.test_should_resolve_segment_via_resolver()]] - `method` [EXTRACTED]
- [[.test_should_return_all_candles_when_fewer_than_requested()]] - `method` [EXTRACTED]
- [[.test_should_return_empty_list_for_empty_response()]] - `method` [EXTRACTED]
- [[.test_should_return_empty_list_for_missing_data_key()]] - `method` [EXTRACTED]
- [[.test_should_return_minimum_1_day()]] - `method` [EXTRACTED]
- [[.test_should_return_none_for_daily_timeframe()]] - `method` [EXTRACTED]
- [[.test_should_skip_malformed_candles_and_continue()]] - `method` [EXTRACTED]
- [[.test_should_use_historical_endpoint_for_daily_timeframe()]] - `method` [EXTRACTED]
- [[.test_should_use_historical_endpoint_for_monthly_timeframe()]] - `method` [EXTRACTED]
- [[.test_should_use_historical_endpoint_for_weekly_timeframe()]] - `method` [EXTRACTED]
- [[.test_should_use_intraday_endpoint_for_sub_daily_timeframe()]] - `method` [EXTRACTED]
- [[.test_should_validate_supported_timeframe()]] - `method` [EXTRACTED]
- [[DhanOrderResponse]] - `uses` [INFERRED]
- [[Exchange_4]] - `uses` [INFERRED]
- [[Fill]] - `uses` [INFERRED]
- [[HistoricalDataAdapter]] - `uses` [INFERRED]
- [[InstrumentNotFoundError]] - `uses` [INFERRED]
- [[MarketDataAdapter]] - `uses` [INFERRED]
- [[Order]] - `uses` [INFERRED]
- [[OrderError]] - `uses` [INFERRED]
- [[OrderSide_1]] - `uses` [INFERRED]
- [[OrderState]] - `uses` [INFERRED]
- [[OrderType]] - `uses` [INFERRED]
- [[OrdersAdapter]] - `uses` [INFERRED]
- [[PortfolioAdapter]] - `uses` [INFERRED]
- [[Position]] - `uses` [INFERRED]
- [[PositionSide]] - `uses` [INFERRED]
- [[PositionState]] - `uses` [INFERRED]
- [[Tests for HistoricalDataAdapter covering OHLCV fetching,     timeframe validatio]] - `rationale_for` [EXTRACTED]
- [[test_adapters.py]] - `contains` [EXTRACTED]

#graphify/code #graphify/EXTRACTED #community/Tests_Unit/Brokers
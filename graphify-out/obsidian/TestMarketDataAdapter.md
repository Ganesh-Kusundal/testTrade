---
source_file: "tests/unit/brokers/dhan/test_adapters.py"
type: "code"
community: "Tests: Unit/Brokers"
location: "L109"
tags:
  - graphify/code
  - graphify/INFERRED
  - community/Tests_Unit/Brokers
---

# TestMarketDataAdapter

## Connections
- [[.test_should_limit_depth_to_five_levels()]] - `method` [EXTRACTED]
- [[.test_should_make_correct_api_call_with_segment_for_market_data()]] - `method` [EXTRACTED]
- [[.test_should_raise_value_error_when_ltp_missing_for_symbol()]] - `method` [EXTRACTED]
- [[.test_should_resolve_segment_via_resolver_for_ltp()]] - `method` [EXTRACTED]
- [[.test_should_return_bids_and_asks_with_decimal_prices()]] - `method` [EXTRACTED]
- [[.test_should_return_empty_dict_when_no_symbols_resolve()]] - `method` [EXTRACTED]
- [[.test_should_return_full_quote_with_decimal_fields()]] - `method` [EXTRACTED]
- [[.test_should_return_ltp_as_decimal_when_api_returns_valid_data()]] - `method` [EXTRACTED]
- [[.test_should_return_ltp_for_multiple_symbols()]] - `method` [EXTRACTED]
- [[.test_should_return_quotes_for_multiple_symbols()]] - `method` [EXTRACTED]
- [[.test_should_return_zero_decimals_when_quote_fields_missing()]] - `method` [EXTRACTED]
- [[.test_should_skip_unresolvable_symbols_in_batch()]] - `method` [EXTRACTED]
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
- [[Tests for MarketDataAdapter covering LTP, Quote, Depth, Batch.]] - `rationale_for` [EXTRACTED]
- [[test_adapters.py]] - `contains` [EXTRACTED]

#graphify/code #graphify/INFERRED #community/Tests_Unit/Brokers
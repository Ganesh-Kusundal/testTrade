---
type: community
cohesion: 0.12
members: 18
---

# Tests: Unit/Brokers

**Cohesion:** 0.12 - loosely connected
**Members:** 18 nodes

## Members
- [[.test_should_limit_depth_to_five_levels()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_make_correct_api_call_with_segment_for_market_data()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_raise_instrument_not_found_when_resolver_fails()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_raise_order_error_when_symbol_resolution_fails()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_raise_value_error_when_ltp_missing_for_symbol()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_resolve_segment_via_resolver_for_ltp()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_return_bids_and_asks_with_decimal_prices()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_return_empty_dict_when_no_symbols_resolve()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_return_full_quote_with_decimal_fields()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_return_ltp_as_decimal_when_api_returns_valid_data()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_return_ltp_for_multiple_symbols()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_return_quotes_for_multiple_symbols()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_return_zero_decimals_when_quote_fields_missing()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_skip_unresolvable_symbols_in_batch()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[Instrument not found in resolver cache.]] - rationale - scalpr/brokers/dhan/exceptions.py
- [[InstrumentNotFoundError]] - code - scalpr/brokers/dhan/exceptions.py
- [[TestMarketDataAdapter]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[Tests for MarketDataAdapter covering LTP, Quote, Depth, Batch.]] - rationale - tests/unit/brokers/dhan/test_adapters.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Tests_Unit/Brokers
SORT file.name ASC
```

## Connections to other communities
- 6 edges to [[_COMMUNITY_Tests UnitBrokers]]
- 5 edges to [[_COMMUNITY_Dhan Broker Integration_2]]
- 3 edges to [[_COMMUNITY_Tests UnitTesting]]
- 3 edges to [[_COMMUNITY_Tests UnitBrokers_6]]
- 2 edges to [[_COMMUNITY_Dhan Broker Integration_6]]
- 2 edges to [[_COMMUNITY_Tests UnitBrokers_4]]
- 2 edges to [[_COMMUNITY_Oms - Order]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers_1]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers_7]]
- 1 edge to [[_COMMUNITY_Dhan Broker Integration_5]]
- 1 edge to [[_COMMUNITY_Dhan Broker Integration_9]]
- 1 edge to [[_COMMUNITY_Domain Events]]

## Top bridge nodes
- [[TestMarketDataAdapter]] - degree 30, connects to 8 communities
- [[InstrumentNotFoundError]] - degree 15, connects to 6 communities
- [[.test_should_raise_order_error_when_symbol_resolution_fails()]] - degree 3, connects to 1 community
- [[.test_should_raise_instrument_not_found_when_resolver_fails()]] - degree 2, connects to 1 community
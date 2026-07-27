---
type: community
cohesion: 0.06
members: 33
---

# Tests: Unit/Brokers

**Cohesion:** 0.06 - loosely connected
**Members:** 33 nodes

## Members
- [[.test_should_calculate_negative_pnl_when_long_is_loss()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_calculate_negative_pnl_when_short_is_loss()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_calculate_unrealised_pnl_for_long_position()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_calculate_unrealised_pnl_for_short_position()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_default_to_nse_for_unknown_exchange()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_derive_flat_for_zero_quantity()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_derive_long_for_positive_quantity()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_derive_short_for_negative_quantity()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_extract_list_from_data_key()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_extract_list_from_direct_list_response()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_extract_list_from_positions_key()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_filter_out_flat_positions()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_find_position_by_symbol_and_exchange()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_handle_alternate_field_names_in_fund_limits()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_handle_non_numeric_quantity_gracefully()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_handle_wrapped_position_response()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_map_short_position_correctly()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_normalise_known_exchange()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_normalise_mcx_exchange()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_return_empty_dict_on_fund_limits_error()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_return_empty_list_for_non_dict_non_list()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_return_empty_list_for_unexpected_structure()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_return_empty_list_on_api_error()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_return_empty_list_on_holdings_error()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_return_false_for_zero_quantity()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_return_fund_limits_dict()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_return_holdings_as_positions()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_return_list_of_positions()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_return_none_for_non_existent_position()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_return_true_for_non_zero_quantity()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_return_zero_pnl_for_flat_position()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[TestPortfolioAdapter]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[Tests for PortfolioAdapter covering positions, holdings,     fund limits, P&L ca]] - rationale - tests/unit/brokers/dhan/test_adapters.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Tests_Unit/Brokers
SORT file.name ASC
```

## Connections to other communities
- 6 edges to [[_COMMUNITY_Tests UnitBrokers]]
- 3 edges to [[_COMMUNITY_Dhan Broker Integration_2]]
- 2 edges to [[_COMMUNITY_Oms - Order]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers_1]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers_8]]
- 1 edge to [[_COMMUNITY_Tests UnitTesting]]
- 1 edge to [[_COMMUNITY_Dhan Broker Integration_5]]
- 1 edge to [[_COMMUNITY_Dhan Broker Integration_9]]
- 1 edge to [[_COMMUNITY_Domain Events]]

## Top bridge nodes
- [[TestPortfolioAdapter]] - degree 49, connects to 9 communities
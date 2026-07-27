---
source_file: "tests/unit/brokers/dhan/test_adapters.py"
type: "code"
community: "Tests: Unit/Brokers"
location: "L613"
tags:
  - graphify/code
  - graphify/EXTRACTED
  - community/Tests_Unit/Brokers
---

# TestPortfolioAdapter

## Connections
- [[.test_should_calculate_negative_pnl_when_long_is_loss()]] - `method` [EXTRACTED]
- [[.test_should_calculate_negative_pnl_when_short_is_loss()]] - `method` [EXTRACTED]
- [[.test_should_calculate_unrealised_pnl_for_long_position()]] - `method` [EXTRACTED]
- [[.test_should_calculate_unrealised_pnl_for_short_position()]] - `method` [EXTRACTED]
- [[.test_should_default_to_nse_for_unknown_exchange()]] - `method` [EXTRACTED]
- [[.test_should_derive_flat_for_zero_quantity()]] - `method` [EXTRACTED]
- [[.test_should_derive_long_for_positive_quantity()]] - `method` [EXTRACTED]
- [[.test_should_derive_short_for_negative_quantity()]] - `method` [EXTRACTED]
- [[.test_should_extract_list_from_data_key()]] - `method` [EXTRACTED]
- [[.test_should_extract_list_from_direct_list_response()]] - `method` [EXTRACTED]
- [[.test_should_extract_list_from_positions_key()]] - `method` [EXTRACTED]
- [[.test_should_filter_out_flat_positions()]] - `method` [EXTRACTED]
- [[.test_should_find_position_by_symbol_and_exchange()]] - `method` [EXTRACTED]
- [[.test_should_handle_alternate_field_names_in_fund_limits()]] - `method` [EXTRACTED]
- [[.test_should_handle_non_numeric_quantity_gracefully()]] - `method` [EXTRACTED]
- [[.test_should_handle_wrapped_position_response()]] - `method` [EXTRACTED]
- [[.test_should_map_short_position_correctly()]] - `method` [EXTRACTED]
- [[.test_should_normalise_known_exchange()]] - `method` [EXTRACTED]
- [[.test_should_normalise_mcx_exchange()]] - `method` [EXTRACTED]
- [[.test_should_return_empty_dict_on_fund_limits_error()]] - `method` [EXTRACTED]
- [[.test_should_return_empty_list_for_non_dict_non_list()]] - `method` [EXTRACTED]
- [[.test_should_return_empty_list_for_unexpected_structure()]] - `method` [EXTRACTED]
- [[.test_should_return_empty_list_on_api_error()]] - `method` [EXTRACTED]
- [[.test_should_return_empty_list_on_holdings_error()]] - `method` [EXTRACTED]
- [[.test_should_return_false_for_zero_quantity()]] - `method` [EXTRACTED]
- [[.test_should_return_fund_limits_dict()]] - `method` [EXTRACTED]
- [[.test_should_return_holdings_as_positions()]] - `method` [EXTRACTED]
- [[.test_should_return_list_of_positions()]] - `method` [EXTRACTED]
- [[.test_should_return_none_for_non_existent_position()]] - `method` [EXTRACTED]
- [[.test_should_return_true_for_non_zero_quantity()]] - `method` [EXTRACTED]
- [[.test_should_return_zero_pnl_for_flat_position()]] - `method` [EXTRACTED]
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
- [[Tests for PortfolioAdapter covering positions, holdings,     fund limits, P&L ca]] - `rationale_for` [EXTRACTED]
- [[test_adapters.py]] - `contains` [EXTRACTED]

#graphify/code #graphify/EXTRACTED #community/Tests_Unit/Brokers
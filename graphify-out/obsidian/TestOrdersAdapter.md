---
source_file: "tests/unit/brokers/dhan/test_adapters.py"
type: "code"
community: "Tests: Unit/Brokers"
location: "L284"
tags:
  - graphify/code
  - graphify/EXTRACTED
  - community/Tests_Unit/Brokers
---

# TestOrdersAdapter

## Connections
- [[.test_should_accept_market_order_with_zero_price()]] - `method` [EXTRACTED]
- [[.test_should_allow_new_order_with_different_correlation_id()]] - `method` [EXTRACTED]
- [[.test_should_block_duplicate_order_by_correlation_id()]] - `method` [EXTRACTED]
- [[.test_should_cancel_order_and_return_true()]] - `method` [EXTRACTED]
- [[.test_should_clear_idempotency_cache()]] - `method` [EXTRACTED]
- [[.test_should_handle_wrapped_orderbook_response()]] - `method` [EXTRACTED]
- [[.test_should_include_trigger_price_when_provided()]] - `method` [EXTRACTED]
- [[.test_should_modify_order_and_return_true()]] - `method` [EXTRACTED]
- [[.test_should_not_add_to_idempotency_cache_on_api_failure()]] - `method` [EXTRACTED]
- [[.test_should_not_construct_limit_order_with_zero_price()]] - `method` [EXTRACTED]
- [[.test_should_not_construct_order_with_negative_quantity()]] - `method` [EXTRACTED]
- [[.test_should_place_order_and_return_fill()]] - `method` [EXTRACTED]
- [[.test_should_raise_error_for_cancelled_state_order()]] - `method` [EXTRACTED]
- [[.test_should_raise_error_for_invalid_modify_quantity()]] - `method` [EXTRACTED]
- [[.test_should_raise_error_for_negative_modify_quantity()]] - `method` [EXTRACTED]
- [[.test_should_raise_error_for_terminal_state_order()]] - `method` [EXTRACTED]
- [[.test_should_raise_error_for_zero_quantity()]] - `method` [EXTRACTED]
- [[.test_should_raise_error_when_cancel_rejected()]] - `method` [EXTRACTED]
- [[.test_should_raise_error_when_modify_rejected()]] - `method` [EXTRACTED]
- [[.test_should_raise_order_error_when_mapper_fails_for_unsupported_exchange()]] - `method` [EXTRACTED]
- [[.test_should_raise_order_error_when_orderbook_fetch_fails()]] - `method` [EXTRACTED]
- [[.test_should_raise_order_error_when_response_is_rejected()]] - `method` [EXTRACTED]
- [[.test_should_raise_order_error_when_symbol_resolution_fails()]] - `method` [EXTRACTED]
- [[.test_should_raise_order_error_when_tradebook_fetch_fails()]] - `method` [EXTRACTED]
- [[.test_should_return_parsed_orderbook()]] - `method` [EXTRACTED]
- [[.test_should_return_parsed_tradebook()]] - `method` [EXTRACTED]
- [[.test_should_send_correct_payload_to_api()]] - `method` [EXTRACTED]
- [[.test_should_use_order_id_as_correlation_id_fallback()]] - `method` [EXTRACTED]
- [[.test_should_use_order_price_when_no_traded_price_in_response()]] - `method` [EXTRACTED]
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
- [[Tests for OrdersAdapter covering place, modify, cancel,     orderbook, tradebook]] - `rationale_for` [EXTRACTED]
- [[test_adapters.py]] - `contains` [EXTRACTED]

#graphify/code #graphify/EXTRACTED #community/Tests_Unit/Brokers
---
type: community
cohesion: 0.09
members: 34
---

# Tests: Unit/Brokers

**Cohesion:** 0.09 - loosely connected
**Members:** 34 nodes

## Members
- [[.test_should_accept_market_order_with_zero_price()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_allow_new_order_with_different_correlation_id()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_block_duplicate_order_by_correlation_id()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_cancel_order_and_return_true()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_clear_idempotency_cache()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_handle_wrapped_orderbook_response()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_include_trigger_price_when_provided()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_modify_order_and_return_true()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_not_add_to_idempotency_cache_on_api_failure()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_not_construct_limit_order_with_zero_price()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_not_construct_order_with_negative_quantity()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_place_order_and_return_fill()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_raise_error_for_cancelled_state_order()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_raise_error_for_invalid_modify_quantity()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_raise_error_for_negative_modify_quantity()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_raise_error_for_terminal_state_order()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_raise_error_for_zero_quantity()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_raise_error_when_cancel_rejected()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_raise_error_when_modify_rejected()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_raise_order_error_when_mapper_fails_for_unsupported_exchange()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_raise_order_error_when_orderbook_fetch_fails()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_raise_order_error_when_response_is_rejected()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_raise_order_error_when_tradebook_fetch_fails()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_return_parsed_orderbook()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_return_parsed_tradebook()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_send_correct_payload_to_api()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_use_order_id_as_correlation_id_fallback()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[.test_should_use_order_price_when_no_traded_price_in_response()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[Factory helper for Order domain objects.]] - rationale - tests/unit/brokers/dhan/test_adapters.py
- [[Order domain object prevents LIMIT order with zero price at construction.]] - rationale - tests/unit/brokers/dhan/test_adapters.py
- [[Order domain object prevents negative quantity at construction.]] - rationale - tests/unit/brokers/dhan/test_adapters.py
- [[TestOrdersAdapter]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[Tests for OrdersAdapter covering place, modify, cancel,     orderbook, tradebook]] - rationale - tests/unit/brokers/dhan/test_adapters.py
- [[make_order()]] - code - tests/unit/brokers/dhan/test_adapters.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Tests_Unit/Brokers
SORT file.name ASC
```

## Connections to other communities
- 6 edges to [[_COMMUNITY_Tests UnitBrokers]]
- 4 edges to [[_COMMUNITY_Dhan Broker Integration_2]]
- 3 edges to [[_COMMUNITY_Tests UnitBrokers_8]]
- 3 edges to [[_COMMUNITY_Oms - Order]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers_1]]
- 1 edge to [[_COMMUNITY_Tests UnitTesting]]
- 1 edge to [[_COMMUNITY_Dhan Broker Integration_5]]
- 1 edge to [[_COMMUNITY_Dhan Broker Integration_9]]
- 1 edge to [[_COMMUNITY_Domain Events]]

## Top bridge nodes
- [[TestOrdersAdapter]] - degree 47, connects to 9 communities
- [[make_order()]] - degree 20, connects to 3 communities
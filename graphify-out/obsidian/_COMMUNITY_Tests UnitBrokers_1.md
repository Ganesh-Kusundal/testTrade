---
type: community
cohesion: 0.07
members: 55
---

# Tests: Unit/Brokers

**Cohesion:** 0.07 - loosely connected
**Members:** 55 nodes

## Members
- [[.__init__()_6]] - code - scalpr/brokers/dhan/mapper.py
- [[.__init__()_50]] - code - tests/unit/brokers/test_gateway.py
- [[._validate_order()]] - code - scalpr/brokers/dhan/orders.py
- [[.dhan_position_to_domain()]] - code - scalpr/brokers/dhan/mapper.py
- [[.dhan_response_to_fill()]] - code - scalpr/brokers/dhan/mapper.py
- [[.error()]] - code - scalpr/brokers/dhan/mapper.py
- [[.failure()]] - code - scalpr/brokers/dhan/mapper.py
- [[.get()_3]] - code - tests/unit/brokers/test_gateway.py
- [[.order_to_dhan_request()]] - code - scalpr/brokers/dhan/mapper.py
- [[.place_order()_2]] - code - scalpr/brokers/dhan/orders.py
- [[.post()_1]] - code - tests/unit/brokers/test_gateway.py
- [[.success()]] - code - scalpr/brokers/dhan/mapper.py
- [[.test_mapper_uses_correct_mcx_segment()]] - code - tests/unit/brokers/dhan/test_critical_fixes.py
- [[.test_mapper_uses_correct_nse_segment()]] - code - tests/unit/brokers/dhan/test_critical_fixes.py
- [[.value()]] - code - scalpr/brokers/dhan/mapper.py
- [[Any_7]] - code
- [[DTO representing an order request payload for Dhan API.]] - rationale - scalpr/brokers/dhan/dtos.py
- [[DTO representing an order response payload from Dhan API.]] - rationale - scalpr/brokers/dhan/dtos.py
- [[Decimal_2]] - code
- [[DhanGateway delegates to orders adapter which handles retry logic.]] - rationale - tests/unit/brokers/test_gateway.py
- [[DhanGateway fails immediately without retrying on 400 Bad Request error.]] - rationale - tests/unit/brokers/test_gateway.py
- [[DhanGateway opens circuit breaker after 5 consecutive failures, fast-failing sub]] - rationale - tests/unit/brokers/test_gateway.py
- [[DhanGateway rate limiter limits calls to 25 RPS (tested here with a lower rate f]] - rationale - tests/unit/brokers/test_gateway.py
- [[DhanMapper]] - code - scalpr/brokers/dhan/mapper.py
- [[DhanMapper does not raise exceptions, returning failure Result on invalid data.]] - rationale - tests/unit/brokers/test_gateway.py
- [[DhanMapper is pure and returns identical output for identical input.]] - rationale - tests/unit/brokers/test_gateway.py
- [[DhanMapper outputs Decimal prices and quantities, never floats.]] - rationale - tests/unit/brokers/test_gateway.py
- [[DhanOrderRequest]] - code - scalpr/brokers/dhan/dtos.py
- [[DhanOrderResponse]] - code - scalpr/brokers/dhan/dtos.py
- [[E]] - code
- [[Helper to create DhanGateway with mocked connection and adapters.]] - rationale - tests/unit/brokers/test_gateway.py
- [[MCX orders must use MCX_COMM segment (not MCXCOMM).]] - rationale - tests/unit/brokers/dhan/test_critical_fixes.py
- [[MockHttpClient]] - code - tests/unit/brokers/test_gateway.py
- [[Monadic Result wrapper for pure, error-safe computations.]] - rationale - scalpr/brokers/dhan/mapper.py
- [[NSE orders must use NSE_EQ segment.]] - rationale - tests/unit/brokers/dhan/test_critical_fixes.py
- [[Orders adapter — place, modify, cancel, orderbook, tradebook.  Provides an Order]] - rationale - scalpr/brokers/dhan/orders.py
- [[Place a new order and return the resulting Fill.          Idempotency If the or]] - rationale - scalpr/brokers/dhan/orders.py
- [[Pure data transformer between Domain objects and Dhan API DTOs.]] - rationale - scalpr/brokers/dhan/mapper.py
- [[Result]] - code - scalpr/brokers/dhan/mapper.py
- [[T]] - code
- [[Validate order before submission.          Raises             OrderError If or]] - rationale - scalpr/brokers/dhan/orders.py
- [[_make_gateway()]] - code - tests/unit/brokers/test_gateway.py
- [[dtos.py]] - code - scalpr/brokers/dhan/dtos.py
- [[mapper.py]] - code - scalpr/brokers/dhan/mapper.py
- [[orders.py]] - code - scalpr/brokers/dhan/orders.py
- [[square_off_all generates selling orders for long positions and buying orders for]] - rationale - tests/unit/brokers/test_gateway.py
- [[test_gateway.py]] - code - tests/unit/brokers/test_gateway.py
- [[test_gateway_does_not_retry_on_400_bad_request()]] - code - tests/unit/brokers/test_gateway.py
- [[test_gateway_opens_circuit_after_5_failures()]] - code - tests/unit/brokers/test_gateway.py
- [[test_gateway_rate_limiter_blocks_above_25_rps()]] - code - tests/unit/brokers/test_gateway.py
- [[test_gateway_retries_on_transient_error()]] - code - tests/unit/brokers/test_gateway.py
- [[test_mapper_is_pure_same_input_same_output()]] - code - tests/unit/brokers/test_gateway.py
- [[test_mapper_price_is_decimal_not_float()]] - code - tests/unit/brokers/test_gateway.py
- [[test_mapper_raises_nothing_returns_result_type()]] - code - tests/unit/brokers/test_gateway.py
- [[test_square_off_all_calls_sell_for_all_long_positions()]] - code - tests/unit/brokers/test_gateway.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Tests_Unit/Brokers
SORT file.name ASC
```

## Connections to other communities
- 36 edges to [[_COMMUNITY_Tests UnitBrokers]]
- 34 edges to [[_COMMUNITY_Oms - Order]]
- 13 edges to [[_COMMUNITY_Dhan Broker Integration_2]]
- 10 edges to [[_COMMUNITY_Domain Events]]
- 7 edges to [[_COMMUNITY_Tests UnitTesting]]
- 2 edges to [[_COMMUNITY_Dhan Broker Integration_12]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers_4]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers_8]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers_6]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers_7]]
- 1 edge to [[_COMMUNITY_Logging System]]
- 1 edge to [[_COMMUNITY_Dhan Broker Integration_6]]

## Top bridge nodes
- [[orders.py]] - degree 23, connects to 8 communities
- [[DhanOrderResponse]] - degree 18, connects to 6 communities
- [[.place_order()_2]] - degree 10, connects to 5 communities
- [[test_gateway.py]] - degree 29, connects to 4 communities
- [[DhanMapper]] - degree 26, connects to 4 communities
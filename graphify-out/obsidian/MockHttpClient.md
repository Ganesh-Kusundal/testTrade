---
source_file: "tests/unit/brokers/test_gateway.py"
type: "code"
community: "Tests: Unit/Brokers"
location: "L14"
tags:
  - graphify/code
  - graphify/INFERRED
  - community/Tests_Unit/Brokers
---

# MockHttpClient

## Connections
- [[.__init__()_50]] - `method` [EXTRACTED]
- [[.get()_3]] - `method` [EXTRACTED]
- [[.post()_1]] - `method` [EXTRACTED]
- [[DhanGateway]] - `uses` [INFERRED]
- [[DhanMapper]] - `uses` [INFERRED]
- [[DhanOrderRequest]] - `uses` [INFERRED]
- [[DhanOrderResponse]] - `uses` [INFERRED]
- [[Exchange_4]] - `uses` [INFERRED]
- [[Fill]] - `uses` [INFERRED]
- [[Order]] - `uses` [INFERRED]
- [[OrderSide_1]] - `uses` [INFERRED]
- [[OrderState]] - `uses` [INFERRED]
- [[OrderType]] - `uses` [INFERRED]
- [[Position]] - `uses` [INFERRED]
- [[Result]] - `uses` [INFERRED]
- [[test_gateway.py]] - `contains` [EXTRACTED]
- [[test_gateway_does_not_retry_on_400_bad_request()]] - `calls` [EXTRACTED]
- [[test_gateway_opens_circuit_after_5_failures()]] - `calls` [EXTRACTED]
- [[test_gateway_rate_limiter_blocks_above_25_rps()]] - `calls` [EXTRACTED]
- [[test_gateway_retries_on_transient_error()]] - `calls` [EXTRACTED]
- [[test_square_off_all_calls_sell_for_all_long_positions()]] - `calls` [EXTRACTED]

#graphify/code #graphify/INFERRED #community/Tests_Unit/Brokers
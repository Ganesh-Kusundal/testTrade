---
source_file: "tests/unit/brokers/dhan/test_gateway_connection.py"
type: "code"
community: "Tests: Unit/Brokers"
location: "L1213"
tags:
  - graphify/code
  - graphify/INFERRED
  - community/Tests_Unit/Brokers
---

# TestDhanGatewayErrorPropagation

## Connections
- [[.test_should_propagate_broker_error_from_cancel_order()]] - `method` [EXTRACTED]
- [[.test_should_propagate_broker_error_from_get_positions()]] - `method` [EXTRACTED]
- [[.test_should_propagate_broker_error_from_place_order()]] - `method` [EXTRACTED]
- [[.test_should_raise_broker_error_when_get_order_status_order_not_found()]] - `method` [EXTRACTED]
- [[.test_should_return_order_when_get_order_status_finds_match()]] - `method` [EXTRACTED]
- [[AuthenticationError]] - `uses` [INFERRED]
- [[BrokerError]] - `uses` [INFERRED]
- [[ConfigurationError]] - `uses` [INFERRED]
- [[Dhan]] - `uses` [INFERRED]
- [[DhanConnection]] - `uses` [INFERRED]
- [[DhanGateway]] - `uses` [INFERRED]
- [[Exchange_4]] - `uses` [INFERRED]
- [[Fill]] - `uses` [INFERRED]
- [[IBrokerGateway]] - `uses` [INFERRED]
- [[Order]] - `uses` [INFERRED]
- [[OrderSide_1]] - `uses` [INFERRED]
- [[OrderState]] - `uses` [INFERRED]
- [[OrderType]] - `uses` [INFERRED]
- [[Position]] - `uses` [INFERRED]
- [[PositionSide]] - `uses` [INFERRED]
- [[Verify errors from connectionadapters propagate correctly through the gateway.]] - `rationale_for` [EXTRACTED]
- [[test_gateway_connection.py]] - `contains` [EXTRACTED]

#graphify/code #graphify/INFERRED #community/Tests_Unit/Brokers
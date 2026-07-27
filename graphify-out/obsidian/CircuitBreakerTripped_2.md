---
source_file: "scalpr/execution/order_router.py"
type: "code"
community: "Oms - Order"
location: "L27"
tags:
  - graphify/code
  - graphify/INFERRED
  - community/Oms_-_Order
---

# CircuitBreakerTripped

## Connections
- [[.submit_order()]] - `calls` [EXTRACTED]
- [[CircuitBreaker_2]] - `uses` [INFERRED]
- [[CircuitBreakerTripped_1]] - `uses` [INFERRED]
- [[Exception]] - `inherits` [EXTRACTED]
- [[Fill]] - `uses` [INFERRED]
- [[IBrokerGateway]] - `uses` [INFERRED]
- [[IEventBus]] - `uses` [INFERRED]
- [[Order]] - `uses` [INFERRED]
- [[OrderManager]] - `uses` [INFERRED]
- [[OrderPlaced]] - `uses` [INFERRED]
- [[Position]] - `uses` [INFERRED]
- [[PreTradeRiskGate]] - `uses` [INFERRED]
- [[Raised when circuit breaker prevents order submission.]] - `rationale_for` [EXTRACTED]
- [[RiskCheckFailed_1]] - `uses` [INFERRED]
- [[TestEventBusWiring]] - `uses` [INFERRED]
- [[__init__.py_5]] - `imports` [EXTRACTED]
- [[order_router.py]] - `contains` [EXTRACTED]
- [[test_event_bus_wiring.py]] - `imports` [EXTRACTED]

#graphify/code #graphify/INFERRED #community/Oms_-_Order
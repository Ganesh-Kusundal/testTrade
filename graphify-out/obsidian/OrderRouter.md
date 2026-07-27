---
source_file: "scalpr/execution/order_router.py"
type: "code"
community: "Oms - Order"
location: "L32"
tags:
  - graphify/code
  - graphify/INFERRED
  - community/Oms_-_Order
---

# OrderRouter

## Connections
- [[.__init__()_17]] - `method` [EXTRACTED]
- [[.__init__()_42]] - `references` [EXTRACTED]
- [[.submit_order()]] - `method` [EXTRACTED]
- [[.test_circuit_breaker_event_published()]] - `calls` [EXTRACTED]
- [[.test_full_event_flow_integration()]] - `calls` [EXTRACTED]
- [[.test_order_placed_event_published()]] - `calls` [EXTRACTED]
- [[.test_order_router_with_broker_failure()]] - `calls` [EXTRACTED]
- [[.test_risk_check_failed_event_published()]] - `calls` [EXTRACTED]
- [[CircuitBreaker_2]] - `uses` [INFERRED]
- [[CircuitBreakerTripped_1]] - `uses` [INFERRED]
- [[ConnectionManager]] - `uses` [INFERRED]
- [[Fill]] - `uses` [INFERRED]
- [[IBrokerGateway]] - `uses` [INFERRED]
- [[IEventBus]] - `uses` [INFERRED]
- [[Mandatory order submission router that enforces risk gates.          All strateg]] - `rationale_for` [EXTRACTED]
- [[Order]] - `uses` [INFERRED]
- [[OrderManager]] - `uses` [INFERRED]
- [[OrderPlaced]] - `uses` [INFERRED]
- [[Position]] - `uses` [INFERRED]
- [[PreTradeRiskGate]] - `uses` [INFERRED]
- [[RiskCheckFailed_1]] - `uses` [INFERRED]
- [[ScalprAmtStrategy]] - `uses` [INFERRED]
- [[TestBrokerFailureInjector]] - `uses` [INFERRED]
- [[TestChaosMonkey]] - `uses` [INFERRED]
- [[TestChaosTestSuite]] - `uses` [INFERRED]
- [[TestCircuitBreakerValidator]] - `uses` [INFERRED]
- [[TestEventBusWiring]] - `uses` [INFERRED]
- [[TestIntegrationChaosScenarios]] - `uses` [INFERRED]
- [[TestMarketDataDisruptor]] - `uses` [INFERRED]
- [[TestOrderFailureInjector]] - `uses` [INFERRED]
- [[TestPersistenceFailureInjector]] - `uses` [INFERRED]
- [[TestStrategyFaultInjector]] - `uses` [INFERRED]
- [[__init__.py_5]] - `imports` [EXTRACTED]
- [[main.py]] - `imports` [EXTRACTED]
- [[order_router.py]] - `contains` [EXTRACTED]
- [[scalpr_amt.py]] - `imports` [EXTRACTED]
- [[test_chaos.py]] - `imports` [EXTRACTED]
- [[test_event_bus_wiring.py]] - `imports` [EXTRACTED]

#graphify/code #graphify/INFERRED #community/Oms_-_Order
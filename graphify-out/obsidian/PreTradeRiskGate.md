---
source_file: "scalpr/risk/pre_trade.py"
type: "code"
community: "Oms - Order"
location: "L9"
tags:
  - graphify/code
  - graphify/INFERRED
  - community/Oms_-_Order
---

# PreTradeRiskGate

## Connections
- [[.__init__()_17]] - `references` [EXTRACTED]
- [[.__init__()_31]] - `method` [EXTRACTED]
- [[.check_order()]] - `method` [EXTRACTED]
- [[.test_circuit_breaker_event_published()]] - `calls` [EXTRACTED]
- [[.test_full_event_flow_integration()]] - `calls` [EXTRACTED]
- [[.test_order_placed_event_published()]] - `calls` [EXTRACTED]
- [[.test_risk_check_failed_event_published()]] - `calls` [EXTRACTED]
- [[CircuitBreakerTripped_2]] - `uses` [INFERRED]
- [[ConnectionManager]] - `uses` [INFERRED]
- [[Order]] - `uses` [INFERRED]
- [[OrderRouter]] - `uses` [INFERRED]
- [[OrderSide_1]] - `uses` [INFERRED]
- [[Position]] - `uses` [INFERRED]
- [[PositionSide]] - `uses` [INFERRED]
- [[Pre-trade risk gateway that validates order submission against account limits.]] - `rationale_for` [EXTRACTED]
- [[RiskCheckFailed_2]] - `uses` [INFERRED]
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
- [[main.py]] - `imports` [EXTRACTED]
- [[order_router.py]] - `imports` [EXTRACTED]
- [[pre_trade.py]] - `contains` [EXTRACTED]
- [[test_chaos.py]] - `imports` [EXTRACTED]
- [[test_event_bus_wiring.py]] - `imports` [EXTRACTED]
- [[test_oms_risk.py]] - `imports` [EXTRACTED]
- [[test_pre_trade_risk_gate()]] - `calls` [EXTRACTED]

#graphify/code #graphify/INFERRED #community/Oms_-_Order
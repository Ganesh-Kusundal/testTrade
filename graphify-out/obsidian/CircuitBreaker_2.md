---
source_file: "scalpr/risk/circuit_breaker.py"
type: "code"
community: "Tests: Unit/Testing"
location: "L9"
tags:
  - graphify/code
  - graphify/EXTRACTED
  - community/Tests_Unit/Testing
---

# CircuitBreaker

## Connections
- [[.__init__()_29]] - `method` [EXTRACTED]
- [[.check_limits()]] - `method` [EXTRACTED]
- [[.halt_all()]] - `method` [EXTRACTED]
- [[.is_tripped()]] - `method` [EXTRACTED]
- [[.reset()]] - `method` [EXTRACTED]
- [[.state()]] - `method` [EXTRACTED]
- [[.test_circuit_breaker_event_published()]] - `calls` [EXTRACTED]
- [[.test_daily_loss_trip()]] - `calls` [EXTRACTED]
- [[.test_drawdown_trip()]] - `calls` [EXTRACTED]
- [[.test_full_event_flow_integration()]] - `calls` [EXTRACTED]
- [[.test_manual_halt()]] - `calls` [EXTRACTED]
- [[.test_order_placed_event_published()]] - `calls` [EXTRACTED]
- [[.test_order_router_with_broker_failure()]] - `calls` [EXTRACTED]
- [[.test_risk_check_failed_event_published()]] - `calls` [EXTRACTED]
- [[BrokerFailureInjector]] - `uses` [INFERRED]
- [[ChaosMonkey]] - `uses` [INFERRED]
- [[ChaosTestSuite]] - `uses` [INFERRED]
- [[CircuitBreakerTripped_2]] - `uses` [INFERRED]
- [[CircuitBreakerValidator]] - `uses` [INFERRED]
- [[ConnectionManager]] - `uses` [INFERRED]
- [[MarketDataDisruptor]] - `uses` [INFERRED]
- [[OrderFailureInjector]] - `uses` [INFERRED]
- [[OrderRouter]] - `uses` [INFERRED]
- [[PersistenceFailureInjector]] - `uses` [INFERRED]
- [[RiskCheckFailed_2]] - `uses` [INFERRED]
- [[StrategyFaultInjector]] - `uses` [INFERRED]
- [[System-level Circuit Breakers for Daily Loss, Drawdown limits, and manual Halt s]] - `rationale_for` [EXTRACTED]
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
- [[chaos.py]] - `imports` [EXTRACTED]
- [[circuit_breaker.py]] - `contains` [EXTRACTED]
- [[main.py]] - `imports` [EXTRACTED]
- [[order_router.py]] - `imports` [EXTRACTED]
- [[test_chaos.py]] - `imports` [EXTRACTED]
- [[test_circuit_breaker_limits()]] - `calls` [EXTRACTED]
- [[test_event_bus_wiring.py]] - `imports` [EXTRACTED]
- [[test_oms_risk.py]] - `imports` [EXTRACTED]

#graphify/code #graphify/EXTRACTED #community/Tests_Unit/Testing
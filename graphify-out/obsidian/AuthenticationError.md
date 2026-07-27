---
source_file: "scalpr/brokers/dhan/exceptions.py"
type: "code"
community: "Tests: Unit/Testing"
location: "L29"
tags:
  - graphify/code
  - graphify/INFERRED
  - community/Tests_Unit/Testing
---

# AuthenticationError

## Connections
- [[._request()]] - `calls` [EXTRACTED]
- [[.test_should_re_raise_authentication_error_without_wrapping()]] - `calls` [EXTRACTED]
- [[BrokerError]] - `inherits` [EXTRACTED]
- [[BrokerFailureInjector]] - `uses` [INFERRED]
- [[ChaosMonkey]] - `uses` [INFERRED]
- [[ChaosTestSuite]] - `uses` [INFERRED]
- [[CircuitBreaker]] - `uses` [INFERRED]
- [[CircuitBreakerValidator]] - `uses` [INFERRED]
- [[DhanConnection]] - `uses` [INFERRED]
- [[DhanHttpClient]] - `uses` [INFERRED]
- [[DhanWebSocketClient]] - `uses` [INFERRED]
- [[MarketDataDisruptor]] - `uses` [INFERRED]
- [[OrderFailureInjector]] - `uses` [INFERRED]
- [[PersistenceFailureInjector]] - `uses` [INFERRED]
- [[StrategyFaultInjector]] - `uses` [INFERRED]
- [[TestBrokerFailureInjector]] - `uses` [INFERRED]
- [[TestChaosMonkey]] - `uses` [INFERRED]
- [[TestChaosTestSuite]] - `uses` [INFERRED]
- [[TestCircuitBreakerValidator]] - `uses` [INFERRED]
- [[TestDhanConnectionAdapterProperties]] - `uses` [INFERRED]
- [[TestDhanConnectionConfigValidation]] - `uses` [INFERRED]
- [[TestDhanConnectionHttpClientConfig]] - `uses` [INFERRED]
- [[TestDhanConnectionLifecycle]] - `uses` [INFERRED]
- [[TestDhanConnectionStateTracking]] - `uses` [INFERRED]
- [[TestDhanConnectionThreadSafety]] - `uses` [INFERRED]
- [[TestDhanConnectionTokenRefresh]] - `uses` [INFERRED]
- [[TestDhanGatewayConnectionProperty]] - `uses` [INFERRED]
- [[TestDhanGatewayErrorPropagation]] - `uses` [INFERRED]
- [[TestDhanGatewayFullDelegationChain]] - `uses` [INFERRED]
- [[TestDhanGatewayHistoricalDelegation]] - `uses` [INFERRED]
- [[TestDhanGatewayInterfaceCompliance]] - `uses` [INFERRED]
- [[TestDhanGatewayLifecycleDelegation]] - `uses` [INFERRED]
- [[TestDhanGatewayMarketDataDelegation]] - `uses` [INFERRED]
- [[TestDhanGatewayOrderDelegation]] - `uses` [INFERRED]
- [[TestDhanGatewayOrderMapping]] - `uses` [INFERRED]
- [[TestDhanGatewayPortfolioDelegation]] - `uses` [INFERRED]
- [[TestDhanGatewaySquareOff]] - `uses` [INFERRED]
- [[TestIntegrationChaosScenarios]] - `uses` [INFERRED]
- [[TestMarketDataDisruptor]] - `uses` [INFERRED]
- [[TestOrderFailureInjector]] - `uses` [INFERRED]
- [[TestPersistenceFailureInjector]] - `uses` [INFERRED]
- [[TestStrategyFaultInjector]] - `uses` [INFERRED]
- [[Token expired or rejected.]] - `rationale_for` [EXTRACTED]
- [[_DhanContextShim]] - `uses` [INFERRED]
- [[_SubscriptionKey]] - `uses` [INFERRED]
- [[chaos.py]] - `imports` [EXTRACTED]
- [[connection.py]] - `imports` [EXTRACTED]
- [[exceptions.py]] - `contains` [EXTRACTED]
- [[http_client.py]] - `imports` [EXTRACTED]
- [[test_chaos.py]] - `imports` [EXTRACTED]
- [[test_gateway_connection.py]] - `imports` [EXTRACTED]
- [[ws_client.py]] - `imports` [EXTRACTED]

#graphify/code #graphify/INFERRED #community/Tests_Unit/Testing
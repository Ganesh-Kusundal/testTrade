---
type: community
cohesion: 0.04
members: 118
---

# Tests: Unit/Testing

**Cohesion:** 0.04 - loosely connected
**Members:** 118 nodes

## Members
- [[.__init__()_16]] - code - scalpr/domain/events.py
- [[.__init__()_44]] - code - scalpr/testing/chaos.py
- [[.__init__()_43]] - code - scalpr/testing/chaos.py
- [[.__init__()_45]] - code - scalpr/testing/chaos.py
- [[.__init__()_46]] - code - scalpr/testing/chaos.py
- [[.cancel_order()_2]] - code - scalpr/brokers/dhan/orders.py
- [[.close()_1]] - code - scalpr/brokers/dhan/http_client.py
- [[.get_order_status()_1]] - code - scalpr/brokers/dhan/gateway.py
- [[.is_tripped()]] - code - scalpr/risk/circuit_breaker.py
- [[.test_crashing_strategy()]] - code - tests/unit/testing/test_chaos.py
- [[.test_deterministic_with_seed()]] - code - tests/unit/testing/test_chaos.py
- [[.test_disconnect_websocket_context_manager()]] - code - tests/unit/testing/test_chaos.py
- [[.test_event_store_with_db_locked()]] - code - tests/unit/testing/test_chaos.py
- [[.test_generate_malformed_ticks()]] - code - tests/unit/testing/test_chaos.py
- [[.test_generate_out_of_order_ticks()]] - code - tests/unit/testing/test_chaos.py
- [[.test_generate_stale_ticks()]] - code - tests/unit/testing/test_chaos.py
- [[.test_inject_http_error_after_calls()]] - code - tests/unit/testing/test_chaos.py
- [[.test_inject_latency_spike()]] - code - tests/unit/testing/test_chaos.py
- [[.test_inject_order_rejection()]] - code - tests/unit/testing/test_chaos.py
- [[.test_inject_partial_fills()]] - code - tests/unit/testing/test_chaos.py
- [[.test_inject_rate_limit()]] - code - tests/unit/testing/test_chaos.py
- [[.test_inject_timeout()]] - code - tests/unit/testing/test_chaos.py
- [[.test_inject_token_expiration()]] - code - tests/unit/testing/test_chaos.py
- [[.test_order_router_with_broker_failure()]] - code - tests/unit/testing/test_chaos.py
- [[.test_patch_broker_http_context_manager()]] - code - tests/unit/testing/test_chaos.py
- [[.test_should_fail_when_disabled()]] - code - tests/unit/testing/test_chaos.py
- [[.test_should_fail_with_probability_one()]] - code - tests/unit/testing/test_chaos.py
- [[.test_should_fail_with_probability_zero()]] - code - tests/unit/testing/test_chaos.py
- [[.test_should_propagate_broker_error_from_cancel_order()]] - code - tests/unit/brokers/dhan/test_gateway_connection.py
- [[.test_should_propagate_broker_error_from_get_positions()]] - code - tests/unit/brokers/dhan/test_gateway_connection.py
- [[.test_should_propagate_broker_error_from_place_order()]] - code - tests/unit/brokers/dhan/test_gateway_connection.py
- [[.test_simulate_db_locked()]] - code - tests/unit/testing/test_chaos.py
- [[.test_simulate_disk_full()]] - code - tests/unit/testing/test_chaos.py
- [[AuthenticationError]] - code - scalpr/brokers/dhan/exceptions.py
- [[Base chaos monkey for injecting failures into the trading system.          Inspi]] - rationale - scalpr/testing/chaos.py
- [[Base exception for all broker errors.]] - rationale - scalpr/brokers/dhan/exceptions.py
- [[BrokerError]] - code - scalpr/brokers/dhan/exceptions.py
- [[BrokerError from cancel_order must propagate.]] - rationale - tests/unit/brokers/dhan/test_gateway_connection.py
- [[BrokerError from get_positions must propagate.]] - rationale - tests/unit/brokers/dhan/test_gateway_connection.py
- [[BrokerError from orders adapter must propagate through gateway.]] - rationale - tests/unit/brokers/dhan/test_gateway_connection.py
- [[BrokerFailureInjector]] - code - scalpr/testing/chaos.py
- [[Cancel an active order.          Args             order_id Dhan order ID to ca_1]] - rationale - scalpr/brokers/dhan/orders.py
- [[Chaos testing infrastructure for SCALPR trading platform.  Provides fault inject]] - rationale - scalpr/testing/chaos.py
- [[Chaos testing validation for SCALPR trading platform.  Tests system resilience u]] - rationale - tests/unit/testing/test_chaos.py
- [[ChaosMonkey]] - code - scalpr/testing/chaos.py
- [[CircuitBreaker_2]] - code - scalpr/risk/circuit_breaker.py
- [[CircuitBreaker trips on exceeding daily loss or drawdown limits and halts all ex]] - rationale - tests/unit/oms/test_oms_risk.py
- [[CircuitBreakerValidator]] - code - scalpr/testing/chaos.py
- [[Dhan broker exceptions.  All exceptions inherit from BrokerError for consistent]] - rationale - scalpr/brokers/dhan/exceptions.py
- [[Dhan connection orchestrator — lifecycle management and adapter coordination.  C]] - rationale - scalpr/brokers/dhan/connection.py
- [[DhanHttpClient]] - code - scalpr/brokers/dhan/http_client.py
- [[Fetch the current status of an order from the orderbook.          Retrieves the]] - rationale - scalpr/brokers/dhan/gateway.py
- [[HTTP client for Dhan REST API with retry, rate limiting, and circuit breaker.  A]] - rationale - scalpr/brokers/dhan/http_client.py
- [[Historical data adapter for Dhan REST API.  Provides methods for fetching histor]] - rationale - scalpr/brokers/dhan/historical.py
- [[InMemoryEventBus]] - code - scalpr/domain/events.py
- [[Inject broker API failures for resilience testing.          Scenarios     - HTT]] - rationale - scalpr/testing/chaos.py
- [[Inject market data feed failures.          Scenarios     - WebSocket disconnect]] - rationale - scalpr/testing/chaos.py
- [[Inject order execution failures.          Scenarios     - Order rejection (insu]] - rationale - scalpr/testing/chaos.py
- [[Inject persistence layer failures.          Scenarios     - SQLite database loc]] - rationale - scalpr/testing/chaos.py
- [[Inject strategy execution faults.          Scenarios     - Strategy timeout (sl]] - rationale - scalpr/testing/chaos.py
- [[Integration tests for chaos scenarios with real components.]] - rationale - tests/unit/testing/test_chaos.py
- [[MarketDataDisruptor]] - code - scalpr/testing/chaos.py
- [[Order placementmodificationcancellation failure.]] - rationale - scalpr/brokers/dhan/exceptions.py
- [[OrderError]] - code - scalpr/brokers/dhan/exceptions.py
- [[OrderFailureInjector]] - code - scalpr/testing/chaos.py
- [[PersistenceFailureInjector]] - code - scalpr/testing/chaos.py
- [[RateLimitError]] - code - scalpr/brokers/dhan/exceptions.py
- [[Simple in-process event bus for single-machine deployment.]] - rationale - scalpr/domain/events.py
- [[StrategyFaultInjector]] - code - scalpr/testing/chaos.py
- [[Sync HTTP client for Dhan API with retry, rate limiting, and circuit breaker.]] - rationale - scalpr/brokers/dhan/http_client.py
- [[System-level Circuit Breakers for Daily Loss, Drawdown limits, and manual Halt s]] - rationale - scalpr/risk/circuit_breaker.py
- [[Test EventStore handles database locked gracefully.]] - rationale - tests/unit/testing/test_chaos.py
- [[Test HTTP error injection after N calls.]] - rationale - tests/unit/testing/test_chaos.py
- [[Test OrderRouter handles broker failures gracefully.]] - rationale - tests/unit/testing/test_chaos.py
- [[Test WebSocket disconnection simulation.]] - rationale - tests/unit/testing/test_chaos.py
- [[Test base chaos monkey functionality.]] - rationale - tests/unit/testing/test_chaos.py
- [[Test broker API failure injection.]] - rationale - tests/unit/testing/test_chaos.py
- [[Test circuit breaker chaos validation.]] - rationale - tests/unit/testing/test_chaos.py
- [[Test complete chaos test suite.]] - rationale - tests/unit/testing/test_chaos.py
- [[Test context manager patches HTTP correctly.]] - rationale - tests/unit/testing/test_chaos.py
- [[Test crashing strategy.]] - rationale - tests/unit/testing/test_chaos.py
- [[Test database locked simulation.]] - rationale - tests/unit/testing/test_chaos.py
- [[Test disk full simulation.]] - rationale - tests/unit/testing/test_chaos.py
- [[Test latency spike injection.]] - rationale - tests/unit/testing/test_chaos.py
- [[Test malformed tick generation.]] - rationale - tests/unit/testing/test_chaos.py
- [[Test market data disruption scenarios.]] - rationale - tests/unit/testing/test_chaos.py
- [[Test order failure injection.]] - rationale - tests/unit/testing/test_chaos.py
- [[Test order rejection injection.]] - rationale - tests/unit/testing/test_chaos.py
- [[Test out-of-order tick generation.]] - rationale - tests/unit/testing/test_chaos.py
- [[Test partial fill injection.]] - rationale - tests/unit/testing/test_chaos.py
- [[Test persistence layer failure injection.]] - rationale - tests/unit/testing/test_chaos.py
- [[Test rate limiting injection.]] - rationale - tests/unit/testing/test_chaos.py
- [[Test stale tick generation.]] - rationale - tests/unit/testing/test_chaos.py
- [[Test strategy fault injection.]] - rationale - tests/unit/testing/test_chaos.py
- [[Test that disabled monkey never fails.]] - rationale - tests/unit/testing/test_chaos.py
- [[Test that probability 0.0 never fails.]] - rationale - tests/unit/testing/test_chaos.py
- [[Test that probability 1.0 always fails.]] - rationale - tests/unit/testing/test_chaos.py
- [[Test that same seed produces same failures.]] - rationale - tests/unit/testing/test_chaos.py
- [[Test timeout injection.]] - rationale - tests/unit/testing/test_chaos.py
- [[Test token expiration injection.]] - rationale - tests/unit/testing/test_chaos.py
- [[TestBrokerFailureInjector]] - code - tests/unit/testing/test_chaos.py
- [[TestChaosMonkey]] - code - tests/unit/testing/test_chaos.py
- [[TestChaosTestSuite]] - code - tests/unit/testing/test_chaos.py
- [[TestCircuitBreakerValidator]] - code - tests/unit/testing/test_chaos.py
- [[TestIntegrationChaosScenarios]] - code - tests/unit/testing/test_chaos.py
- [[TestMarketDataDisruptor]] - code - tests/unit/testing/test_chaos.py
- [[TestOrderFailureInjector]] - code - tests/unit/testing/test_chaos.py
- [[TestPersistenceFailureInjector]] - code - tests/unit/testing/test_chaos.py
- [[TestStrategyFaultInjector]] - code - tests/unit/testing/test_chaos.py
- [[Token expired or rejected.]] - rationale - scalpr/brokers/dhan/exceptions.py
- [[Validate circuit breaker behavior under chaos conditions.]] - rationale - scalpr/testing/chaos.py
- [[chaos.py]] - code - scalpr/testing/chaos.py
- [[connection.py]] - code - scalpr/brokers/dhan/connection.py
- [[exceptions.py]] - code - scalpr/brokers/dhan/exceptions.py
- [[historical.py]] - code - scalpr/brokers/dhan/historical.py
- [[http_client.py]] - code - scalpr/brokers/dhan/http_client.py
- [[test_chaos.py]] - code - tests/unit/testing/test_chaos.py
- [[test_circuit_breaker_limits()]] - code - tests/unit/oms/test_oms_risk.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Tests_Unit/Testing
SORT file.name ASC
```

## Connections to other communities
- 123 edges to [[_COMMUNITY_Tests UnitBrokers]]
- 72 edges to [[_COMMUNITY_Oms - Order]]
- 37 edges to [[_COMMUNITY_Chaos Testing]]
- 30 edges to [[_COMMUNITY_Domain Events]]
- 27 edges to [[_COMMUNITY_Dhan Broker Integration_2]]
- 21 edges to [[_COMMUNITY_Dhan Broker Integration_4]]
- 19 edges to [[_COMMUNITY_Market - Data]]
- 19 edges to [[_COMMUNITY_Simulation - Replay]]
- 18 edges to [[_COMMUNITY_Backtester]]
- 18 edges to [[_COMMUNITY_Market - Data_2]]
- 7 edges to [[_COMMUNITY_Tests UnitBrokers_1]]
- 6 edges to [[_COMMUNITY_Tests UnitBrokers_3]]
- 6 edges to [[_COMMUNITY_Dhan Broker Integration_6]]
- 6 edges to [[_COMMUNITY_Dhan Broker Integration_3]]
- 5 edges to [[_COMMUNITY_Dhan Broker Integration_5]]
- 4 edges to [[_COMMUNITY_Logging System]]
- 4 edges to [[_COMMUNITY_Dhan Broker Integration_9]]
- 4 edges to [[_COMMUNITY_Scripts - Test - Dhan]]
- 3 edges to [[_COMMUNITY_Dhan Broker Integration_10]]
- 3 edges to [[_COMMUNITY_Tests UnitBrokers_8]]
- 3 edges to [[_COMMUNITY_Dhan Broker Integration_12]]
- 2 edges to [[_COMMUNITY_Configuration_2]]
- 2 edges to [[_COMMUNITY_API Server]]
- 2 edges to [[_COMMUNITY_Dhan Broker Integration_7]]
- 2 edges to [[_COMMUNITY_Market - Data_1]]
- 2 edges to [[_COMMUNITY_Risk - Circuit]]
- 1 edge to [[_COMMUNITY_Dhan Broker Integration_19]]
- 1 edge to [[_COMMUNITY_Dhan Broker Integration_13]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers_4]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers_6]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers_7]]
- 1 edge to [[_COMMUNITY_Dhan Broker Integration_1]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers_41]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers_2]]
- 1 edge to [[_COMMUNITY_Risk - Circuit_1]]
- 1 edge to [[_COMMUNITY_Risk - Circuit_2]]
- 1 edge to [[_COMMUNITY_Risk - Circuit_3]]
- 1 edge to [[_COMMUNITY_Chaos Testing_4]]
- 1 edge to [[_COMMUNITY_Chaos Testing_1]]
- 1 edge to [[_COMMUNITY_Chaos Testing_2]]
- 1 edge to [[_COMMUNITY_Chaos Testing_3]]
- 1 edge to [[_COMMUNITY_Chaos Testing_5]]
- 1 edge to [[_COMMUNITY_Chaos Testing_6]]
- 1 edge to [[_COMMUNITY_Chaos Testing_7]]
- 1 edge to [[_COMMUNITY_Chaos Testing_8]]
- 1 edge to [[_COMMUNITY_Chaos Testing_9]]
- 1 edge to [[_COMMUNITY_Chaos Testing_10]]
- 1 edge to [[_COMMUNITY_Chaos Testing_12]]
- 1 edge to [[_COMMUNITY_Chaos Testing_13]]
- 1 edge to [[_COMMUNITY_Chaos Testing_11]]

## Top bridge nodes
- [[BrokerError]] - degree 77, connects to 15 communities
- [[connection.py]] - degree 28, connects to 13 communities
- [[OrderFailureInjector]] - degree 30, connects to 10 communities
- [[DhanHttpClient]] - degree 45, connects to 9 communities
- [[test_chaos.py]] - degree 43, connects to 9 communities
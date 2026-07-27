---
source_file: "scalpr/observability/event_store.py"
type: "code"
community: "Domain Events"
location: "L223"
tags:
  - graphify/code
  - graphify/INFERRED
  - community/Domain_Events
---

# EventStore

## Connections
- [[.__init__()_23]] - `method` [EXTRACTED]
- [[._init_db()]] - `method` [EXTRACTED]
- [[.append()]] - `method` [EXTRACTED]
- [[.compact()]] - `method` [EXTRACTED]
- [[.delete_session()]] - `method` [EXTRACTED]
- [[.event_store()]] - `calls` [EXTRACTED]
- [[.get_event_count()]] - `method` [EXTRACTED]
- [[.get_latest_sequence()]] - `method` [EXTRACTED]
- [[.get_session_events()]] - `method` [EXTRACTED]
- [[.setup_replay()]] - `calls` [EXTRACTED]
- [[.test_event_store_with_db_locked()]] - `calls` [EXTRACTED]
- [[.test_persistence_across_instances()]] - `calls` [EXTRACTED]
- [[BarClosed]] - `uses` [INFERRED]
- [[CircuitBreakerTripped_1]] - `uses` [INFERRED]
- [[ConnectionManager]] - `uses` [INFERRED]
- [[DomainEvent]] - `uses` [INFERRED]
- [[Exchange_4]] - `uses` [INFERRED]
- [[Fill]] - `uses` [INFERRED]
- [[FillReceived]] - `uses` [INFERRED]
- [[GateFailed]] - `uses` [INFERRED]
- [[HistoricalDataLoaded]] - `uses` [INFERRED]
- [[Order]] - `uses` [INFERRED]
- [[OrderCancelled]] - `uses` [INFERRED]
- [[OrderExpired]] - `uses` [INFERRED]
- [[OrderModified]] - `uses` [INFERRED]
- [[OrderPlaced]] - `uses` [INFERRED]
- [[OrderRejected]] - `uses` [INFERRED]
- [[OrderSide_1]] - `uses` [INFERRED]
- [[OrderState]] - `uses` [INFERRED]
- [[OrderType]] - `uses` [INFERRED]
- [[OrderUpdated]] - `uses` [INFERRED]
- [[Persistent event store backed by SQLite.          Provides     - Append-only ev]] - `rationale_for` [EXTRACTED]
- [[Position]] - `uses` [INFERRED]
- [[PositionClosed]] - `uses` [INFERRED]
- [[PositionOpened]] - `uses` [INFERRED]
- [[PositionReversed]] - `uses` [INFERRED]
- [[PositionSide]] - `uses` [INFERRED]
- [[PositionUpdated]] - `uses` [INFERRED]
- [[RiskCheckFailed_1]] - `uses` [INFERRED]
- [[RiskCheckPassed]] - `uses` [INFERRED]
- [[SessionHalted]] - `uses` [INFERRED]
- [[Signal]] - `uses` [INFERRED]
- [[SignalGenerated]] - `uses` [INFERRED]
- [[SignalType]] - `uses` [INFERRED]
- [[TestBrokerFailureInjector]] - `uses` [INFERRED]
- [[TestChaosMonkey]] - `uses` [INFERRED]
- [[TestChaosTestSuite]] - `uses` [INFERRED]
- [[TestCircuitBreakerValidator]] - `uses` [INFERRED]
- [[TestEventStore]] - `uses` [INFERRED]
- [[TestIntegrationChaosScenarios]] - `uses` [INFERRED]
- [[TestMarketDataDisruptor]] - `uses` [INFERRED]
- [[TestOrderFailureInjector]] - `uses` [INFERRED]
- [[TestPersistenceFailureInjector]] - `uses` [INFERRED]
- [[TestReplayEngineWithEvents]] - `uses` [INFERRED]
- [[TestStrategyFaultInjector]] - `uses` [INFERRED]
- [[Tick]] - `uses` [INFERRED]
- [[TickReceived]] - `uses` [INFERRED]
- [[event_store.py]] - `contains` [EXTRACTED]
- [[main.py]] - `imports` [EXTRACTED]
- [[test_chaos.py]] - `imports` [EXTRACTED]
- [[test_event_store.py]] - `imports` [EXTRACTED]

#graphify/code #graphify/INFERRED #community/Domain_Events
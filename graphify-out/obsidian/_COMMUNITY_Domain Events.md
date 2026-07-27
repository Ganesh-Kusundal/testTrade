---
type: community
cohesion: 0.06
members: 95
---

# Domain Events

**Cohesion:** 0.06 - loosely connected
**Members:** 95 nodes

## Members
- [[.__init__()]] - code - scalpr/api/main.py
- [[.__post_init__()]] - code - scalpr/domain/events.py
- [[.__post_init__()_1]] - code - scalpr/domain/fill.py
- [[.__post_init__()_6]] - code - scalpr/domain/signal.py
- [[.get_tradebook()]] - code - scalpr/brokers/broker_port.py
- [[.place_order()]] - code - scalpr/brokers/broker_port.py
- [[.publish()]] - code - scalpr/domain/events.py
- [[.publish()_1]] - code - scalpr/domain/events.py
- [[.save_fill()]] - code - scalpr/oms/persistence.py
- [[.square_off_all()]] - code - scalpr/brokers/broker_port.py
- [[.subscribe()_4]] - code - scalpr/domain/events.py
- [[.subscribe()_5]] - code - scalpr/domain/events.py
- [[.test_load_from_events_filters_non_ticks()]] - code - tests/unit/observability/test_event_store.py
- [[.test_multiple_event_subscribers()]] - code - tests/unit/test_event_bus_wiring.py
- [[.test_tick_received_event_published()]] - code - tests/unit/test_event_bus_wiring.py
- [[.unsubscribe()_4]] - code - scalpr/domain/events.py
- [[.unsubscribe()_5]] - code - scalpr/domain/events.py
- [[A standard execution fill.]] - rationale - tests/unit/brokers/dhan/test_gateway_connection.py
- [[All prices must be Decimal. Passing float raises TypeError.]] - rationale - tests/unit/domain/test_domain.py
- [[BarClosed]] - code - scalpr/domain/events.py
- [[Base class for all domain events. Immutable with UTC timestamp.]] - rationale - scalpr/domain/events.py
- [[CircuitBreakerTripped_1]] - code - scalpr/domain/events.py
- [[ConnectionManager]] - code - scalpr/api/main.py
- [[Domain events for the SCALPR trading system.  All events are frozen dataclasses]] - rationale - scalpr/domain/events.py
- [[DomainEvent]] - code - scalpr/domain/events.py
- [[Event published when a circuit breaker is tripped.]] - rationale - scalpr/domain/events.py
- [[Event published when a market tick is received.]] - rationale - scalpr/domain/events.py
- [[Event published when a new OHLCV bar is closed.]] - rationale - scalpr/domain/events.py
- [[Event published when a new order is submitted.]] - rationale - scalpr/domain/events.py
- [[Event published when a new position is opened.]] - rationale - scalpr/domain/events.py
- [[Event published when a position is fully closed.]] - rationale - scalpr/domain/events.py
- [[Event published when a position is reversed (long→short or vice versa).]] - rationale - scalpr/domain/events.py
- [[Event published when a position is updated (e.g., quantity change).]] - rationale - scalpr/domain/events.py
- [[Event published when a risk check fails.]] - rationale - scalpr/domain/events.py
- [[Event published when a risk check passes.]] - rationale - scalpr/domain/events.py
- [[Event published when a signal gate fails.]] - rationale - scalpr/domain/events.py
- [[Event published when a trading signal is generated.]] - rationale - scalpr/domain/events.py
- [[Event published when an execution fill is received.]] - rationale - scalpr/domain/events.py
- [[Event published when an order expires.]] - rationale - scalpr/domain/events.py
- [[Event published when an order is cancelled.]] - rationale - scalpr/domain/events.py
- [[Event published when an order is modified.]] - rationale - scalpr/domain/events.py
- [[Event published when an order is rejected by broker.]] - rationale - scalpr/domain/events.py
- [[Event published when an order is updated (e.g., state change).]] - rationale - scalpr/domain/events.py
- [[Event published when historical data is loaded.]] - rationale - scalpr/domain/events.py
- [[Event published when trading session is halted.]] - rationale - scalpr/domain/events.py
- [[EventStore]] - code - scalpr/observability/event_store.py
- [[Execution fill details.]] - rationale - scalpr/domain/fill.py
- [[Fetch the day's tradebook (execution fills).]] - rationale - scalpr/brokers/broker_port.py
- [[Fill]] - code - scalpr/domain/fill.py
- [[FillReceived]] - code - scalpr/domain/events.py
- [[Gate]] - code - scalpr/domain/signal.py
- [[GateFailed]] - code - scalpr/domain/events.py
- [[HistoricalDataLoaded]] - code - scalpr/domain/events.py
- [[Manages active WebSockets connections and broadcasts streaming messages.]] - rationale - scalpr/api/main.py
- [[OrderCancelled]] - code - scalpr/domain/events.py
- [[OrderExpired]] - code - scalpr/domain/events.py
- [[OrderModified]] - code - scalpr/domain/events.py
- [[OrderPlaced]] - code - scalpr/domain/events.py
- [[OrderRejected]] - code - scalpr/domain/events.py
- [[OrderUpdated]] - code - scalpr/domain/events.py
- [[Persist an execution fill.]] - rationale - scalpr/oms/persistence.py
- [[Persistent event store backed by SQLite.          Provides     - Append-only ev]] - rationale - scalpr/observability/event_store.py
- [[Persistent event store for event replay and audit trail.  Stores all domain even]] - rationale - scalpr/observability/event_store.py
- [[Place an order and return the resulting execution Fill.]] - rationale - scalpr/brokers/broker_port.py
- [[PositionClosed]] - code - scalpr/domain/events.py
- [[PositionOpened]] - code - scalpr/domain/events.py
- [[PositionReversed]] - code - scalpr/domain/events.py
- [[PositionUpdated]] - code - scalpr/domain/events.py
- [[Publish an event to all subscribers.]] - rationale - scalpr/domain/events.py
- [[RiskCheckFailed_1]] - code - scalpr/domain/events.py
- [[RiskCheckPassed]] - code - scalpr/domain/events.py
- [[SessionHalted]] - code - scalpr/domain/events.py
- [[Signal]] - code - scalpr/domain/signal.py
- [[Signal generation filter gate status.]] - rationale - scalpr/domain/signal.py
- [[SignalGenerated]] - code - scalpr/domain/events.py
- [[SignalType]] - code - scalpr/domain/signal.py
- [[Square off all current positions and return execution Fills.]] - rationale - scalpr/brokers/broker_port.py
- [[Subscribe to events of a specific type.]] - rationale - scalpr/domain/events.py
- [[Test ReplayEngine integration with EventStore.]] - rationale - tests/unit/observability/test_event_store.py
- [[Test that only tick events are loaded.]] - rationale - tests/unit/observability/test_event_store.py
- [[TestReplayEngineWithEvents]] - code - tests/unit/observability/test_event_store.py
- [[Tests for EventStore and replay integration.]] - rationale - tests/unit/observability/test_event_store.py
- [[TickReceived]] - code - scalpr/domain/events.py
- [[Trading signal indicating setup detection.]] - rationale - scalpr/domain/signal.py
- [[Unsubscribe from events of a specific type.]] - rationale - scalpr/domain/events.py
- [[Verify TickReceived event is published when tick callback fires.]] - rationale - tests/unit/test_event_bus_wiring.py
- [[Verify multiple subscribers can listen to the same event type.]] - rationale - tests/unit/test_event_bus_wiring.py
- [[__init__.py_4]] - code - scalpr/domain/__init__.py
- [[callable]] - code
- [[event_store.py]] - code - scalpr/observability/event_store.py
- [[events.py]] - code - scalpr/domain/events.py
- [[sample_fill()]] - code - tests/unit/brokers/dhan/test_gateway_connection.py
- [[signal.py]] - code - scalpr/domain/signal.py
- [[test_event_store.py]] - code - tests/unit/observability/test_event_store.py
- [[test_fill_price_is_decimal_not_float()]] - code - tests/unit/domain/test_domain.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Domain_Events
SORT file.name ASC
```

## Connections to other communities
- 128 edges to [[_COMMUNITY_Oms - Order]]
- 56 edges to [[_COMMUNITY_Tests UnitBrokers]]
- 37 edges to [[_COMMUNITY_Market - Data]]
- 30 edges to [[_COMMUNITY_Tests UnitTesting]]
- 23 edges to [[_COMMUNITY_API Server]]
- 23 edges to [[_COMMUNITY_Backtester]]
- 19 edges to [[_COMMUNITY_Tests UnitObservability]]
- 11 edges to [[_COMMUNITY_Observability - Event]]
- 10 edges to [[_COMMUNITY_Tests UnitBrokers_1]]
- 9 edges to [[_COMMUNITY_Simulation - Replay]]
- 7 edges to [[_COMMUNITY_Dhan Broker Integration_2]]
- 7 edges to [[_COMMUNITY_Oms - Paper]]
- 5 edges to [[_COMMUNITY_API Server_3]]
- 4 edges to [[_COMMUNITY_API Server_2]]
- 4 edges to [[_COMMUNITY_Portfolio Management]]
- 3 edges to [[_COMMUNITY_Market - Data_1]]
- 2 edges to [[_COMMUNITY_Signals - Gate]]
- 2 edges to [[_COMMUNITY_Dhan Broker Integration_13]]
- 2 edges to [[_COMMUNITY_Tests UnitBrokers_2]]
- 2 edges to [[_COMMUNITY_Scanner - Options]]
- 2 edges to [[_COMMUNITY_Logging System]]
- 2 edges to [[_COMMUNITY_Tests UnitOms]]
- 2 edges to [[_COMMUNITY_Observability - Event_1]]
- 1 edge to [[_COMMUNITY_API Server_10]]
- 1 edge to [[_COMMUNITY_API Server_11]]
- 1 edge to [[_COMMUNITY_API Server_1]]
- 1 edge to [[_COMMUNITY_Dhan Broker Integration]]
- 1 edge to [[_COMMUNITY_Chaos Testing]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers_4]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers_8]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers_6]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers_7]]
- 1 edge to [[_COMMUNITY_Observability - Event_2]]
- 1 edge to [[_COMMUNITY_Observability - Event_3]]
- 1 edge to [[_COMMUNITY_Observability - Event_4]]
- 1 edge to [[_COMMUNITY_Observability - Event_5]]
- 1 edge to [[_COMMUNITY_Tests UnitObservability_4]]
- 1 edge to [[_COMMUNITY_Tests UnitObservability_3]]

## Top bridge nodes
- [[Fill]] - degree 122, connects to 19 communities
- [[EventStore]] - degree 61, connects to 13 communities
- [[ConnectionManager]] - degree 37, connects to 11 communities
- [[__init__.py_4]] - degree 47, connects to 8 communities
- [[events.py]] - degree 45, connects to 7 communities
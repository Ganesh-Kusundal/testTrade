---
source_file: "scalpr/domain/events.py"
type: "code"
community: "Domain Events"
location: "L121"
tags:
  - graphify/code
  - graphify/EXTRACTED
  - community/Domain_Events
---

# TickReceived

## Connections
- [[._create_tick_event()]] - `references` [EXTRACTED]
- [[.test_event_immutability()]] - `calls` [EXTRACTED]
- [[.test_full_event_flow_integration()]] - `calls` [EXTRACTED]
- [[.test_load_from_events()]] - `calls` [EXTRACTED]
- [[.test_load_from_events_filters_non_ticks()]] - `calls` [EXTRACTED]
- [[.test_multiple_event_subscribers()]] - `calls` [EXTRACTED]
- [[.test_persistence_across_instances()]] - `calls` [EXTRACTED]
- [[.test_replay_from_event_store()]] - `calls` [EXTRACTED]
- [[.test_tick_received_event_published()]] - `calls` [EXTRACTED]
- [[ConnectionManager]] - `uses` [INFERRED]
- [[DomainEvent]] - `inherits` [EXTRACTED]
- [[Event published when a market tick is received.]] - `rationale_for` [EXTRACTED]
- [[EventStore]] - `uses` [INFERRED]
- [[Fill]] - `uses` [INFERRED]
- [[OHLCV]] - `uses` [INFERRED]
- [[Order]] - `uses` [INFERRED]
- [[Position]] - `uses` [INFERRED]
- [[Signal]] - `uses` [INFERRED]
- [[TestEventBusWiring]] - `uses` [INFERRED]
- [[TestEventStore]] - `uses` [INFERRED]
- [[TestReplayEngineWithEvents]] - `uses` [INFERRED]
- [[Tick]] - `uses` [INFERRED]
- [[__init__.py_4]] - `imports` [EXTRACTED]
- [[_on_tick_received()]] - `references` [EXTRACTED]
- [[event_store.py]] - `imports` [EXTRACTED]
- [[events.py]] - `contains` [EXTRACTED]
- [[feed_on_tick_callback()]] - `calls` [EXTRACTED]
- [[main.py]] - `imports` [EXTRACTED]
- [[test_event_bus_wiring.py]] - `imports` [EXTRACTED]
- [[test_event_store.py]] - `imports` [EXTRACTED]

#graphify/code #graphify/EXTRACTED #community/Domain_Events
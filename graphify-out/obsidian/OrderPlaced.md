---
source_file: "scalpr/domain/events.py"
type: "code"
community: "Domain Events"
location: "L45"
tags:
  - graphify/code
  - graphify/EXTRACTED
  - community/Domain_Events
---

# OrderPlaced

## Connections
- [[._create_order_event()]] - `references` [EXTRACTED]
- [[.submit_order()]] - `calls` [EXTRACTED]
- [[.test_load_from_events_filters_non_ticks()]] - `calls` [EXTRACTED]
- [[CircuitBreakerTripped_2]] - `uses` [INFERRED]
- [[ConnectionManager]] - `uses` [INFERRED]
- [[DomainEvent]] - `inherits` [EXTRACTED]
- [[Event published when a new order is submitted.]] - `rationale_for` [EXTRACTED]
- [[EventStore]] - `uses` [INFERRED]
- [[Fill]] - `uses` [INFERRED]
- [[OHLCV]] - `uses` [INFERRED]
- [[Order]] - `uses` [INFERRED]
- [[OrderRouter]] - `uses` [INFERRED]
- [[Position]] - `uses` [INFERRED]
- [[RiskCheckFailed_2]] - `uses` [INFERRED]
- [[Signal]] - `uses` [INFERRED]
- [[TestEventBusWiring]] - `uses` [INFERRED]
- [[TestEventStore]] - `uses` [INFERRED]
- [[TestReplayEngineWithEvents]] - `uses` [INFERRED]
- [[Tick]] - `uses` [INFERRED]
- [[__init__.py_4]] - `imports` [EXTRACTED]
- [[_on_order_placed()]] - `references` [EXTRACTED]
- [[_ws_broadcast_order_placed()]] - `references` [EXTRACTED]
- [[_ws_on_order_placed_sync()]] - `references` [EXTRACTED]
- [[event_store.py]] - `imports` [EXTRACTED]
- [[events.py]] - `contains` [EXTRACTED]
- [[main.py]] - `imports` [EXTRACTED]
- [[order_router.py]] - `imports` [EXTRACTED]
- [[test_domain.py]] - `imports` [EXTRACTED]
- [[test_event_bus_wiring.py]] - `imports` [EXTRACTED]
- [[test_event_store.py]] - `imports` [EXTRACTED]

#graphify/code #graphify/EXTRACTED #community/Domain_Events
---
source_file: "tests/unit/observability/test_event_store.py"
type: "code"
community: "Tests: Unit/Observability"
location: "L29"
tags:
  - graphify/code
  - graphify/INFERRED
  - community/Tests_Unit/Observability
---

# TestEventStore

## Connections
- [[._create_order_event()]] - `method` [EXTRACTED]
- [[._create_tick_event()]] - `method` [EXTRACTED]
- [[.event_store()]] - `method` [EXTRACTED]
- [[.test_append_and_retrieve_single_event()]] - `method` [EXTRACTED]
- [[.test_append_multiple_events_preserves_sequence()]] - `method` [EXTRACTED]
- [[.test_delete_session()]] - `method` [EXTRACTED]
- [[.test_error_handling_invalid_event_type()]] - `method` [EXTRACTED]
- [[.test_event_round_trip_complex_event()]] - `method` [EXTRACTED]
- [[.test_filter_by_event_type()]] - `method` [EXTRACTED]
- [[.test_get_latest_sequence()]] - `method` [EXTRACTED]
- [[.test_multiple_sessions_isolated()]] - `method` [EXTRACTED]
- [[.test_persistence_across_instances()]] - `method` [EXTRACTED]
- [[.test_range_query()]] - `method` [EXTRACTED]
- [[CircuitBreakerTripped_1]] - `uses` [INFERRED]
- [[DomainEvent]] - `uses` [INFERRED]
- [[EventStore]] - `uses` [INFERRED]
- [[Exchange_4]] - `uses` [INFERRED]
- [[Fill]] - `uses` [INFERRED]
- [[FillReceived]] - `uses` [INFERRED]
- [[Order]] - `uses` [INFERRED]
- [[OrderCancelled]] - `uses` [INFERRED]
- [[OrderPlaced]] - `uses` [INFERRED]
- [[OrderSide_1]] - `uses` [INFERRED]
- [[OrderState]] - `uses` [INFERRED]
- [[OrderType]] - `uses` [INFERRED]
- [[ReplayEngine]] - `uses` [INFERRED]
- [[SessionHalted]] - `uses` [INFERRED]
- [[Signal]] - `uses` [INFERRED]
- [[SignalGenerated]] - `uses` [INFERRED]
- [[SignalType]] - `uses` [INFERRED]
- [[StrategyExecutor]] - `uses` [INFERRED]
- [[Test EventStore persistence and retrieval.]] - `rationale_for` [EXTRACTED]
- [[Tick]] - `uses` [INFERRED]
- [[TickReceived]] - `uses` [INFERRED]
- [[test_event_store.py]] - `contains` [EXTRACTED]

#graphify/code #graphify/INFERRED #community/Tests_Unit/Observability
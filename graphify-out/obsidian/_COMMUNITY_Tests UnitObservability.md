---
type: community
cohesion: 0.10
members: 26
---

# Tests: Unit/Observability

**Cohesion:** 0.10 - loosely connected
**Members:** 26 nodes

## Members
- [[._create_order_event()]] - code - tests/unit/observability/test_event_store.py
- [[._create_tick_event()]] - code - tests/unit/observability/test_event_store.py
- [[.event_store()]] - code - tests/unit/observability/test_event_store.py
- [[.test_append_and_retrieve_single_event()]] - code - tests/unit/observability/test_event_store.py
- [[.test_append_multiple_events_preserves_sequence()]] - code - tests/unit/observability/test_event_store.py
- [[.test_delete_session()]] - code - tests/unit/observability/test_event_store.py
- [[.test_error_handling_invalid_event_type()]] - code - tests/unit/observability/test_event_store.py
- [[.test_event_round_trip_complex_event()]] - code - tests/unit/observability/test_event_store.py
- [[.test_filter_by_event_type()]] - code - tests/unit/observability/test_event_store.py
- [[.test_get_latest_sequence()]] - code - tests/unit/observability/test_event_store.py
- [[.test_multiple_sessions_isolated()]] - code - tests/unit/observability/test_event_store.py
- [[.test_persistence_across_instances()]] - code - tests/unit/observability/test_event_store.py
- [[.test_range_query()]] - code - tests/unit/observability/test_event_store.py
- [[Create temporary event store for testing.]] - rationale - tests/unit/observability/test_event_store.py
- [[Test EventStore persistence and retrieval.]] - rationale - tests/unit/observability/test_event_store.py
- [[Test basic event append and retrieve.]] - rationale - tests/unit/observability/test_event_store.py
- [[Test deleting all events for a session.]] - rationale - tests/unit/observability/test_event_store.py
- [[Test filtering events by type.]] - rationale - tests/unit/observability/test_event_store.py
- [[Test getting latest sequence number.]] - rationale - tests/unit/observability/test_event_store.py
- [[Test graceful handling of unknown event types.]] - rationale - tests/unit/observability/test_event_store.py
- [[Test retrieving events within a sequence range.]] - rationale - tests/unit/observability/test_event_store.py
- [[Test serializationdeserialization of complex events.]] - rationale - tests/unit/observability/test_event_store.py
- [[Test that different sessions have isolated event streams.]] - rationale - tests/unit/observability/test_event_store.py
- [[Test that events maintain sequence order.]] - rationale - tests/unit/observability/test_event_store.py
- [[Test that events persist across EventStore instances.]] - rationale - tests/unit/observability/test_event_store.py
- [[TestEventStore]] - code - tests/unit/observability/test_event_store.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Tests_Unit/Observability
SORT file.name ASC
```

## Connections to other communities
- 19 edges to [[_COMMUNITY_Domain Events]]
- 4 edges to [[_COMMUNITY_Tests UnitBrokers]]
- 3 edges to [[_COMMUNITY_Market - Data]]
- 2 edges to [[_COMMUNITY_Oms - Order]]
- 2 edges to [[_COMMUNITY_Simulation - Replay]]

## Top bridge nodes
- [[TestEventStore]] - degree 35, connects to 5 communities
- [[._create_tick_event()]] - degree 10, connects to 2 communities
- [[._create_order_event()]] - degree 5, connects to 2 communities
- [[.test_persistence_across_instances()]] - degree 5, connects to 2 communities
- [[.event_store()]] - degree 3, connects to 1 community
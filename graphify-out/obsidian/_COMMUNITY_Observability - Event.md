---
type: community
cohesion: 0.19
members: 13
---

# Observability - Event

**Cohesion:** 0.19 - loosely connected
**Members:** 13 nodes

## Members
- [[.append()]] - code - scalpr/observability/event_store.py
- [[.get_session_events()]] - code - scalpr/observability/event_store.py
- [[Any_15]] - code
- [[Append event to store. Returns sequence number.                  Thread-safe. Ap]] - rationale - scalpr/observability/event_store.py
- [[Deserialize JSON dict back to domain event.]] - rationale - scalpr/observability/event_store.py
- [[Get events for a session in sequence order.                  Args             s]] - rationale - scalpr/observability/event_store.py
- [[Reconstruct domain object from dict.]] - rationale - scalpr/observability/event_store.py
- [[Serialize domain event to JSON-compatible dict.]] - rationale - scalpr/observability/event_store.py
- [[Serialize domain object (Order, Fill, Tick, etc.) to dict.]] - rationale - scalpr/observability/event_store.py
- [[_deserialize_event()]] - code - scalpr/observability/event_store.py
- [[_reconstruct_domain_object()]] - code - scalpr/observability/event_store.py
- [[_serialize_domain_object()]] - code - scalpr/observability/event_store.py
- [[_serialize_event()]] - code - scalpr/observability/event_store.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Observability_-_Event
SORT file.name ASC
```

## Connections to other communities
- 11 edges to [[_COMMUNITY_Domain Events]]
- 1 edge to [[_COMMUNITY_Oms - Order]]
- 1 edge to [[_COMMUNITY_Market - Data]]

## Top bridge nodes
- [[_reconstruct_domain_object()]] - degree 7, connects to 3 communities
- [[_deserialize_event()]] - degree 6, connects to 1 community
- [[_serialize_event()]] - degree 6, connects to 1 community
- [[.append()]] - degree 5, connects to 1 community
- [[.get_session_events()]] - degree 5, connects to 1 community
---
type: community
cohesion: 1.00
members: 2
---

# Observability - Event

**Cohesion:** 1.00 - tightly connected
**Members:** 2 nodes

## Members
- [[.delete_session()]] - code - scalpr/observability/event_store.py
- [[Delete all events for a session. Returns deleted count.]] - rationale - scalpr/observability/event_store.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Observability_-_Event
SORT file.name ASC
```

## Connections to other communities
- 1 edge to [[_COMMUNITY_Domain Events]]

## Top bridge nodes
- [[.delete_session()]] - degree 2, connects to 1 community
---
type: community
cohesion: 0.67
members: 3
---

# Observability - Event

**Cohesion:** 0.67 - moderately connected
**Members:** 3 nodes

## Members
- [[.__init__()_23]] - code - scalpr/observability/event_store.py
- [[._init_db()]] - code - scalpr/observability/event_store.py
- [[Initialize event store schema.]] - rationale - scalpr/observability/event_store.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Observability_-_Event
SORT file.name ASC
```

## Connections to other communities
- 2 edges to [[_COMMUNITY_Domain Events]]

## Top bridge nodes
- [[._init_db()]] - degree 3, connects to 1 community
- [[.__init__()_23]] - degree 2, connects to 1 community
---
type: community
cohesion: 1.00
members: 2
---

# Observability - Event

**Cohesion:** 1.00 - tightly connected
**Members:** 2 nodes

## Members
- [[.compact()]] - code - scalpr/observability/event_store.py
- [[Compact old events. Returns deleted count.                  Args             ma]] - rationale - scalpr/observability/event_store.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Observability_-_Event
SORT file.name ASC
```

## Connections to other communities
- 1 edge to [[_COMMUNITY_Domain Events]]

## Top bridge nodes
- [[.compact()]] - degree 2, connects to 1 community
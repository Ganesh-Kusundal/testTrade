---
type: community
cohesion: 0.50
members: 4
---

# API Server

**Cohesion:** 0.50 - moderately connected
**Members:** 4 nodes

## Members
- [[.get_trace_id()]] - code - scalpr/observability/tracing.py
- [[Get current trace ID from context.]] - rationale - scalpr/observability/tracing.py
- [[Persist domain events to EventStore for replay and audit.]] - rationale - scalpr/api/main.py
- [[_persist_event_to_store()]] - code - scalpr/api/main.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/API_Server
SORT file.name ASC
```

## Connections to other communities
- 1 edge to [[_COMMUNITY_API Server]]
- 1 edge to [[_COMMUNITY_API Server_1]]
- 1 edge to [[_COMMUNITY_Tracing]]

## Top bridge nodes
- [[_persist_event_to_store()]] - degree 4, connects to 2 communities
- [[.get_trace_id()]] - degree 3, connects to 1 community
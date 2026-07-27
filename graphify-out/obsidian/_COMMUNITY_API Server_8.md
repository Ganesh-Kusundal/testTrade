---
type: community
cohesion: 1.00
members: 2
---

# API Server

**Cohesion:** 1.00 - tightly connected
**Members:** 2 nodes

## Members
- [[Return session risk state circuit breaker status, halt state.]] - rationale - scalpr/api/main.py
- [[get_risk_session()]] - code - scalpr/api/main.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/API_Server
SORT file.name ASC
```

## Connections to other communities
- 1 edge to [[_COMMUNITY_API Server]]

## Top bridge nodes
- [[get_risk_session()]] - degree 2, connects to 1 community
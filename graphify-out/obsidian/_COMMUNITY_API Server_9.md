---
type: community
cohesion: 1.00
members: 2
---

# API Server

**Cohesion:** 1.00 - tightly connected
**Members:** 2 nodes

## Members
- [[Return active strategies and their current state.]] - rationale - scalpr/api/main.py
- [[get_strategy_status()]] - code - scalpr/api/main.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/API_Server
SORT file.name ASC
```

## Connections to other communities
- 1 edge to [[_COMMUNITY_API Server]]

## Top bridge nodes
- [[get_strategy_status()]] - degree 2, connects to 1 community
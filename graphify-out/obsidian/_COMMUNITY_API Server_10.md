---
type: community
cohesion: 1.00
members: 2
---

# API Server

**Cohesion:** 1.00 - tightly connected
**Members:** 2 nodes

## Members
- [[Log order placement for audit trail.]] - rationale - scalpr/api/main.py
- [[_on_order_placed()]] - code - scalpr/api/main.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/API_Server
SORT file.name ASC
```

## Connections to other communities
- 1 edge to [[_COMMUNITY_API Server]]
- 1 edge to [[_COMMUNITY_Domain Events]]

## Top bridge nodes
- [[_on_order_placed()]] - degree 3, connects to 2 communities
---
type: community
cohesion: 1.00
members: 2
---

# Domain Order Model

**Cohesion:** 1.00 - tightly connected
**Members:** 2 nodes

## Members
- [[.is_active()]] - code - scalpr/domain/order.py
- [[Return True if order is in a non-terminal state.]] - rationale - scalpr/domain/order.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Domain_Order_Model
SORT file.name ASC
```

## Connections to other communities
- 1 edge to [[_COMMUNITY_Oms - Order]]

## Top bridge nodes
- [[.is_active()]] - degree 2, connects to 1 community
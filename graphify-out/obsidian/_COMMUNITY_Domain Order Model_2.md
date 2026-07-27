---
type: community
cohesion: 1.00
members: 2
---

# Domain Order Model

**Cohesion:** 1.00 - tightly connected
**Members:** 2 nodes

## Members
- [[.remaining_quantity()]] - code - scalpr/domain/order.py
- [[Return unfilled quantity.]] - rationale - scalpr/domain/order.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Domain_Order_Model
SORT file.name ASC
```

## Connections to other communities
- 1 edge to [[_COMMUNITY_Oms - Order]]

## Top bridge nodes
- [[.remaining_quantity()]] - degree 2, connects to 1 community
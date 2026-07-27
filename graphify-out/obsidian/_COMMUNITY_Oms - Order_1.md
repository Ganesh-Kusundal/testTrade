---
type: community
cohesion: 1.00
members: 2
---

# Oms - Order

**Cohesion:** 1.00 - tightly connected
**Members:** 2 nodes

## Members
- [[.restore_state()]] - code - scalpr/oms/order_manager.py
- [[Restore orders and fills from persistence (crash recovery).]] - rationale - scalpr/oms/order_manager.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Oms_-_Order
SORT file.name ASC
```

## Connections to other communities
- 1 edge to [[_COMMUNITY_Oms - Order]]

## Top bridge nodes
- [[.restore_state()]] - degree 2, connects to 1 community
---
type: community
cohesion: 0.40
members: 5
---

# Domain Order Model

**Cohesion:** 0.40 - moderately connected
**Members:** 5 nodes

## Members
- [[.fill_ratio()]] - code - scalpr/domain/order.py
- [[.notional_value()]] - code - scalpr/domain/order.py
- [[Decimal_8]] - code
- [[Return price  quantity as Decimal.]] - rationale - scalpr/domain/order.py
- [[Return ratio of filled to total quantity.]] - rationale - scalpr/domain/order.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Domain_Order_Model
SORT file.name ASC
```

## Connections to other communities
- 3 edges to [[_COMMUNITY_Oms - Order]]

## Top bridge nodes
- [[.fill_ratio()]] - degree 3, connects to 1 community
- [[.notional_value()]] - degree 3, connects to 1 community
- [[Decimal_8]] - degree 3, connects to 1 community
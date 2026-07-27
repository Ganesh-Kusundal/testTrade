---
type: community
cohesion: 0.17
members: 12
---

# Domain Position Model

**Cohesion:** 0.17 - loosely connected
**Members:** 12 nodes

## Members
- [[.is_reducing()]] - code - scalpr/domain/position.py
- [[.notional_value()_1]] - code - scalpr/domain/position.py
- [[.total_pnl()]] - code - scalpr/domain/position.py
- [[.with_fill()]] - code - scalpr/domain/position.py
- [[.with_ltp()]] - code - scalpr/domain/position.py
- [[Calculate updated position state after applying a signed fill quantity.]] - rationale - scalpr/domain/position.py
- [[Check if a fill would reduce this position's exposure.]] - rationale - scalpr/domain/position.py
- [[Decimal_9]] - code
- [[Mark-to-market position with updated LTP and return new Position copy.]] - rationale - scalpr/domain/position.py
- [[OrderSide_2]] - code
- [[Return abs(quantity)  ltp as Decimal.]] - rationale - scalpr/domain/position.py
- [[Return total PnL (realised + unrealised).]] - rationale - scalpr/domain/position.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Domain_Position_Model
SORT file.name ASC
```

## Connections to other communities
- 6 edges to [[_COMMUNITY_Oms - Order]]

## Top bridge nodes
- [[Decimal_9]] - degree 5, connects to 1 community
- [[.with_fill()]] - degree 4, connects to 1 community
- [[.is_reducing()]] - degree 3, connects to 1 community
- [[.notional_value()_1]] - degree 3, connects to 1 community
- [[.total_pnl()]] - degree 3, connects to 1 community
---
type: community
cohesion: 0.15
members: 20
---

# Oms - Paper

**Cohesion:** 0.15 - loosely connected
**Members:** 20 nodes

## Members
- [[.__init__()_26]] - code - scalpr/oms/paper_oms.py
- [[._recalculate_peak_drawdown()]] - code - scalpr/oms/paper_oms.py
- [[.cancel_order()_3]] - code - scalpr/oms/paper_oms.py
- [[.daily_pnl()]] - code - scalpr/oms/paper_oms.py
- [[.drawdown()]] - code - scalpr/oms/paper_oms.py
- [[.get_margins()_2]] - code - scalpr/oms/paper_oms.py
- [[.get_order_status()_2]] - code - scalpr/oms/paper_oms.py
- [[.get_positions()_3]] - code - scalpr/oms/paper_oms.py
- [[.is_connected()_8]] - code - scalpr/oms/paper_oms.py
- [[.modify_order()_3]] - code - scalpr/oms/paper_oms.py
- [[.place_order()_3]] - code - scalpr/oms/paper_oms.py
- [[.set_last_price()]] - code - scalpr/oms/paper_oms.py
- [[.square_off_all()_2]] - code - scalpr/oms/paper_oms.py
- [[Calculate aggregate PnL (realised + unrealised) across all positions.]] - rationale - scalpr/oms/paper_oms.py
- [[Current drawdown from peak balance.]] - rationale - scalpr/oms/paper_oms.py
- [[Decimal_11]] - code
- [[Paper Trading OMS simulating order executions, slippage, and tracking paper port]] - rationale - scalpr/oms/paper_oms.py
- [[PaperOms]] - code - scalpr/oms/paper_oms.py
- [[Update last known price (used for market fills and mark-to-market).]] - rationale - scalpr/oms/paper_oms.py
- [[replace_order_state()]] - code - scalpr/oms/paper_oms.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Oms_-_Paper
SORT file.name ASC
```

## Connections to other communities
- 21 edges to [[_COMMUNITY_Oms - Order]]
- 7 edges to [[_COMMUNITY_Domain Events]]
- 6 edges to [[_COMMUNITY_Tests UnitBrokers]]
- 3 edges to [[_COMMUNITY_Backtester]]
- 2 edges to [[_COMMUNITY_Broker Registry]]
- 2 edges to [[_COMMUNITY_Signals - Gate]]
- 1 edge to [[_COMMUNITY_Dhan Broker Integration_2]]

## Top bridge nodes
- [[PaperOms]] - degree 42, connects to 7 communities
- [[.place_order()_3]] - degree 10, connects to 2 communities
- [[replace_order_state()]] - degree 5, connects to 2 communities
- [[.square_off_all()_2]] - degree 4, connects to 2 communities
- [[Decimal_11]] - degree 9, connects to 1 community
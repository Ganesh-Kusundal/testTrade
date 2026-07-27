---
type: community
cohesion: 0.18
members: 16
---

# Portfolio Management

**Cohesion:** 0.18 - loosely connected
**Members:** 16 nodes

## Members
- [[.__init__()_28]] - code - scalpr/portfolio/portfolio.py
- [[._update_peak_equity()]] - code - scalpr/portfolio/portfolio.py
- [[.total_pnl()_1]] - code - scalpr/portfolio/portfolio.py
- [[.total_realised_pnl()]] - code - scalpr/portfolio/portfolio.py
- [[.total_unrealised_pnl()]] - code - scalpr/portfolio/portfolio.py
- [[.update_ltp()]] - code - scalpr/portfolio/portfolio.py
- [[.update_position_from_fill()]] - code - scalpr/portfolio/portfolio.py
- [[Any_16]] - code
- [[Apply a new fill transaction to update position averages and realized pnl.]] - rationale - scalpr/portfolio/portfolio.py
- [[Decimal_13]] - code
- [[Manages aggregate portfolio state, marks-to-market positions, and tracks session]] - rationale - scalpr/portfolio/portfolio.py
- [[Mark positions to market on new price ticks.]] - rationale - scalpr/portfolio/portfolio.py
- [[PortfolioManager]] - code - scalpr/portfolio/portfolio.py
- [[PortfolioManager marks positions to market and tracks realizedunrealized PnL.]] - rationale - tests/unit/strategy_sim/test_strategy_sim.py
- [[portfolio.py_1]] - code - scalpr/portfolio/portfolio.py
- [[test_portfolio_manager_realised_pnl()]] - code - tests/unit/strategy_sim/test_strategy_sim.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Portfolio_Management
SORT file.name ASC
```

## Connections to other communities
- 5 edges to [[_COMMUNITY_Oms - Order]]
- 4 edges to [[_COMMUNITY_Domain Events]]
- 4 edges to [[_COMMUNITY_Market - Data]]
- 3 edges to [[_COMMUNITY_Signals - Gate]]
- 1 edge to [[_COMMUNITY_Market - Data_1]]

## Top bridge nodes
- [[portfolio.py_1]] - degree 9, connects to 5 communities
- [[PortfolioManager]] - degree 14, connects to 4 communities
- [[test_portfolio_manager_realised_pnl()]] - degree 5, connects to 3 communities
- [[.update_position_from_fill()]] - degree 7, connects to 2 communities
- [[.update_ltp()]] - degree 4, connects to 1 community
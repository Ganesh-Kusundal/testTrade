---
type: community
cohesion: 0.27
members: 10
---

# Portfolio Analytics

**Cohesion:** 0.27 - loosely connected
**Members:** 10 nodes

## Members
- [[.calculate_max_drawdown()]] - code - scalpr/portfolio/analytics.py
- [[.calculate_sharpe_ratio()]] - code - scalpr/portfolio/analytics.py
- [[.calculate_win_rate()]] - code - scalpr/portfolio/analytics.py
- [[Calculate Sharpe Ratio for portfolio returns.]] - rationale - scalpr/portfolio/analytics.py
- [[Calculate win rate as percentage of winning trades.]] - rationale - scalpr/portfolio/analytics.py
- [[Compute the maximum peak-to-trough drawdown from an equity curve series.]] - rationale - scalpr/portfolio/analytics.py
- [[Computes attribution, Sharpe ratio, win rate, and drawdown series for portfolio]] - rationale - scalpr/portfolio/analytics.py
- [[Decimal_12]] - code
- [[TradeAnalytics]] - code - scalpr/portfolio/analytics.py
- [[analytics.py]] - code - scalpr/portfolio/analytics.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Portfolio_Analytics
SORT file.name ASC
```

## Connections to other communities
- 2 edges to [[_COMMUNITY_Signals - Gate]]

## Top bridge nodes
- [[TradeAnalytics]] - degree 6, connects to 1 community
- [[analytics.py]] - degree 3, connects to 1 community
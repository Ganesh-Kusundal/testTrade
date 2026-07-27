---
type: community
cohesion: 0.50
members: 4
---

# Dhan Broker Integration

**Cohesion:** 0.50 - moderately connected
**Members:** 4 nodes

## Members
- [[.get_fund_limits()_1]] - code - scalpr/brokers/dhan/gateway.py
- [[.get_margins()_1]] - code - scalpr/brokers/dhan/gateway.py
- [[Fetch available margin limits and fund details.          Alias for get_margins()]] - rationale - scalpr/brokers/dhan/gateway.py
- [[Fetch available margin limits and fund details.          Delegates to PortfolioA]] - rationale - scalpr/brokers/dhan/gateway.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Dhan_Broker_Integration
SORT file.name ASC
```

## Connections to other communities
- 2 edges to [[_COMMUNITY_Tests UnitBrokers]]

## Top bridge nodes
- [[.get_fund_limits()_1]] - degree 3, connects to 1 community
- [[.get_margins()_1]] - degree 3, connects to 1 community
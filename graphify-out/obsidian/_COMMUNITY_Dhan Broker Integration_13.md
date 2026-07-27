---
type: community
cohesion: 0.33
members: 6
---

# Dhan Broker Integration

**Cohesion:** 0.33 - loosely connected
**Members:** 6 nodes

## Members
- [[.get_positions()_1]] - code - scalpr/brokers/dhan/gateway.py
- [[.place_order()_1]] - code - scalpr/brokers/dhan/gateway.py
- [[.square_off_all()_1]] - code - scalpr/brokers/dhan/gateway.py
- [[Fetch current open positions.          Delegates to PortfolioAdapter.get_positio]] - rationale - scalpr/brokers/dhan/gateway.py
- [[Place a new order and return the resulting Fill.          Delegates to OrdersAda]] - rationale - scalpr/brokers/dhan/gateway.py
- [[Square off all current open positions with market orders.          For each open]] - rationale - scalpr/brokers/dhan/gateway.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Dhan_Broker_Integration
SORT file.name ASC
```

## Connections to other communities
- 3 edges to [[_COMMUNITY_Tests UnitBrokers]]
- 3 edges to [[_COMMUNITY_Oms - Order]]
- 2 edges to [[_COMMUNITY_Domain Events]]
- 1 edge to [[_COMMUNITY_Tests UnitTesting]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers_2]]

## Top bridge nodes
- [[.square_off_all()_1]] - degree 8, connects to 5 communities
- [[.place_order()_1]] - degree 5, connects to 3 communities
- [[.get_positions()_1]] - degree 4, connects to 2 communities
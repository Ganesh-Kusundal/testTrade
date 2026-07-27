---
type: community
cohesion: 0.29
members: 8
---

# Dhan Broker Integration

**Cohesion:** 0.29 - loosely connected
**Members:** 8 nodes

## Members
- [[.get_orderbook()]] - code - scalpr/brokers/dhan/orders.py
- [[.get_tradebook()_2]] - code - scalpr/brokers/dhan/orders.py
- [[.modify_order()_2]] - code - scalpr/brokers/dhan/orders.py
- [[Any_9]] - code
- [[Decimal_4]] - code
- [[Fetch the day's orderbook from Dhan.          Returns             List of order]] - rationale - scalpr/brokers/dhan/orders.py
- [[Fetch the day's tradebook (execution fills) from Dhan.          Returns_1]] - rationale - scalpr/brokers/dhan/orders.py
- [[Modify an existing order's price, quantity, andor trigger price.          Args_1]] - rationale - scalpr/brokers/dhan/orders.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Dhan_Broker_Integration
SORT file.name ASC
```

## Connections to other communities
- 3 edges to [[_COMMUNITY_Tests UnitTesting]]
- 3 edges to [[_COMMUNITY_Tests UnitBrokers]]
- 2 edges to [[_COMMUNITY_Tests UnitBrokers_1]]

## Top bridge nodes
- [[.get_orderbook()]] - degree 5, connects to 2 communities
- [[.get_tradebook()_2]] - degree 5, connects to 2 communities
- [[.modify_order()_2]] - degree 4, connects to 2 communities
- [[Decimal_4]] - degree 5, connects to 1 community
---
type: community
cohesion: 0.40
members: 5
---

# Brokers - Broker

**Cohesion:** 0.40 - moderately connected
**Members:** 5 nodes

## Members
- [[.get_ltp()]] - code - scalpr/brokers/broker_port.py
- [[.modify_order()]] - code - scalpr/brokers/broker_port.py
- [[Decimal]] - code
- [[Get Last Traded Price for a symbol.]] - rationale - scalpr/brokers/broker_port.py
- [[Modify an existing order's price and quantity.]] - rationale - scalpr/brokers/broker_port.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Brokers_-_Broker
SORT file.name ASC
```

## Connections to other communities
- 2 edges to [[_COMMUNITY_Tests UnitBrokers]]
- 1 edge to [[_COMMUNITY_Oms - Order]]

## Top bridge nodes
- [[.get_ltp()]] - degree 3, connects to 1 community
- [[.modify_order()]] - degree 3, connects to 1 community
- [[Decimal]] - degree 3, connects to 1 community
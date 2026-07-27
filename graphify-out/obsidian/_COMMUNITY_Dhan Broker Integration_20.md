---
type: community
cohesion: 1.00
members: 2
---

# Dhan Broker Integration

**Cohesion:** 1.00 - tightly connected
**Members:** 2 nodes

## Members
- [[.cancel_order()_1]] - code - scalpr/brokers/dhan/gateway.py
- [[Cancel an active order.          Args             order_id Dhan order ID to ca]] - rationale - scalpr/brokers/dhan/gateway.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Dhan_Broker_Integration
SORT file.name ASC
```

## Connections to other communities
- 1 edge to [[_COMMUNITY_Tests UnitBrokers]]

## Top bridge nodes
- [[.cancel_order()_1]] - degree 2, connects to 1 community
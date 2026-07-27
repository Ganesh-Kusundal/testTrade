---
type: community
cohesion: 1.00
members: 2
---

# Dhan Broker Integration

**Cohesion:** 1.00 - tightly connected
**Members:** 2 nodes

## Members
- [[.orders()]] - code - scalpr/brokers/dhan/connection.py
- [[Access orders adapter.          Raises             BrokerError If not connecte]] - rationale - scalpr/brokers/dhan/connection.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Dhan_Broker_Integration
SORT file.name ASC
```

## Connections to other communities
- 1 edge to [[_COMMUNITY_Tests UnitBrokers_3]]
- 1 edge to [[_COMMUNITY_Tests UnitTesting]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers]]

## Top bridge nodes
- [[.orders()]] - degree 4, connects to 3 communities
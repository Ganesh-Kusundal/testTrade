---
type: community
cohesion: 1.00
members: 2
---

# Brokers - Broker

**Cohesion:** 1.00 - tightly connected
**Members:** 2 nodes

## Members
- [[.disconnect()_2]] - code - scalpr/brokers/broker_port.py
- [[Close connection and release resources.]] - rationale - scalpr/brokers/broker_port.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Brokers_-_Broker
SORT file.name ASC
```

## Connections to other communities
- 1 edge to [[_COMMUNITY_Tests UnitBrokers]]

## Top bridge nodes
- [[.disconnect()_2]] - degree 2, connects to 1 community
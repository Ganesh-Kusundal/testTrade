---
type: community
cohesion: 0.40
members: 5
---

# Dhan Broker Integration

**Cohesion:** 0.40 - moderately connected
**Members:** 5 nodes

## Members
- [[.__init__()_1]] - code - scalpr/brokers/dhan/connection.py
- [[._validate_config()]] - code - scalpr/brokers/dhan/connection.py
- [[Any_3]] - code
- [[Initialise DhanConnection with configuration.          Args             config]] - rationale - scalpr/brokers/dhan/connection.py
- [[Validate required configuration keys.]] - rationale - scalpr/brokers/dhan/connection.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Dhan_Broker_Integration
SORT file.name ASC
```

## Connections to other communities
- 2 edges to [[_COMMUNITY_Tests UnitBrokers_3]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers]]

## Top bridge nodes
- [[._validate_config()]] - degree 4, connects to 2 communities
- [[.__init__()_1]] - degree 4, connects to 1 community
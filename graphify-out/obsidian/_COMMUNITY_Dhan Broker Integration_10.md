---
type: community
cohesion: 0.17
members: 12
---

# Dhan Broker Integration

**Cohesion:** 0.17 - loosely connected
**Members:** 12 nodes

## Members
- [[._cleanup()]] - code - scalpr/brokers/dhan/connection.py
- [[._create_http_client()]] - code - scalpr/brokers/dhan/connection.py
- [[._create_resolver()]] - code - scalpr/brokers/dhan/connection.py
- [[._verify_connection()]] - code - scalpr/brokers/dhan/connection.py
- [[.connect()_3]] - code - scalpr/brokers/dhan/connection.py
- [[.disconnect()_3]] - code - scalpr/brokers/dhan/connection.py
- [[Close connection and release resources.          Safe to call multiple times. Cl]] - rationale - scalpr/brokers/dhan/connection.py
- [[Create and configure the shared HTTP client.]] - rationale - scalpr/brokers/dhan/connection.py
- [[Establish connection to Dhan API and initialise all adapters.          Steps]] - rationale - scalpr/brokers/dhan/connection.py
- [[Load instrument master and build the symbol resolver.]] - rationale - scalpr/brokers/dhan/connection.py
- [[Release all resources.]] - rationale - scalpr/brokers/dhan/connection.py
- [[Verify the connection and validate account setup.          Checks         - pr]] - rationale - scalpr/brokers/dhan/connection.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Dhan_Broker_Integration
SORT file.name ASC
```

## Connections to other communities
- 6 edges to [[_COMMUNITY_Tests UnitBrokers_3]]
- 3 edges to [[_COMMUNITY_Tests UnitTesting]]
- 1 edge to [[_COMMUNITY_Dhan Broker Integration_5]]
- 1 edge to [[_COMMUNITY_Dhan Broker Integration_9]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers]]
- 1 edge to [[_COMMUNITY_Dhan Broker Integration_2]]
- 1 edge to [[_COMMUNITY_Dhan Broker Integration_4]]
- 1 edge to [[_COMMUNITY_Dhan Broker Integration_7]]
- 1 edge to [[_COMMUNITY_Dhan Broker Integration_6]]

## Top bridge nodes
- [[.connect()_3]] - degree 11, connects to 6 communities
- [[._create_http_client()]] - degree 5, connects to 3 communities
- [[._create_resolver()]] - degree 5, connects to 3 communities
- [[._verify_connection()]] - degree 4, connects to 2 communities
- [[._cleanup()]] - degree 4, connects to 1 community
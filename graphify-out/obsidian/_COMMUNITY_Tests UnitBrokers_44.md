---
type: community
cohesion: 1.00
members: 2
---

# Tests: Unit/Brokers

**Cohesion:** 1.00 - tightly connected
**Members:** 2 nodes

## Members
- [[.test_should_raise_broker_error_when_market_data_accessed_before_connect()]] - code - tests/unit/brokers/dhan/test_gateway_connection.py
- [[Accessing .market_data before connect() must raise BrokerError.]] - rationale - tests/unit/brokers/dhan/test_gateway_connection.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Tests_Unit/Brokers
SORT file.name ASC
```

## Connections to other communities
- 1 edge to [[_COMMUNITY_Tests UnitBrokers_3]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers]]

## Top bridge nodes
- [[.test_should_raise_broker_error_when_market_data_accessed_before_connect()]] - degree 3, connects to 2 communities
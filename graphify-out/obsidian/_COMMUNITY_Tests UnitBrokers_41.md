---
type: community
cohesion: 1.00
members: 2
---

# Tests: Unit/Brokers

**Cohesion:** 1.00 - tightly connected
**Members:** 2 nodes

## Members
- [[.test_should_re_raise_authentication_error_without_wrapping()]] - code - tests/unit/brokers/dhan/test_gateway_connection.py
- [[AuthenticationError must propagate directly, not wrapped in BrokerError.]] - rationale - tests/unit/brokers/dhan/test_gateway_connection.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Tests_Unit/Brokers
SORT file.name ASC
```

## Connections to other communities
- 1 edge to [[_COMMUNITY_Tests UnitBrokers_3]]
- 1 edge to [[_COMMUNITY_Tests UnitTesting]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers]]

## Top bridge nodes
- [[.test_should_re_raise_authentication_error_without_wrapping()]] - degree 4, connects to 3 communities
---
type: community
cohesion: 1.00
members: 2
---

# Tests: Unit/Brokers

**Cohesion:** 1.00 - tightly connected
**Members:** 2 nodes

## Members
- [[.test_should_execute_full_get_positions_chain()]] - code - tests/unit/brokers/dhan/test_gateway_connection.py
- [[Verify gateway.get_positions → connection.portfolio.get_positions → returns lis]] - rationale - tests/unit/brokers/dhan/test_gateway_connection.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Tests_Unit/Brokers
SORT file.name ASC
```

## Connections to other communities
- 1 edge to [[_COMMUNITY_Tests UnitBrokers]]

## Top bridge nodes
- [[.test_should_execute_full_get_positions_chain()]] - degree 2, connects to 1 community
---
type: community
cohesion: 1.00
members: 2
---

# Tests: Unit/Brokers

**Cohesion:** 1.00 - tightly connected
**Members:** 2 nodes

## Members
- [[.test_should_be_safe_to_disconnect_when_already_disconnected()]] - code - tests/unit/brokers/dhan/test_gateway_connection.py
- [[Calling disconnect() on an already disconnected connection must not raise.]] - rationale - tests/unit/brokers/dhan/test_gateway_connection.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Tests_Unit/Brokers
SORT file.name ASC
```

## Connections to other communities
- 1 edge to [[_COMMUNITY_Tests UnitBrokers]]

## Top bridge nodes
- [[.test_should_be_safe_to_disconnect_when_already_disconnected()]] - degree 2, connects to 1 community
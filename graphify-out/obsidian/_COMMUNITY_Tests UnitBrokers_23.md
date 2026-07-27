---
type: community
cohesion: 1.00
members: 2
---

# Tests: Unit/Brokers

**Cohesion:** 1.00 - tightly connected
**Members:** 2 nodes

## Members
- [[.test_should_raise_broker_error_when_get_order_status_order_not_found()]] - code - tests/unit/brokers/dhan/test_gateway_connection.py
- [[get_order_status must raise BrokerError when order_id not found.]] - rationale - tests/unit/brokers/dhan/test_gateway_connection.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Tests_Unit/Brokers
SORT file.name ASC
```

## Connections to other communities
- 1 edge to [[_COMMUNITY_Tests UnitBrokers]]

## Top bridge nodes
- [[.test_should_raise_broker_error_when_get_order_status_order_not_found()]] - degree 2, connects to 1 community
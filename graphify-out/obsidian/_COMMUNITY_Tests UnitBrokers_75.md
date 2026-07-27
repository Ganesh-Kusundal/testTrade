---
type: community
cohesion: 1.00
members: 2
---

# Tests: Unit/Brokers

**Cohesion:** 1.00 - tightly connected
**Members:** 2 nodes

## Members
- [[.test_should_re_raise_broker_error_on_square_off_failure()]] - code - tests/unit/brokers/dhan/test_gateway_connection.py
- [[If place_order fails during square_off, BrokerError must be raised.]] - rationale - tests/unit/brokers/dhan/test_gateway_connection.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Tests_Unit/Brokers
SORT file.name ASC
```

## Connections to other communities
- 1 edge to [[_COMMUNITY_Tests UnitBrokers]]

## Top bridge nodes
- [[.test_should_re_raise_broker_error_on_square_off_failure()]] - degree 2, connects to 1 community
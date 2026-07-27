---
type: community
cohesion: 1.00
members: 2
---

# Tests: Unit/Brokers

**Cohesion:** 1.00 - tightly connected
**Members:** 2 nodes

## Members
- [[.test_should_delegate_modify_order_with_trigger_price()]] - code - tests/unit/brokers/dhan/test_gateway_connection.py
- [[gateway.modify_order() with trigger_price must pass it through.]] - rationale - tests/unit/brokers/dhan/test_gateway_connection.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Tests_Unit/Brokers
SORT file.name ASC
```

## Connections to other communities
- 1 edge to [[_COMMUNITY_Tests UnitBrokers]]

## Top bridge nodes
- [[.test_should_delegate_modify_order_with_trigger_price()]] - degree 2, connects to 1 community
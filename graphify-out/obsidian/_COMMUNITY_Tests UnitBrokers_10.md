---
type: community
cohesion: 0.25
members: 8
---

# Tests: Unit/Brokers

**Cohesion:** 0.25 - loosely connected
**Members:** 8 nodes

## Members
- [[.test_orders_code_uses_security_id_field()]] - code - tests/unit/brokers/dhan/test_security_id_consistency.py
- [[Create a mock SymbolResolver that returns real instruments.]] - rationale - tests/unit/brokers/dhan/test_security_id_consistency.py
- [[Orders adapter should reference inst.security_id in source code.]] - rationale - tests/unit/brokers/dhan/test_security_id_consistency.py
- [[Security ID consistency tests for Dhan broker integration.  These tests verify t]] - rationale - tests/unit/brokers/dhan/test_security_id_consistency.py
- [[TestOrdersSecurityIdUsage]] - code - tests/unit/brokers/dhan/test_security_id_consistency.py
- [[Verify orders code uses inst.security_id, not inst.symbol.]] - rationale - tests/unit/brokers/dhan/test_security_id_consistency.py
- [[mock_resolver()_1]] - code - tests/unit/brokers/dhan/test_security_id_consistency.py
- [[test_security_id_consistency.py]] - code - tests/unit/brokers/dhan/test_security_id_consistency.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Tests_Unit/Brokers
SORT file.name ASC
```

## Connections to other communities
- 7 edges to [[_COMMUNITY_Scanner - Options]]
- 4 edges to [[_COMMUNITY_Tests UnitBrokers]]
- 2 edges to [[_COMMUNITY_Dhan Broker Integration_5]]
- 2 edges to [[_COMMUNITY_Dhan Broker Integration_1]]
- 1 edge to [[_COMMUNITY_Dhan Broker Integration_3]]
- 1 edge to [[_COMMUNITY_Dhan Broker Integration_2]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers_12]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers_11]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers_9]]

## Top bridge nodes
- [[test_security_id_consistency.py]] - degree 16, connects to 9 communities
- [[TestOrdersSecurityIdUsage]] - degree 10, connects to 4 communities
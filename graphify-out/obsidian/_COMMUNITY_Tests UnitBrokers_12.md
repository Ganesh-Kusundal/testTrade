---
type: community
cohesion: 0.33
members: 6
---

# Tests: Unit/Brokers

**Cohesion:** 0.33 - loosely connected
**Members:** 6 nodes

## Members
- [[.test_full_subscription_flow_reliance()]] - code - tests/unit/brokers/dhan/test_security_id_consistency.py
- [[.test_full_subscription_flow_tcs()]] - code - tests/unit/brokers/dhan/test_security_id_consistency.py
- [[Complete flow for TCS symbol.]] - rationale - tests/unit/brokers/dhan/test_security_id_consistency.py
- [[Complete flow Symbol → Resolver → security_id int → SDK subscription.]] - rationale - tests/unit/brokers/dhan/test_security_id_consistency.py
- [[TestEndToEndSecurityIdFlow]] - code - tests/unit/brokers/dhan/test_security_id_consistency.py
- [[Verify security_id flows correctly through WebSocket subscription.]] - rationale - tests/unit/brokers/dhan/test_security_id_consistency.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Tests_Unit/Brokers
SORT file.name ASC
```

## Connections to other communities
- 3 edges to [[_COMMUNITY_Dhan Broker Integration_1]]
- 3 edges to [[_COMMUNITY_Scanner - Options]]
- 2 edges to [[_COMMUNITY_Tests UnitBrokers]]
- 1 edge to [[_COMMUNITY_Dhan Broker Integration_5]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers_10]]

## Top bridge nodes
- [[TestEndToEndSecurityIdFlow]] - degree 11, connects to 5 communities
- [[.test_full_subscription_flow_reliance()]] - degree 3, connects to 1 community
- [[.test_full_subscription_flow_tcs()]] - degree 3, connects to 1 community
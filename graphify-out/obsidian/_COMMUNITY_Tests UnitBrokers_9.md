---
type: community
cohesion: 0.20
members: 10
---

# Tests: Unit/Brokers

**Cohesion:** 0.20 - loosely connected
**Members:** 10 nodes

## Members
- [[.test_subscribe_fallback_without_resolver()]] - code - tests/unit/brokers/dhan/test_security_id_consistency.py
- [[.test_subscribe_handles_resolution_failure_gracefully()]] - code - tests/unit/brokers/dhan/test_security_id_consistency.py
- [[.test_subscribe_resolves_security_id_via_resolver()]] - code - tests/unit/brokers/dhan/test_security_id_consistency.py
- [[.test_subscribe_uses_integer_security_id()]] - code - tests/unit/brokers/dhan/test_security_id_consistency.py
- [[Security ID must be converted to integer for SDK.]] - rationale - tests/unit/brokers/dhan/test_security_id_consistency.py
- [[TestWebSocketSecurityIdResolution]] - code - tests/unit/brokers/dhan/test_security_id_consistency.py
- [[Verify WebSocket client resolves symbols to security_ids before subscribing.]] - rationale - tests/unit/brokers/dhan/test_security_id_consistency.py
- [[subscribe() should fallback to int(symbol) if no resolver available.]] - rationale - tests/unit/brokers/dhan/test_security_id_consistency.py
- [[subscribe() should handle resolution failures gracefully (log warning, skip).]] - rationale - tests/unit/brokers/dhan/test_security_id_consistency.py
- [[subscribe() should resolve symbol to security_id using resolver.]] - rationale - tests/unit/brokers/dhan/test_security_id_consistency.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Tests_Unit/Brokers
SORT file.name ASC
```

## Connections to other communities
- 5 edges to [[_COMMUNITY_Dhan Broker Integration_1]]
- 3 edges to [[_COMMUNITY_Scanner - Options]]
- 2 edges to [[_COMMUNITY_Tests UnitBrokers]]
- 1 edge to [[_COMMUNITY_Dhan Broker Integration_5]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers_10]]

## Top bridge nodes
- [[TestWebSocketSecurityIdResolution]] - degree 13, connects to 5 communities
- [[.test_subscribe_fallback_without_resolver()]] - degree 3, connects to 1 community
- [[.test_subscribe_handles_resolution_failure_gracefully()]] - degree 3, connects to 1 community
- [[.test_subscribe_resolves_security_id_via_resolver()]] - degree 3, connects to 1 community
- [[.test_subscribe_uses_integer_security_id()]] - degree 3, connects to 1 community
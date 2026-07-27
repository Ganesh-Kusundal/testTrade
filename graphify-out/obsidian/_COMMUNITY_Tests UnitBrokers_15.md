---
type: community
cohesion: 1.00
members: 2
---

# Tests: Unit/Brokers

**Cohesion:** 1.00 - tightly connected
**Members:** 2 nodes

## Members
- [[.test_connect_logs_active_segments()]] - code - tests/unit/brokers/dhan/test_critical_fixes.py
- [[Connection should log active segments from profile.]] - rationale - tests/unit/brokers/dhan/test_critical_fixes.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Tests_Unit/Brokers
SORT file.name ASC
```

## Connections to other communities
- 1 edge to [[_COMMUNITY_Tests UnitBrokers_3]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers]]

## Top bridge nodes
- [[.test_connect_logs_active_segments()]] - degree 3, connects to 2 communities
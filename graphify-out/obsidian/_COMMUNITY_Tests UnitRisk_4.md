---
type: community
cohesion: 0.33
members: 4
---

# Tests: Unit/Risk

**Cohesion:** 0.33 - loosely connected
**Members:** 4 nodes

## Members
- [[.test_warning_fires_at_15_00()]] - code - tests/unit/risk/test_session_guard.py
- [[.test_warning_fires_only_once()]] - code - tests/unit/risk/test_session_guard.py
- [[Verify warning does not fire again at 1505.]] - rationale - tests/unit/risk/test_session_guard.py
- [[Verify warning fires once at 1500 IST.]] - rationale - tests/unit/risk/test_session_guard.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Tests_Unit/Risk
SORT file.name ASC
```

## Connections to other communities
- 2 edges to [[_COMMUNITY_Risk - Session]]
- 2 edges to [[_COMMUNITY_Tests UnitRisk]]
- 2 edges to [[_COMMUNITY_Tests UnitRisk_1]]

## Top bridge nodes
- [[.test_warning_fires_at_15_00()]] - degree 4, connects to 3 communities
- [[.test_warning_fires_only_once()]] - degree 4, connects to 3 communities
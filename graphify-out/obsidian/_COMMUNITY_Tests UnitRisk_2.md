---
type: community
cohesion: 0.18
members: 13
---

# Tests: Unit/Risk

**Cohesion:** 0.18 - loosely connected
**Members:** 13 nodes

## Members
- [[._make_time()]] - code - tests/unit/risk/test_session_guard.py
- [[.test_reset_clears_consecutive_losses()]] - code - tests/unit/risk/test_session_guard.py
- [[.test_reset_clears_halt()]] - code - tests/unit/risk/test_session_guard.py
- [[.test_reset_clears_warnings()]] - code - tests/unit/risk/test_session_guard.py
- [[Comprehensive tests for SessionGuard timezone logic bug fix.]] - rationale - tests/unit/risk/test_session_guard.py
- [[Create a datetime in IST timezone.]] - rationale - tests/unit/risk/test_session_guard.py
- [[Test SessionGuard reset functionality.]] - rationale - tests/unit/risk/test_session_guard.py
- [[TestSessionGuardReset]] - code - tests/unit/risk/test_session_guard.py
- [[Verify reset clears halt state.]] - rationale - tests/unit/risk/test_session_guard.py
- [[Verify reset clears loss counter.]] - rationale - tests/unit/risk/test_session_guard.py
- [[Verify reset clears warning flags.]] - rationale - tests/unit/risk/test_session_guard.py
- [[datetime_7]] - code
- [[test_session_guard.py]] - code - tests/unit/risk/test_session_guard.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Tests_Unit/Risk
SORT file.name ASC
```

## Connections to other communities
- 6 edges to [[_COMMUNITY_Risk - Session]]
- 2 edges to [[_COMMUNITY_Tests UnitRisk_1]]
- 2 edges to [[_COMMUNITY_Tests UnitRisk]]
- 1 edge to [[_COMMUNITY_Tests UnitRisk_3]]

## Top bridge nodes
- [[test_session_guard.py]] - degree 8, connects to 4 communities
- [[TestSessionGuardReset]] - degree 6, connects to 1 community
- [[datetime_7]] - degree 5, connects to 1 community
- [[.test_reset_clears_halt()]] - degree 4, connects to 1 community
- [[.test_reset_clears_warnings()]] - degree 4, connects to 1 community
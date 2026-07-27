---
type: community
cohesion: 0.11
members: 18
---

# Tests: Unit/Risk

**Cohesion:** 0.11 - loosely connected
**Members:** 18 nodes

## Members
- [[.test_cutoff_window_minutes()]] - code - tests/unit/risk/test_session_guard.py
- [[.test_no_action_before_15_00()]] - code - tests/unit/risk/test_session_guard.py
- [[.test_square_off_fires_at_15_15()]] - code - tests/unit/risk/test_session_guard.py
- [[.test_square_off_fires_at_15_16()]] - code - tests/unit/risk/test_session_guard.py
- [[.test_square_off_fires_at_15_30()]] - code - tests/unit/risk/test_session_guard.py
- [[.test_warning_and_cutoff_sequence()]] - code - tests/unit/risk/test_session_guard.py
- [[.test_warning_fires_at_15_14()]] - code - tests/unit/risk/test_session_guard.py
- [[.test_warning_window_minutes()]] - code - tests/unit/risk/test_session_guard.py
- [[Test NSE market cutoff logic (1500-1530 IST window).]] - rationale - tests/unit/risk/test_session_guard.py
- [[Test all minutes in cutoff window (1515+).]] - rationale - tests/unit/risk/test_session_guard.py
- [[Test all minutes in warning window (1500-1514).]] - rationale - tests/unit/risk/test_session_guard.py
- [[Test full sequence warning at 1500, cutoff at 1515.]] - rationale - tests/unit/risk/test_session_guard.py
- [[TestSessionGuardNSE]] - code - tests/unit/risk/test_session_guard.py
- [[Verify no warning or square-off before 1500.]] - rationale - tests/unit/risk/test_session_guard.py
- [[Verify square-off fires at 1516 IST (after cutoff).]] - rationale - tests/unit/risk/test_session_guard.py
- [[Verify square-off fires at 1530 IST (well after cutoff).]] - rationale - tests/unit/risk/test_session_guard.py
- [[Verify square-off fires at exactly 1515 IST.]] - rationale - tests/unit/risk/test_session_guard.py
- [[Verify warning still fires at 1514 (last minute before cutoff).]] - rationale - tests/unit/risk/test_session_guard.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Tests_Unit/Risk
SORT file.name ASC
```

## Connections to other communities
- 9 edges to [[_COMMUNITY_Risk - Session]]
- 8 edges to [[_COMMUNITY_Tests UnitRisk_1]]
- 2 edges to [[_COMMUNITY_Tests UnitRisk_2]]
- 2 edges to [[_COMMUNITY_Tests UnitRisk_4]]

## Top bridge nodes
- [[TestSessionGuardNSE]] - degree 14, connects to 3 communities
- [[.test_cutoff_window_minutes()]] - degree 4, connects to 2 communities
- [[.test_no_action_before_15_00()]] - degree 4, connects to 2 communities
- [[.test_square_off_fires_at_15_15()]] - degree 4, connects to 2 communities
- [[.test_square_off_fires_at_15_16()]] - degree 4, connects to 2 communities
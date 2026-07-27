---
type: community
cohesion: 0.16
members: 18
---

# Tests: Unit/Risk

**Cohesion:** 0.16 - loosely connected
**Members:** 18 nodes

## Members
- [[._make_time()_1]] - code - tests/unit/risk/test_session_guard.py
- [[.test_cutoff_window_minutes()_1]] - code - tests/unit/risk/test_session_guard.py
- [[.test_no_action_before_23_00()]] - code - tests/unit/risk/test_session_guard.py
- [[.test_square_off_fires_at_23_15()]] - code - tests/unit/risk/test_session_guard.py
- [[.test_square_off_fires_at_23_16()]] - code - tests/unit/risk/test_session_guard.py
- [[.test_warning_fires_at_23_00()]] - code - tests/unit/risk/test_session_guard.py
- [[.test_warning_fires_only_once()_1]] - code - tests/unit/risk/test_session_guard.py
- [[.test_warning_window_minutes()_1]] - code - tests/unit/risk/test_session_guard.py
- [[Create a datetime in IST timezone._1]] - rationale - tests/unit/risk/test_session_guard.py
- [[Test MCX market cutoff logic (2300-2330 IST window).]] - rationale - tests/unit/risk/test_session_guard.py
- [[Test all minutes in MCX cutoff window (2315+).]] - rationale - tests/unit/risk/test_session_guard.py
- [[Test all minutes in MCX warning window (2300-2314).]] - rationale - tests/unit/risk/test_session_guard.py
- [[TestSessionGuardMCX]] - code - tests/unit/risk/test_session_guard.py
- [[Verify no action before 2300.]] - rationale - tests/unit/risk/test_session_guard.py
- [[Verify square-off fires at 2316 IST.]] - rationale - tests/unit/risk/test_session_guard.py
- [[Verify square-off fires at exactly 2315 IST.]] - rationale - tests/unit/risk/test_session_guard.py
- [[Verify warning does not fire again at 2305.]] - rationale - tests/unit/risk/test_session_guard.py
- [[Verify warning fires once at 2300 IST.]] - rationale - tests/unit/risk/test_session_guard.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Tests_Unit/Risk
SORT file.name ASC
```

## Connections to other communities
- 8 edges to [[_COMMUNITY_Risk - Session]]
- 8 edges to [[_COMMUNITY_Tests UnitRisk]]
- 2 edges to [[_COMMUNITY_Tests UnitRisk_2]]
- 2 edges to [[_COMMUNITY_Tests UnitRisk_4]]

## Top bridge nodes
- [[._make_time()_1]] - degree 20, connects to 3 communities
- [[TestSessionGuardMCX]] - degree 11, connects to 2 communities
- [[.test_cutoff_window_minutes()_1]] - degree 4, connects to 1 community
- [[.test_no_action_before_23_00()]] - degree 4, connects to 1 community
- [[.test_square_off_fires_at_23_15()]] - degree 4, connects to 1 community
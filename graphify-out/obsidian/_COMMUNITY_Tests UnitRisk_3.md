---
type: community
cohesion: 0.25
members: 8
---

# Tests: Unit/Risk

**Cohesion:** 0.25 - loosely connected
**Members:** 8 nodes

## Members
- [[.test_profit_resets_counter()]] - code - tests/unit/risk/test_session_guard.py
- [[.test_three_losses_trigger_halt()]] - code - tests/unit/risk/test_session_guard.py
- [[.test_zero_pnl_resets_counter()]] - code - tests/unit/risk/test_session_guard.py
- [[Test consecutive loss tracking.]] - rationale - tests/unit/risk/test_session_guard.py
- [[TestSessionGuardConsecutiveLosses]] - code - tests/unit/risk/test_session_guard.py
- [[Verify 3 consecutive losses trigger square-off.]] - rationale - tests/unit/risk/test_session_guard.py
- [[Verify profit resets consecutive loss counter.]] - rationale - tests/unit/risk/test_session_guard.py
- [[Verify zero PnL resets counter (not a loss).]] - rationale - tests/unit/risk/test_session_guard.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Tests_Unit/Risk
SORT file.name ASC
```

## Connections to other communities
- 4 edges to [[_COMMUNITY_Risk - Session]]
- 1 edge to [[_COMMUNITY_Tests UnitRisk_2]]

## Top bridge nodes
- [[TestSessionGuardConsecutiveLosses]] - degree 6, connects to 2 communities
- [[.test_profit_resets_counter()]] - degree 3, connects to 1 community
- [[.test_three_losses_trigger_halt()]] - degree 3, connects to 1 community
- [[.test_zero_pnl_resets_counter()]] - degree 3, connects to 1 community
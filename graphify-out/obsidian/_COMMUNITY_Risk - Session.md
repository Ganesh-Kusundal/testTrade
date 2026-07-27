---
type: community
cohesion: 0.16
members: 14
---

# Risk - Session

**Cohesion:** 0.16 - loosely connected
**Members:** 14 nodes

## Members
- [[.__init__()_32]] - code - scalpr/risk/session_guard.py
- [[.check_market_cutoff()]] - code - scalpr/risk/session_guard.py
- [[.record_pnl()]] - code - scalpr/risk/session_guard.py
- [[.reset_guard()]] - code - scalpr/risk/session_guard.py
- [[Check current time against IST market boundaries. Squares off intraday positions]] - rationale - scalpr/risk/session_guard.py
- [[Decimal_17]] - code
- [[Record trade PnL. Halts and squares off after 3 consecutive losses.]] - rationale - scalpr/risk/session_guard.py
- [[Reset the loss counters and halt state (requires manual operator action).]] - rationale - scalpr/risk/session_guard.py
- [[SessionGuard]] - code - scalpr/risk/session_guard.py
- [[SessionGuard registers consecutive losses and triggers square off when reaching]] - rationale - tests/unit/oms/test_oms_risk.py
- [[Tracks consecutive session losses and manages IST intraday square-off times.]] - rationale - scalpr/risk/session_guard.py
- [[datetime_4]] - code
- [[session_guard.py]] - code - scalpr/risk/session_guard.py
- [[test_session_guard_loss_tripping()]] - code - tests/unit/oms/test_oms_risk.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Risk_-_Session
SORT file.name ASC
```

## Connections to other communities
- 9 edges to [[_COMMUNITY_Tests UnitRisk]]
- 8 edges to [[_COMMUNITY_Tests UnitRisk_1]]
- 6 edges to [[_COMMUNITY_Tests UnitRisk_2]]
- 4 edges to [[_COMMUNITY_Oms - Order]]
- 4 edges to [[_COMMUNITY_Tests UnitRisk_3]]
- 3 edges to [[_COMMUNITY_Tests UnitBrokers]]
- 2 edges to [[_COMMUNITY_Tests UnitRisk_4]]
- 1 edge to [[_COMMUNITY_Logging System]]

## Top bridge nodes
- [[SessionGuard]] - degree 37, connects to 7 communities
- [[session_guard.py]] - degree 8, connects to 4 communities
- [[test_session_guard_loss_tripping()]] - degree 3, connects to 1 community
- [[.__init__()_32]] - degree 2, connects to 1 community
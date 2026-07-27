---
type: community
cohesion: 0.09
members: 25
---

# API Server

**Cohesion:** 0.09 - loosely connected
**Members:** 25 nodes

## Members
- [[Capture SessionHalted events.]] - rationale - scalpr/api/main.py
- [[Capture SignalGenerated events for the strategysignals endpoint.]] - rationale - scalpr/api/main.py
- [[Dhan connection health — actual connectivity check.]] - rationale - scalpr/api/main.py
- [[Generates synthetic ticks for development — bypasses the real feed.]] - rationale - scalpr/api/main.py
- [[Log fill execution for audit trail.]] - rationale - scalpr/api/main.py
- [[Log tick receipt for audit trail.]] - rationale - scalpr/api/main.py
- [[Prometheus-style metrics endpoint for production monitoring.]] - rationale - scalpr/api/main.py
- [[Return current Risk limit configuration.]] - rationale - scalpr/api/main.py
- [[Return last known Gate FSM evaluation per symbol.]] - rationale - scalpr/api/main.py
- [[Return recent trading signals, bounded to last N (default 50).]] - rationale - scalpr/api/main.py
- [[_capture_session_halted()]] - code - scalpr/api/main.py
- [[_capture_signal_generated()]] - code - scalpr/api/main.py
- [[_on_fill_received()]] - code - scalpr/api/main.py
- [[_on_tick_received()]] - code - scalpr/api/main.py
- [[feed_on_tick_callback()]] - code - scalpr/api/main.py
- [[get_health_dhan()]] - code - scalpr/api/main.py
- [[get_metrics()]] - code - scalpr/api/main.py
- [[get_portfolio()]] - code - scalpr/api/main.py
- [[get_positions()]] - code - scalpr/api/main.py
- [[get_risk_limits()]] - code - scalpr/api/main.py
- [[get_strategy_gates()]] - code - scalpr/api/main.py
- [[get_strategy_signals()]] - code - scalpr/api/main.py
- [[health_check()]] - code - scalpr/api/main.py
- [[main.py]] - code - scalpr/api/main.py
- [[tick_simulation_loop()]] - code - scalpr/api/main.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/API_Server
SORT file.name ASC
```

## Connections to other communities
- 23 edges to [[_COMMUNITY_Domain Events]]
- 12 edges to [[_COMMUNITY_API Server_1]]
- 10 edges to [[_COMMUNITY_Oms - Order]]
- 7 edges to [[_COMMUNITY_API Server_2]]
- 4 edges to [[_COMMUNITY_API Server_4]]
- 4 edges to [[_COMMUNITY_API Server_3]]
- 4 edges to [[_COMMUNITY_Market - Data]]
- 4 edges to [[_COMMUNITY_Simulation - Replay]]
- 2 edges to [[_COMMUNITY_Logging System]]
- 2 edges to [[_COMMUNITY_Tests UnitBrokers]]
- 2 edges to [[_COMMUNITY_Tests UnitTesting]]
- 2 edges to [[_COMMUNITY_Tracing]]
- 2 edges to [[_COMMUNITY_Signals - Gate]]
- 1 edge to [[_COMMUNITY_API Server_6]]
- 1 edge to [[_COMMUNITY_API Server_7]]
- 1 edge to [[_COMMUNITY_API Server_8]]
- 1 edge to [[_COMMUNITY_API Server_9]]
- 1 edge to [[_COMMUNITY_API Server_10]]
- 1 edge to [[_COMMUNITY_API Server_11]]
- 1 edge to [[_COMMUNITY_API Server_5]]
- 1 edge to [[_COMMUNITY_Dhan Broker Integration]]
- 1 edge to [[_COMMUNITY_Market - Data_1]]
- 1 edge to [[_COMMUNITY_Tests UnitObservability_1]]

## Top bridge nodes
- [[main.py]] - degree 91, connects to 22 communities
- [[feed_on_tick_callback()]] - degree 5, connects to 3 communities
- [[tick_simulation_loop()]] - degree 5, connects to 2 communities
- [[_capture_session_halted()]] - degree 3, connects to 1 community
- [[_capture_signal_generated()]] - degree 3, connects to 1 community
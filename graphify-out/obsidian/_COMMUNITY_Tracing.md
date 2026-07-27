---
type: community
cohesion: 0.25
members: 9
---

# Tracing

**Cohesion:** 0.25 - loosely connected
**Members:** 9 nodes

## Members
- [[.get_tick_id()]] - code - scalpr/observability/tracing.py
- [[Async-safe trace context for SCALPR trading platform.]] - rationale - scalpr/observability/tracing.py
- [[Get current tick ID from context.]] - rationale - scalpr/observability/tracing.py
- [[Thread-safe metrics registry for SCALPR trading platform.]] - rationale - scalpr/observability/metrics.py
- [[Trace context for correlating tick → signal → order → fill lifecycle.]] - rationale - scalpr/observability/tracing.py
- [[TraceContext]] - code - scalpr/observability/tracing.py
- [[__init__.py_6]] - code - scalpr/observability/__init__.py
- [[metrics.py]] - code - scalpr/observability/metrics.py
- [[tracing.py]] - code - scalpr/observability/tracing.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Tracing
SORT file.name ASC
```

## Connections to other communities
- 6 edges to [[_COMMUNITY_Logging System]]
- 3 edges to [[_COMMUNITY_Metrics]]
- 2 edges to [[_COMMUNITY_API Server]]
- 2 edges to [[_COMMUNITY_Tests UnitObservability_2]]
- 2 edges to [[_COMMUNITY_Metrics_2]]
- 2 edges to [[_COMMUNITY_Metrics_1]]
- 2 edges to [[_COMMUNITY_Tests UnitObservability_1]]
- 1 edge to [[_COMMUNITY_Simulation - Replay]]
- 1 edge to [[_COMMUNITY_API Server_5]]

## Top bridge nodes
- [[TraceContext]] - degree 14, connects to 8 communities
- [[metrics.py]] - degree 9, connects to 7 communities
- [[__init__.py_6]] - degree 6, connects to 2 communities
- [[tracing.py]] - degree 4, connects to 1 community
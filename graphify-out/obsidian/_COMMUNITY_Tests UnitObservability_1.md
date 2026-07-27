---
type: community
cohesion: 0.27
members: 10
---

# Tests: Unit/Observability

**Cohesion:** 0.27 - loosely connected
**Members:** 10 nodes

## Members
- [[.start()_1]] - code - scalpr/observability/tracing.py
- [[.test_context_var_propagation()]] - code - tests/unit/observability/test_metrics.py
- [[.test_different_symbols_different_contexts()]] - code - tests/unit/observability/test_metrics.py
- [[.test_start_creates_context()]] - code - tests/unit/observability/test_metrics.py
- [[.test_trace_id_is_short()]] - code - tests/unit/observability/test_metrics.py
- [[Start new trace context for a tick.                  Args             symbol T]] - rationale - scalpr/observability/tracing.py
- [[Test that context vars are set correctly.]] - rationale - tests/unit/observability/test_metrics.py
- [[Test trace context functionality.]] - rationale - tests/unit/observability/test_metrics.py
- [[TestTraceContext]] - code - tests/unit/observability/test_metrics.py
- [[Trace ID should be first 8 chars of UUID.]] - rationale - tests/unit/observability/test_metrics.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Tests_Unit/Observability
SORT file.name ASC
```

## Connections to other communities
- 2 edges to [[_COMMUNITY_Logging System]]
- 2 edges to [[_COMMUNITY_Tracing]]
- 1 edge to [[_COMMUNITY_API Server]]
- 1 edge to [[_COMMUNITY_Tests UnitObservability_2]]
- 1 edge to [[_COMMUNITY_Metrics_1]]
- 1 edge to [[_COMMUNITY_Metrics_2]]
- 1 edge to [[_COMMUNITY_Metrics]]

## Top bridge nodes
- [[TestTraceContext]] - degree 12, connects to 6 communities
- [[.start()_1]] - degree 7, connects to 2 communities
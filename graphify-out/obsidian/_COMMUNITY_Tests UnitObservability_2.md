---
type: community
cohesion: 0.31
members: 9
---

# Tests: Unit/Observability

**Cohesion:** 0.31 - loosely connected
**Members:** 9 nodes

## Members
- [[.get_counter()]] - code - scalpr/observability/metrics.py
- [[.increment()]] - code - scalpr/observability/metrics.py
- [[.test_increment()]] - code - tests/unit/observability/test_metrics.py
- [[.test_increment_by_amount()]] - code - tests/unit/observability/test_metrics.py
- [[.test_multiple_increments()]] - code - tests/unit/observability/test_metrics.py
- [[CounterMetric]] - code - scalpr/observability/metrics.py
- [[Monotonically increasing counter metric.]] - rationale - scalpr/observability/metrics.py
- [[Test counter metric functionality.]] - rationale - tests/unit/observability/test_metrics.py
- [[TestCounterMetric]] - code - tests/unit/observability/test_metrics.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Tests_Unit/Observability
SORT file.name ASC
```

## Connections to other communities
- 4 edges to [[_COMMUNITY_Logging System]]
- 4 edges to [[_COMMUNITY_Metrics]]
- 2 edges to [[_COMMUNITY_Tracing]]
- 2 edges to [[_COMMUNITY_Metrics_2]]
- 2 edges to [[_COMMUNITY_Metrics_1]]
- 1 edge to [[_COMMUNITY_Tests UnitObservability_1]]

## Top bridge nodes
- [[CounterMetric]] - degree 15, connects to 6 communities
- [[TestCounterMetric]] - degree 11, connects to 5 communities
- [[.get_counter()]] - degree 2, connects to 1 community
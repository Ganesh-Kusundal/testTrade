---
type: community
cohesion: 0.17
members: 18
---

# Metrics

**Cohesion:** 0.17 - loosely connected
**Members:** 18 nodes

## Members
- [[.__init__()_24]] - code - scalpr/observability/metrics.py
- [[._init_core_metrics()]] - code - scalpr/observability/metrics.py
- [[.get_histogram()]] - code - scalpr/observability/metrics.py
- [[.register_counter()]] - code - scalpr/observability/metrics.py
- [[.register_gauge()]] - code - scalpr/observability/metrics.py
- [[.register_histogram()]] - code - scalpr/observability/metrics.py
- [[.test_core_metrics_initialized()]] - code - tests/unit/observability/test_metrics.py
- [[.test_counter_persistence()]] - code - tests/unit/observability/test_metrics.py
- [[.test_get_counter()]] - code - tests/unit/observability/test_metrics.py
- [[.test_register_counter()]] - code - tests/unit/observability/test_metrics.py
- [[.test_snapshot()]] - code - tests/unit/observability/test_metrics.py
- [[Initialize standard trading platform metrics.]] - rationale - scalpr/observability/metrics.py
- [[MetricsRegistry]] - code - scalpr/observability/metrics.py
- [[Test metrics registry functionality.]] - rationale - tests/unit/observability/test_metrics.py
- [[Test that core trading metrics are initialized on startup.]] - rationale - tests/unit/observability/test_metrics.py
- [[Test that counter values persist across get calls.]] - rationale - tests/unit/observability/test_metrics.py
- [[TestMetricsRegistry]] - code - tests/unit/observability/test_metrics.py
- [[Thread-safe metrics registry for production monitoring.]] - rationale - scalpr/observability/metrics.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Metrics
SORT file.name ASC
```

## Connections to other communities
- 5 edges to [[_COMMUNITY_Metrics_1]]
- 4 edges to [[_COMMUNITY_Logging System]]
- 4 edges to [[_COMMUNITY_Tests UnitObservability_2]]
- 4 edges to [[_COMMUNITY_Metrics_2]]
- 3 edges to [[_COMMUNITY_Tracing]]
- 1 edge to [[_COMMUNITY_Tests UnitObservability_1]]

## Top bridge nodes
- [[MetricsRegistry]] - degree 24, connects to 6 communities
- [[TestMetricsRegistry]] - degree 13, connects to 5 communities
- [[.register_counter()]] - degree 3, connects to 1 community
- [[.register_gauge()]] - degree 3, connects to 1 community
- [[.register_histogram()]] - degree 3, connects to 1 community
---
type: community
cohesion: 0.19
members: 16
---

# Metrics

**Cohesion:** 0.19 - loosely connected
**Members:** 16 nodes

## Members
- [[.count()]] - code - scalpr/observability/metrics.py
- [[.observe()]] - code - scalpr/observability/metrics.py
- [[.p50()]] - code - scalpr/observability/metrics.py
- [[.p99()]] - code - scalpr/observability/metrics.py
- [[.snapshot()]] - code - scalpr/observability/metrics.py
- [[.test_count()]] - code - tests/unit/observability/test_metrics.py
- [[.test_empty_histogram()]] - code - tests/unit/observability/test_metrics.py
- [[.test_observe()]] - code - tests/unit/observability/test_metrics.py
- [[.test_p50_even_count()]] - code - tests/unit/observability/test_metrics.py
- [[.test_p50_odd_count()]] - code - tests/unit/observability/test_metrics.py
- [[.test_p99()]] - code - tests/unit/observability/test_metrics.py
- [[Histogram metric for tracking latency distributions.]] - rationale - scalpr/observability/metrics.py
- [[HistogramMetric]] - code - scalpr/observability/metrics.py
- [[Return current metrics snapshot for metrics endpoint.]] - rationale - scalpr/observability/metrics.py
- [[Test histogram metric functionality.]] - rationale - tests/unit/observability/test_metrics.py
- [[TestHistogramMetric]] - code - tests/unit/observability/test_metrics.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Metrics
SORT file.name ASC
```

## Connections to other communities
- 5 edges to [[_COMMUNITY_Metrics]]
- 4 edges to [[_COMMUNITY_Logging System]]
- 2 edges to [[_COMMUNITY_Tracing]]
- 2 edges to [[_COMMUNITY_Tests UnitObservability_2]]
- 2 edges to [[_COMMUNITY_Metrics_2]]
- 1 edge to [[_COMMUNITY_Tests UnitObservability_1]]

## Top bridge nodes
- [[HistogramMetric]] - degree 21, connects to 6 communities
- [[TestHistogramMetric]] - degree 14, connects to 5 communities
- [[.snapshot()]] - degree 5, connects to 1 community
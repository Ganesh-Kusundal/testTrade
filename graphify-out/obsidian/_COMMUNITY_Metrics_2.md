---
type: community
cohesion: 0.32
members: 8
---

# Metrics

**Cohesion:** 0.32 - loosely connected
**Members:** 8 nodes

## Members
- [[.get_gauge()]] - code - scalpr/observability/metrics.py
- [[.set()]] - code - scalpr/observability/metrics.py
- [[.test_override()]] - code - tests/unit/observability/test_metrics.py
- [[.test_set()]] - code - tests/unit/observability/test_metrics.py
- [[Gauge metric for point-in-time values.]] - rationale - scalpr/observability/metrics.py
- [[GaugeMetric]] - code - scalpr/observability/metrics.py
- [[Test gauge metric functionality.]] - rationale - tests/unit/observability/test_metrics.py
- [[TestGaugeMetric]] - code - tests/unit/observability/test_metrics.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Metrics
SORT file.name ASC
```

## Connections to other communities
- 4 edges to [[_COMMUNITY_Logging System]]
- 4 edges to [[_COMMUNITY_Metrics]]
- 2 edges to [[_COMMUNITY_Tracing]]
- 2 edges to [[_COMMUNITY_Tests UnitObservability_2]]
- 2 edges to [[_COMMUNITY_Metrics_1]]
- 1 edge to [[_COMMUNITY_Tests UnitObservability_1]]

## Top bridge nodes
- [[GaugeMetric]] - degree 14, connects to 6 communities
- [[TestGaugeMetric]] - degree 10, connects to 5 communities
- [[.get_gauge()]] - degree 2, connects to 1 community
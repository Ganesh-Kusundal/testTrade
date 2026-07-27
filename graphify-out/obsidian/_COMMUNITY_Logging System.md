---
type: community
cohesion: 0.24
members: 13
---

# Logging System

**Cohesion:** 0.24 - loosely connected
**Members:** 13 nodes

## Members
- [[.format()]] - code - scalpr/observability/logging.py
- [[.test_format_basic()]] - code - tests/unit/observability/test_metrics.py
- [[.test_format_with_trace_id()]] - code - tests/unit/observability/test_metrics.py
- [[Configure logging based on environment.          Args         environment dev]] - rationale - scalpr/observability/logging.py
- [[JSON log formatter for production observability.]] - rationale - scalpr/observability/logging.py
- [[JsonFormatter]] - code - scalpr/observability/logging.py
- [[Structured logging configuration for SCALPR trading platform.]] - rationale - scalpr/observability/logging.py
- [[Test JSON log formatter.]] - rationale - tests/unit/observability/test_metrics.py
- [[TestJsonFormatter]] - code - tests/unit/observability/test_metrics.py
- [[Tests for observability foundation (metrics, logging, tracing).]] - rationale - tests/unit/observability/test_metrics.py
- [[logging.py]] - code - scalpr/observability/logging.py
- [[setup_logging()]] - code - scalpr/observability/logging.py
- [[test_metrics.py]] - code - tests/unit/observability/test_metrics.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Logging_System
SORT file.name ASC
```

## Connections to other communities
- 6 edges to [[_COMMUNITY_Tracing]]
- 4 edges to [[_COMMUNITY_Tests UnitTesting]]
- 4 edges to [[_COMMUNITY_Oms - Order]]
- 4 edges to [[_COMMUNITY_Tests UnitObservability_2]]
- 4 edges to [[_COMMUNITY_Metrics_2]]
- 4 edges to [[_COMMUNITY_Metrics_1]]
- 4 edges to [[_COMMUNITY_Metrics]]
- 3 edges to [[_COMMUNITY_Dhan Broker Integration_2]]
- 3 edges to [[_COMMUNITY_Market - Data]]
- 2 edges to [[_COMMUNITY_API Server]]
- 2 edges to [[_COMMUNITY_Domain Events]]
- 2 edges to [[_COMMUNITY_Simulation - Replay]]
- 2 edges to [[_COMMUNITY_Tests UnitObservability_1]]
- 1 edge to [[_COMMUNITY_API Server_2]]
- 1 edge to [[_COMMUNITY_Dhan Broker Integration_7]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers_1]]
- 1 edge to [[_COMMUNITY_Dhan Broker Integration_3]]
- 1 edge to [[_COMMUNITY_Broker Contracts]]
- 1 edge to [[_COMMUNITY_Broker Registry]]
- 1 edge to [[_COMMUNITY_Market - Data_1]]
- 1 edge to [[_COMMUNITY_Risk - Session]]
- 1 edge to [[_COMMUNITY_Scanner - Options]]
- 1 edge to [[_COMMUNITY_Simulation - Walk]]
- 1 edge to [[_COMMUNITY_Signals - Gate]]
- 1 edge to [[_COMMUNITY_Scripts - Test - Dhan]]
- 1 edge to [[_COMMUNITY_Tests UnitConfig]]

## Top bridge nodes
- [[logging.py]] - degree 38, connects to 20 communities
- [[test_metrics.py]] - degree 17, connects to 6 communities
- [[JsonFormatter]] - degree 13, connects to 5 communities
- [[TestJsonFormatter]] - degree 10, connects to 5 communities
- [[setup_logging()]] - degree 7, connects to 3 communities
---
type: community
cohesion: 1.00
members: 2
---

# Tests: Unit/Brokers

**Cohesion:** 1.00 - tightly connected
**Members:** 2 nodes

## Members
- [[.test_charts_rate_limit_is_5_per_second()]] - code - tests/unit/brokers/dhan/test_critical_fixes.py
- [[Charts API rate limit should be 0.2s (5 reqsec).]] - rationale - tests/unit/brokers/dhan/test_critical_fixes.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Tests_Unit/Brokers
SORT file.name ASC
```

## Connections to other communities
- 1 edge to [[_COMMUNITY_Tests UnitBrokers]]

## Top bridge nodes
- [[.test_charts_rate_limit_is_5_per_second()]] - degree 2, connects to 1 community
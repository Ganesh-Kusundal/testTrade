---
type: community
cohesion: 0.67
members: 3
---

# API Server

**Cohesion:** 0.67 - moderately connected
**Members:** 3 nodes

## Members
- [[Capture RiskCheckFailed events.]] - rationale - scalpr/api/main.py
- [[RiskCheckFailed]] - code
- [[_capture_risk_check_failed()]] - code - scalpr/api/main.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/API_Server
SORT file.name ASC
```

## Connections to other communities
- 1 edge to [[_COMMUNITY_API Server]]

## Top bridge nodes
- [[_capture_risk_check_failed()]] - degree 3, connects to 1 community
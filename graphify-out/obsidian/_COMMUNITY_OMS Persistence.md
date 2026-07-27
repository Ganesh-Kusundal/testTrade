---
type: community
cohesion: 0.67
members: 3
---

# OMS Persistence

**Cohesion:** 0.67 - moderately connected
**Members:** 3 nodes

## Members
- [[.__init__()_27]] - code - scalpr/oms/persistence.py
- [[._init_db()_1]] - code - scalpr/oms/persistence.py
- [[Create tables and enable Write-Ahead Logging (WAL) mode.]] - rationale - scalpr/oms/persistence.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/OMS_Persistence
SORT file.name ASC
```

## Connections to other communities
- 2 edges to [[_COMMUNITY_Tests UnitBrokers]]

## Top bridge nodes
- [[._init_db()_1]] - degree 3, connects to 1 community
- [[.__init__()_27]] - degree 2, connects to 1 community
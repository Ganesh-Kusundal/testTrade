---
type: community
cohesion: 1.00
members: 2
---

# Chaos Testing

**Cohesion:** 1.00 - tightly connected
**Members:** 2 nodes

## Members
- [[.inject_timeout()]] - code - scalpr/testing/chaos.py
- [[Create mock that raises timeout after N successful calls.]] - rationale - scalpr/testing/chaos.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Chaos_Testing
SORT file.name ASC
```

## Connections to other communities
- 1 edge to [[_COMMUNITY_Tests UnitTesting]]

## Top bridge nodes
- [[.inject_timeout()]] - degree 2, connects to 1 community
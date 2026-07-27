---
type: community
cohesion: 1.00
members: 2
---

# Chaos Testing

**Cohesion:** 1.00 - tightly connected
**Members:** 2 nodes

## Members
- [[.inject_token_expiration()]] - code - scalpr/testing/chaos.py
- [[Create mock that simulates token expiration.]] - rationale - scalpr/testing/chaos.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Chaos_Testing
SORT file.name ASC
```

## Connections to other communities
- 1 edge to [[_COMMUNITY_Tests UnitTesting]]

## Top bridge nodes
- [[.inject_token_expiration()]] - degree 2, connects to 1 community
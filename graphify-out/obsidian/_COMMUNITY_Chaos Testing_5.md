---
type: community
cohesion: 1.00
members: 2
---

# Chaos Testing

**Cohesion:** 1.00 - tightly connected
**Members:** 2 nodes

## Members
- [[.disconnect_websocket()]] - code - scalpr/testing/chaos.py
- [[Simulate WebSocket disconnection.]] - rationale - scalpr/testing/chaos.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Chaos_Testing
SORT file.name ASC
```

## Connections to other communities
- 1 edge to [[_COMMUNITY_Tests UnitTesting]]

## Top bridge nodes
- [[.disconnect_websocket()]] - degree 2, connects to 1 community
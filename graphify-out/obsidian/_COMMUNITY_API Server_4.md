---
type: community
cohesion: 0.33
members: 6
---

# API Server

**Cohesion:** 0.33 - loosely connected
**Members:** 6 nodes

## Members
- [[Generate realistic mock candles based on a deterministic symbol seed.]] - rationale - scalpr/api/main.py
- [[WebSocket endpoint to drive progressive chart replay visualization.]] - rationale - scalpr/api/main.py
- [[datetime]] - code
- [[generate_mock_candles()]] - code - scalpr/api/main.py
- [[hash_string()]] - code - scalpr/api/main.py
- [[websocket_replay_endpoint()]] - code - scalpr/api/main.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/API_Server
SORT file.name ASC
```

## Connections to other communities
- 4 edges to [[_COMMUNITY_API Server]]
- 1 edge to [[_COMMUNITY_API Server_1]]
- 1 edge to [[_COMMUNITY_API Server_2]]

## Top bridge nodes
- [[generate_mock_candles()]] - degree 6, connects to 2 communities
- [[websocket_replay_endpoint()]] - degree 4, connects to 2 communities
- [[hash_string()]] - degree 2, connects to 1 community
- [[datetime]] - degree 2, connects to 1 community
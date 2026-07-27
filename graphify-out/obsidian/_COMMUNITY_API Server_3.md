---
type: community
cohesion: 0.20
members: 10
---

# API Server

**Cohesion:** 0.20 - loosely connected
**Members:** 10 nodes

## Members
- [[.broadcast_to_all()]] - code - scalpr/api/main.py
- [[Broadcast FillReceived event to all connected WebSocket clients.]] - rationale - scalpr/api/main.py
- [[Broadcast OrderPlaced event to all connected WebSocket clients.]] - rationale - scalpr/api/main.py
- [[Broadcast a message to ALL connected WebSocket clients.]] - rationale - scalpr/api/main.py
- [[Sync wrapper for async WebSocket broadcast of FillReceived events.]] - rationale - scalpr/api/main.py
- [[Sync wrapper for async WebSocket broadcast of OrderPlaced events.]] - rationale - scalpr/api/main.py
- [[_ws_broadcast_fill_received()]] - code - scalpr/api/main.py
- [[_ws_broadcast_order_placed()]] - code - scalpr/api/main.py
- [[_ws_on_fill_received_sync()]] - code - scalpr/api/main.py
- [[_ws_on_order_placed_sync()]] - code - scalpr/api/main.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/API_Server
SORT file.name ASC
```

## Connections to other communities
- 5 edges to [[_COMMUNITY_Domain Events]]
- 4 edges to [[_COMMUNITY_API Server]]
- 1 edge to [[_COMMUNITY_API Server_1]]

## Top bridge nodes
- [[.broadcast_to_all()]] - degree 5, connects to 2 communities
- [[_ws_broadcast_fill_received()]] - degree 5, connects to 2 communities
- [[_ws_broadcast_order_placed()]] - degree 5, connects to 2 communities
- [[_ws_on_fill_received_sync()]] - degree 4, connects to 2 communities
- [[_ws_on_order_placed_sync()]] - degree 4, connects to 2 communities
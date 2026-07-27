---
type: community
cohesion: 0.18
members: 15
---

# API Server

**Cohesion:** 0.18 - loosely connected
**Members:** 15 nodes

## Members
- [[.connect()_1]] - code - scalpr/api/main.py
- [[.disconnect()_1]] - code - scalpr/api/main.py
- [[.subscribe()_1]] - code - scalpr/api/main.py
- [[.unsubscribe()_1]] - code - scalpr/api/main.py
- [[Fetch historical OHLCV candles from Dhan (real data, no mocks).]] - rationale - scalpr/api/main.py
- [[Fetch historical OHLCV for a specific date range from Dhan.]] - rationale - scalpr/api/main.py
- [[Get Level 2 order book (top 5 bidask levels) from Dhan.]] - rationale - scalpr/api/main.py
- [[Gracefully disconnect market feed on application shutdown.]] - rationale - scalpr/api/main.py
- [[WebSocket]] - code
- [[get_candles()]] - code - scalpr/api/main.py
- [[get_historical()]] - code - scalpr/api/main.py
- [[get_market_depth()]] - code - scalpr/api/main.py
- [[shutdown_event()]] - code - scalpr/api/main.py
- [[startup_event()]] - code - scalpr/api/main.py
- [[websocket_endpoint()]] - code - scalpr/api/main.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/API_Server
SORT file.name ASC
```

## Connections to other communities
- 7 edges to [[_COMMUNITY_API Server]]
- 4 edges to [[_COMMUNITY_Domain Events]]
- 3 edges to [[_COMMUNITY_API Server_1]]
- 1 edge to [[_COMMUNITY_API Server_4]]
- 1 edge to [[_COMMUNITY_Logging System]]

## Top bridge nodes
- [[startup_event()]] - degree 5, connects to 2 communities
- [[get_candles()]] - degree 4, connects to 2 communities
- [[get_historical()]] - degree 4, connects to 2 communities
- [[get_market_depth()]] - degree 4, connects to 2 communities
- [[.connect()_1]] - degree 7, connects to 1 community
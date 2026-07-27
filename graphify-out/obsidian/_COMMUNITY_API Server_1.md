---
type: community
cohesion: 0.12
members: 17
---

# API Server

**Cohesion:** 0.12 - loosely connected
**Members:** 17 nodes

## Members
- [[.broadcast_to_subscribers()]] - code - scalpr/api/main.py
- [[Any_1]] - code
- [[Delete all events for a session.]] - rationale - scalpr/api/main.py
- [[Get event statistics for a session.]] - rationale - scalpr/api/main.py
- [[Retrieve quote structure for a given symbol.]] - rationale - scalpr/api/main.py
- [[Return all orders from Dhan broker, merged with local OMS state.]] - rationale - scalpr/api/main.py
- [[Return execution fillstrades from Dhan broker.]] - rationale - scalpr/api/main.py
- [[control_session()]] - code - scalpr/api/main.py
- [[create_session()]] - code - scalpr/api/main.py
- [[delete_session_events()]] - code - scalpr/api/main.py
- [[get_event_stats()]] - code - scalpr/api/main.py
- [[get_fills()]] - code - scalpr/api/main.py
- [[get_orders()]] - code - scalpr/api/main.py
- [[get_quote()]] - code - scalpr/api/main.py
- [[get_quote_data()]] - code - scalpr/api/main.py
- [[get_replay_sessions()]] - code - scalpr/api/main.py
- [[search_symbols()]] - code - scalpr/api/main.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/API_Server
SORT file.name ASC
```

## Connections to other communities
- 12 edges to [[_COMMUNITY_API Server]]
- 3 edges to [[_COMMUNITY_API Server_2]]
- 1 edge to [[_COMMUNITY_API Server_5]]
- 1 edge to [[_COMMUNITY_API Server_3]]
- 1 edge to [[_COMMUNITY_API Server_4]]
- 1 edge to [[_COMMUNITY_Domain Events]]

## Top bridge nodes
- [[Any_1]] - degree 19, connects to 5 communities
- [[get_quote_data()]] - degree 4, connects to 1 community
- [[delete_session_events()]] - degree 3, connects to 1 community
- [[get_event_stats()]] - degree 3, connects to 1 community
- [[get_fills()]] - degree 3, connects to 1 community
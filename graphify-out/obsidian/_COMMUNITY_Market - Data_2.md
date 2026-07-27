---
type: community
cohesion: 0.15
members: 16
---

# Market - Data

**Cohesion:** 0.15 - loosely connected
**Members:** 16 nodes

## Members
- [[.__init__()_19]] - code - scalpr/market_data/dhan_feed.py
- [[._process_queue_loop()]] - code - scalpr/market_data/dhan_feed.py
- [[.connect()_8]] - code - scalpr/market_data/dhan_feed.py
- [[.disconnect()_8]] - code - scalpr/market_data/dhan_feed.py
- [[.is_connected()_6]] - code - scalpr/market_data/dhan_feed.py
- [[.on_tick()_2]] - code - scalpr/market_data/dhan_feed.py
- [[.parse_raw_message()]] - code - scalpr/market_data/dhan_feed.py
- [[.put_tick()]] - code - scalpr/market_data/dhan_feed.py
- [[.subscribe()_6]] - code - scalpr/market_data/dhan_feed.py
- [[.unsubscribe()_6]] - code - scalpr/market_data/dhan_feed.py
- [[Any_14]] - code
- [[DhanMarketFeed]] - code - scalpr/market_data/dhan_feed.py
- [[Parse raw WS packet into domain Tick, calculating delta volume.]] - rationale - scalpr/market_data/dhan_feed.py
- [[Put raw message into the queue (with backpressure safety).]] - rationale - scalpr/market_data/dhan_feed.py
- [[Queue consumer loop that calls the tick callback.]] - rationale - scalpr/market_data/dhan_feed.py
- [[WebSocket feed client for streaming real-time ticks from DhanHQ.]] - rationale - scalpr/market_data/dhan_feed.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Market_-_Data
SORT file.name ASC
```

## Connections to other communities
- 18 edges to [[_COMMUNITY_Tests UnitTesting]]
- 5 edges to [[_COMMUNITY_Market - Data]]
- 2 edges to [[_COMMUNITY_Market - Data_1]]
- 1 edge to [[_COMMUNITY_Chaos Testing]]

## Top bridge nodes
- [[DhanMarketFeed]] - degree 35, connects to 4 communities
- [[.parse_raw_message()]] - degree 5, connects to 1 community
- [[.on_tick()_2]] - degree 2, connects to 1 community
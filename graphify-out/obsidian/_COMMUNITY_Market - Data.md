---
type: community
cohesion: 0.06
members: 48
---

# Market - Data

**Cohesion:** 0.06 - loosely connected
**Members:** 48 nodes

## Members
- [[.__post_init__()_7]] - code - scalpr/domain/tick.py
- [[.connect()_9]] - code - scalpr/market_data/feed_port.py
- [[.disconnect()_9]] - code - scalpr/market_data/feed_port.py
- [[.is_connected()_7]] - code - scalpr/market_data/feed_port.py
- [[.on_tick()_3]] - code - scalpr/market_data/feed_port.py
- [[.on_tick()_6]] - code - scalpr/strategy/strategy_port.py
- [[.process_tick()_1]] - code - scalpr/signals/cvd.py
- [[.should_process_tick()]] - code - scalpr/market_data/historical.py
- [[.subscribe()_7]] - code - scalpr/market_data/feed_port.py
- [[.test_event_immutability()]] - code - tests/unit/test_event_bus_wiring.py
- [[.test_load_from_events()]] - code - tests/unit/observability/test_event_store.py
- [[.test_replay_from_event_store()]] - code - tests/unit/observability/test_event_store.py
- [[.unsubscribe()_7]] - code - scalpr/market_data/feed_port.py
- [[.validate_tick()]] - code - scalpr/market_data/validators.py
- [[ABC]] - code
- [[Abstract interface defining the market data stream provider (WebSocket).]] - rationale - scalpr/market_data/feed_port.py
- [[Basic tests for SDK-based WebSocket client.]] - rationale - tests/unit/brokers/dhan/test_websocket.py
- [[Check if WebSocket connection is active._2]] - rationale - scalpr/market_data/feed_port.py
- [[ConnectionStatus]] - code - scalpr/brokers/dhan/ws_manager.py
- [[Drop any ticks older than or equal to the end of historical bars.]] - rationale - scalpr/market_data/historical.py
- [[Establish connection with the market data server.]] - rationale - scalpr/market_data/feed_port.py
- [[Explicit connection lifecycle states.]] - rationale - scalpr/brokers/dhan/ws_manager.py
- [[Handle incoming real-time market tick.]] - rationale - scalpr/strategy/strategy_port.py
- [[HealthMetrics]] - code - scalpr/brokers/dhan/ws_manager.py
- [[IMarketDataFeed]] - code - scalpr/market_data/feed_port.py
- [[Immutable snapshot of connection health.]] - rationale - scalpr/brokers/dhan/ws_manager.py
- [[Mutable internal metrics — never exposed directly.]] - rationale - scalpr/brokers/dhan/ws_manager.py
- [[Real-time market tick containing price and volume information.]] - rationale - scalpr/domain/tick.py
- [[Register callback for incoming tick packets._1]] - rationale - scalpr/market_data/feed_port.py
- [[Subscribe to real-time tick feeds for the specified symbols.]] - rationale - scalpr/market_data/feed_port.py
- [[Terminate connection with the market data server._1]] - rationale - scalpr/market_data/feed_port.py
- [[Test full replay from event store.]] - rationale - tests/unit/observability/test_event_store.py
- [[Test loading ticks from event store.]] - rationale - tests/unit/observability/test_event_store.py
- [[TestClientBasic]] - code - tests/unit/brokers/dhan/test_websocket.py
- [[Tick]] - code - scalpr/domain/tick.py
- [[Tick delta_volume is separate from cumulative_volume.]] - rationale - tests/unit/domain/test_domain.py
- [[Unit tests for Dhan WebSocket components (SDK-based).  Tests cover - DhanWebSoc]] - rationale - tests/unit/brokers/dhan/test_websocket.py
- [[Unsubscribe from tick feeds for the specified symbols._1]] - rationale - scalpr/market_data/feed_port.py
- [[Update CVD ask_qty - bid_qty delta addition.]] - rationale - scalpr/signals/cvd.py
- [[Validate tick. Returns True if valid, False if rejected.]] - rationale - scalpr/market_data/validators.py
- [[Verify events are immutable (frozen dataclasses).]] - rationale - tests/unit/test_event_bus_wiring.py
- [[WebSocket connection manager for Dhan market data.  High-level manager that coor]] - rationale - scalpr/brokers/dhan/ws_manager.py
- [[_MutableMetrics]] - code - scalpr/brokers/dhan/ws_manager.py
- [[dhan_feed.py]] - code - scalpr/market_data/dhan_feed.py
- [[feed_port.py]] - code - scalpr/market_data/feed_port.py
- [[test_tick_delta_volume_separate_from_cumulative()]] - code - tests/unit/domain/test_domain.py
- [[test_websocket.py]] - code - tests/unit/brokers/dhan/test_websocket.py
- [[ws_manager.py]] - code - scalpr/brokers/dhan/ws_manager.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Market_-_Data
SORT file.name ASC
```

## Connections to other communities
- 37 edges to [[_COMMUNITY_Domain Events]]
- 23 edges to [[_COMMUNITY_Tests UnitBrokers_5]]
- 21 edges to [[_COMMUNITY_Market - Data_1]]
- 19 edges to [[_COMMUNITY_Tests UnitTesting]]
- 16 edges to [[_COMMUNITY_Dhan Broker Integration_1]]
- 16 edges to [[_COMMUNITY_Dhan Broker Integration]]
- 10 edges to [[_COMMUNITY_Simulation - Replay]]
- 9 edges to [[_COMMUNITY_Oms - Order]]
- 8 edges to [[_COMMUNITY_Signals - Gate]]
- 5 edges to [[_COMMUNITY_Backtester]]
- 5 edges to [[_COMMUNITY_Market - Data_2]]
- 4 edges to [[_COMMUNITY_API Server]]
- 4 edges to [[_COMMUNITY_Dhan Broker Integration_3]]
- 4 edges to [[_COMMUNITY_Portfolio Management]]
- 4 edges to [[_COMMUNITY_Chaos Testing]]
- 4 edges to [[_COMMUNITY_Tests UnitStrategy]]
- 3 edges to [[_COMMUNITY_Logging System]]
- 3 edges to [[_COMMUNITY_Tests UnitObservability]]
- 2 edges to [[_COMMUNITY_Broker Gateway]]
- 2 edges to [[_COMMUNITY_Broker Registry]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers]]
- 1 edge to [[_COMMUNITY_Dhan Broker Integration_2]]
- 1 edge to [[_COMMUNITY_Broker Contracts]]
- 1 edge to [[_COMMUNITY_CLI Commands_1]]
- 1 edge to [[_COMMUNITY_Market - Data_3]]
- 1 edge to [[_COMMUNITY_Observability - Event]]
- 1 edge to [[_COMMUNITY_Scripts - Validate - Streaming]]

## Top bridge nodes
- [[Tick]] - degree 163, connects to 24 communities
- [[test_websocket.py]] - degree 18, connects to 6 communities
- [[ws_manager.py]] - degree 14, connects to 6 communities
- [[ABC]] - degree 8, connects to 4 communities
- [[ConnectionStatus]] - degree 13, connects to 3 communities
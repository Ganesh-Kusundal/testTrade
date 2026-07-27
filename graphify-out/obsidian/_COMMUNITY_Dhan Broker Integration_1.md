---
type: community
cohesion: 0.05
members: 48
---

# Dhan Broker Integration

**Cohesion:** 0.05 - loosely connected
**Members:** 48 nodes

## Members
- [[.__aexit__()]] - code - scalpr/brokers/dhan/ws_client.py
- [[.__init__()_13]] - code - scalpr/brokers/dhan/ws_client.py
- [[.__repr__()_1]] - code - scalpr/brokers/dhan/ws_client.py
- [[._on_close()]] - code - scalpr/brokers/dhan/ws_client.py
- [[._on_connect()]] - code - scalpr/brokers/dhan/ws_client.py
- [[._on_error()]] - code - scalpr/brokers/dhan/ws_client.py
- [[._on_message()]] - code - scalpr/brokers/dhan/ws_client.py
- [[._parse_sdk_data()]] - code - scalpr/brokers/dhan/ws_client.py
- [[._run_sdk()]] - code - scalpr/brokers/dhan/ws_client.py
- [[.close()_2]] - code - scalpr/brokers/dhan/ws_client.py
- [[.disconnect()_5]] - code - scalpr/brokers/dhan/ws_client.py
- [[.is_connected()_3]] - code - scalpr/brokers/dhan/ws_client.py
- [[.on_tick()]] - code - scalpr/brokers/dhan/ws_client.py
- [[.subscriptions()]] - code - scalpr/brokers/dhan/ws_client.py
- [[.test_is_connected_false_initially()]] - code - tests/unit/brokers/dhan/test_websocket.py
- [[.test_on_tick_registers_callback()]] - code - tests/unit/brokers/dhan/test_websocket.py
- [[.test_repr_disconnected()]] - code - tests/unit/brokers/dhan/test_websocket.py
- [[Alias for disconnect for resource cleanup contexts.]] - rationale - scalpr/brokers/dhan/ws_client.py
- [[Any_10]] - code
- [[Async WebSocket client for Dhan live market data streaming.          Uses the of]] - rationale - scalpr/brokers/dhan/ws_client.py
- [[Async context manager exit.]] - rationale - scalpr/brokers/dhan/ws_client.py
- [[Callback for received ticks.]] - rationale - test_live_crude_oil.py
- [[Callback for received ticks._1]] - rationale - test_live_nifty.py
- [[Check if WebSocket connection is active.]] - rationale - scalpr/brokers/dhan/ws_client.py
- [[Client should report disconnected before connect() is called.]] - rationale - tests/unit/brokers/dhan/test_websocket.py
- [[DhanWebSocketClient]] - code - scalpr/brokers/dhan/ws_client.py
- [[Gracefully close the WebSocket connection.                  Returns]] - rationale - scalpr/brokers/dhan/ws_client.py
- [[Initialise the WebSocket client.                  Args             access_token]] - rationale - scalpr/brokers/dhan/ws_client.py
- [[Parse SDK market data dict into Tick domain object.                  Args]] - rationale - scalpr/brokers/dhan/ws_client.py
- [[Register callback for incoming tick packets.                  Args]] - rationale - scalpr/brokers/dhan/ws_client.py
- [[Return current subscriptions as (symbol, exchange) tuples.]] - rationale - scalpr/brokers/dhan/ws_client.py
- [[Run SDK event loop in background thread.]] - rationale - scalpr/brokers/dhan/ws_client.py
- [[SDK callback connection closed.]] - rationale - scalpr/brokers/dhan/ws_client.py
- [[SDK callback connection established.]] - rationale - scalpr/brokers/dhan/ws_client.py
- [[SDK callback error occurred.]] - rationale - scalpr/brokers/dhan/ws_client.py
- [[SDK callback market data received.                  The SDK already parsed the]] - rationale - scalpr/brokers/dhan/ws_client.py
- [[Test live WebSocket subscription for Crude Oil spot price.]] - rationale - test_live_crude_oil.py
- [[Test live WebSocket subscription for Crude Oil.]] - rationale - test_live_crude_oil.py
- [[Test live WebSocket subscription for NIFTY 50.]] - rationale - test_live_nifty.py
- [[Test live WebSocket with NIFTY 50 (should be very liquid).]] - rationale - test_live_nifty.py
- [[main()_6]] - code - test_live_crude_oil.py
- [[main()_7]] - code - test_live_nifty.py
- [[on_tick() should store the callback.]] - rationale - tests/unit/brokers/dhan/test_websocket.py
- [[on_tick_received()]] - code - test_live_crude_oil.py
- [[on_tick_received()_1]] - code - test_live_nifty.py
- [[repr() should show disconnected state.]] - rationale - tests/unit/brokers/dhan/test_websocket.py
- [[test_live_crude_oil.py]] - code - test_live_crude_oil.py
- [[test_live_nifty.py]] - code - test_live_nifty.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Dhan_Broker_Integration
SORT file.name ASC
```

## Connections to other communities
- 16 edges to [[_COMMUNITY_Market - Data]]
- 8 edges to [[_COMMUNITY_Dhan Broker Integration_3]]
- 5 edges to [[_COMMUNITY_Tests UnitBrokers_9]]
- 5 edges to [[_COMMUNITY_Tests UnitBrokers_5]]
- 3 edges to [[_COMMUNITY_Tests UnitBrokers_12]]
- 2 edges to [[_COMMUNITY_Dhan Broker Integration]]
- 2 edges to [[_COMMUNITY_Tests UnitBrokers_10]]
- 2 edges to [[_COMMUNITY_Market - Data_1]]
- 1 edge to [[_COMMUNITY_Tests UnitTesting]]
- 1 edge to [[_COMMUNITY_Scanner - Options]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers_11]]

## Top bridge nodes
- [[DhanWebSocketClient]] - degree 55, connects to 10 communities
- [[test_live_crude_oil.py]] - degree 7, connects to 3 communities
- [[test_live_nifty.py]] - degree 7, connects to 3 communities
- [[._parse_sdk_data()]] - degree 5, connects to 1 community
- [[on_tick_received()]] - degree 4, connects to 1 community
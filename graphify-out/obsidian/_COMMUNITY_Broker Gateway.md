---
type: community
cohesion: 0.06
members: 38
---

# Broker Gateway

**Cohesion:** 0.06 - loosely connected
**Members:** 38 nodes

## Members
- [[.__init__()_15]] - code - scalpr/brokers/gateway.py
- [[._init_websocket_manager()]] - code - scalpr/brokers/gateway.py
- [[._load_config_from_env()]] - code - scalpr/brokers/gateway.py
- [[.broker_name()]] - code - scalpr/brokers/gateway.py
- [[.connect()_7]] - code - scalpr/brokers/gateway.py
- [[.depth()]] - code - scalpr/brokers/gateway.py
- [[.disconnect()_7]] - code - scalpr/brokers/gateway.py
- [[.gateway()]] - code - scalpr/brokers/gateway.py
- [[.history()]] - code - scalpr/brokers/gateway.py
- [[.holdings()]] - code - scalpr/brokers/gateway.py
- [[.is_connected()_5]] - code - scalpr/brokers/gateway.py
- [[.is_streaming()]] - code - scalpr/brokers/gateway.py
- [[.orders()_1]] - code - scalpr/brokers/gateway.py
- [[.positions()]] - code - scalpr/brokers/gateway.py
- [[.stop_stream()]] - code - scalpr/brokers/gateway.py
- [[.stream()]] - code - scalpr/brokers/gateway.py
- [[.trades()]] - code - scalpr/brokers/gateway.py
- [[Access the underlying IBrokerGateway implementation.          Use this for advan]] - rationale - scalpr/brokers/gateway.py
- [[Any_12]] - code
- [[Check if gateway is connected.          Returns             True if connected]] - rationale - scalpr/brokers/gateway.py
- [[Check if streaming is active.          Returns             True if streaming is]] - rationale - scalpr/brokers/gateway.py
- [[Close connection and release resources._1]] - rationale - scalpr/brokers/gateway.py
- [[DataFrame_4]] - code
- [[Establish connection to broker API._1]] - rationale - scalpr/brokers/gateway.py
- [[Fetch current open positions.          Returns             List of Position dom]] - rationale - scalpr/brokers/gateway.py
- [[Fetch historical OHLCV candlestick data.          Args             symbol Sing]] - rationale - scalpr/brokers/gateway.py
- [[Fetch long-term delivery holdings.          Returns             List of Holding]] - rationale - scalpr/brokers/gateway.py
- [[Fetch the day's tradebook (execution fills).          Returns             List]] - rationale - scalpr/brokers/gateway.py
- [[Fetch the full orderbook.          Returns             List of Order domain obj]] - rationale - scalpr/brokers/gateway.py
- [[Gateway]] - code - scalpr/brokers/gateway.py
- [[Get market depth (order book) for a symbol.          Args             symbol T]] - rationale - scalpr/brokers/gateway.py
- [[High-level broker-agnostic gateway with intelligent defaults.      Provides a si]] - rationale - scalpr/brokers/gateway.py
- [[Initialize Gateway with broker and configuration.          Args             bro]] - rationale - scalpr/brokers/gateway.py
- [[Initialize WebSocket manager for streaming.]] - rationale - scalpr/brokers/gateway.py
- [[Load broker configuration from environment variables.          Returns]] - rationale - scalpr/brokers/gateway.py
- [[Stop all streaming subscriptions.]] - rationale - scalpr/brokers/gateway.py
- [[Subscribe to live market data stream for symbols.          Args             sym]] - rationale - scalpr/brokers/gateway.py
- [[Trade_2]] - code

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Broker_Gateway
SORT file.name ASC
```

## Connections to other communities
- 10 edges to [[_COMMUNITY_Scripts - Validate - Gateway]]
- 9 edges to [[_COMMUNITY_Broker Contracts]]
- 3 edges to [[_COMMUNITY_Broker Gateway_1]]
- 2 edges to [[_COMMUNITY_Tests UnitBrokers]]
- 2 edges to [[_COMMUNITY_Dhan Broker Integration]]
- 2 edges to [[_COMMUNITY_Broker Registry]]
- 2 edges to [[_COMMUNITY_Market - Data]]
- 1 edge to [[_COMMUNITY_CLI Commands]]

## Top bridge nodes
- [[Gateway]] - degree 43, connects to 8 communities
- [[.__init__()_15]] - degree 6, connects to 1 community
- [[._init_websocket_manager()]] - degree 5, connects to 1 community
- [[.stream()]] - degree 4, connects to 1 community
- [[.depth()]] - degree 3, connects to 1 community
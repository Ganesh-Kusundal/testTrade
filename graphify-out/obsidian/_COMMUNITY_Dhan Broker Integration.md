---
type: community
cohesion: 0.05
members: 56
---

# Dhan Broker Integration

**Cohesion:** 0.05 - loosely connected
**Members:** 56 nodes

## Members
- [[.__aenter__()_1]] - code - scalpr/brokers/dhan/ws_manager.py
- [[.__aexit__()_1]] - code - scalpr/brokers/dhan/ws_manager.py
- [[.__init__()_14]] - code - scalpr/brokers/dhan/ws_manager.py
- [[._add_subscriber_async()]] - code - scalpr/brokers/dhan/ws_manager.py
- [[._distribute_tick()]] - code - scalpr/brokers/dhan/ws_manager.py
- [[._distribute_tick_sync()]] - code - scalpr/brokers/dhan/ws_manager.py
- [[._ensure_components()]] - code - scalpr/brokers/dhan/ws_manager.py
- [[._health_check_loop()]] - code - scalpr/brokers/dhan/ws_manager.py
- [[._log_task_exception()]] - code - scalpr/brokers/dhan/ws_manager.py
- [[._message_loop()]] - code - scalpr/brokers/dhan/ws_manager.py
- [[._on_tick_received()]] - code - scalpr/brokers/dhan/ws_manager.py
- [[._reconnect()]] - code - scalpr/brokers/dhan/ws_manager.py
- [[._remove_subscriber_async()]] - code - scalpr/brokers/dhan/ws_manager.py
- [[._set_status()]] - code - scalpr/brokers/dhan/ws_manager.py
- [[._subscribe_async()]] - code - scalpr/brokers/dhan/ws_manager.py
- [[._unsubscribe_async()]] - code - scalpr/brokers/dhan/ws_manager.py
- [[.add_subscriber()]] - code - scalpr/brokers/dhan/ws_manager.py
- [[.connect()_6]] - code - scalpr/brokers/dhan/ws_manager.py
- [[.disconnect()_6]] - code - scalpr/brokers/dhan/ws_manager.py
- [[.get_active_subscriptions()]] - code - scalpr/brokers/dhan/ws_manager.py
- [[.get_health_status()]] - code - scalpr/brokers/dhan/ws_manager.py
- [[.is_connected()_4]] - code - scalpr/brokers/dhan/ws_manager.py
- [[.on_tick()_1]] - code - scalpr/brokers/dhan/ws_manager.py
- [[.remove_subscriber()]] - code - scalpr/brokers/dhan/ws_manager.py
- [[.restore_subscriptions()]] - code - scalpr/brokers/dhan/ws_manager.py
- [[.start()]] - code - scalpr/brokers/dhan/ws_manager.py
- [[.stop()]] - code - scalpr/brokers/dhan/ws_manager.py
- [[.subscribe()_3]] - code - scalpr/brokers/dhan/ws_manager.py
- [[.unsubscribe()_3]] - code - scalpr/brokers/dhan/ws_manager.py
- [[Add to subscription list and send subscribe to client if running.]] - rationale - scalpr/brokers/dhan/ws_manager.py
- [[Any_11]] - code
- [[Callback invoked by ws_client when a tick arrives.          Records metrics and]] - rationale - scalpr/brokers/dhan/ws_manager.py
- [[Check if WebSocket connection is active._1]] - rationale - scalpr/brokers/dhan/ws_manager.py
- [[Connect WebSocket client and start message processing loop.          This is the]] - rationale - scalpr/brokers/dhan/ws_manager.py
- [[Core message processing loop.          Registers a tick callback on the ws_clien]] - rationale - scalpr/brokers/dhan/ws_manager.py
- [[DhanWebSocketManager]] - code - scalpr/brokers/dhan/ws_manager.py
- [[Disconnect gracefully — drain messages, persist subscriptions.          Order ma]] - rationale - scalpr/brokers/dhan/ws_manager.py
- [[Distribute tick to all registered subscribers (async version).]] - rationale - scalpr/brokers/dhan/ws_manager.py
- [[Distribute tick to all registered subscribers (sync version).          Critical]] - rationale - scalpr/brokers/dhan/ws_manager.py
- [[Establish connection with the market data server.          Synchronous wrapper —]] - rationale - scalpr/brokers/dhan/ws_manager.py
- [[Lazy import and create ws_client instance.          This allows ws_manager to be]] - rationale - scalpr/brokers/dhan/ws_manager.py
- [[Log exceptions from fire-and-forget tasks.]] - rationale - scalpr/brokers/dhan/ws_manager.py
- [[Periodic health check — runs every _health_check_interval seconds.          Resp]] - rationale - scalpr/brokers/dhan/ws_manager.py
- [[Production-ready WebSocket manager for Dhan market data.      Responsibilities]] - rationale - scalpr/brokers/dhan/ws_manager.py
- [[Reconnection strategy — delegate to ws_client with backoff.]] - rationale - scalpr/brokers/dhan/ws_manager.py
- [[Register callback for incoming tick packets.]] - rationale - scalpr/brokers/dhan/ws_manager.py
- [[Register callback for tick delivery.          Thread-safe uses asyncio.Lock for]] - rationale - scalpr/brokers/dhan/ws_manager.py
- [[Remove from subscription list and send unsubscribe to client.]] - rationale - scalpr/brokers/dhan/ws_manager.py
- [[Restore subscriptions from persisted state.          Call this before start() to]] - rationale - scalpr/brokers/dhan/ws_manager.py
- [[Return current subscriptions as a list of (symbol, exchange) tuples.          Us]] - rationale - scalpr/brokers/dhan/ws_manager.py
- [[Return immutable snapshot of connection health.          Safe to call from any t]] - rationale - scalpr/brokers/dhan/ws_manager.py
- [[Subscribe to real-time tick feeds for the specified symbols.          For IMarke]] - rationale - scalpr/brokers/dhan/ws_manager.py
- [[Task]] - code
- [[Terminate connection with the market data server.]] - rationale - scalpr/brokers/dhan/ws_manager.py
- [[Transition connection status with logging.]] - rationale - scalpr/brokers/dhan/ws_manager.py
- [[Unsubscribe from tick feeds for the specified symbols.]] - rationale - scalpr/brokers/dhan/ws_manager.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Dhan_Broker_Integration
SORT file.name ASC
```

## Connections to other communities
- 16 edges to [[_COMMUNITY_Market - Data]]
- 6 edges to [[_COMMUNITY_Tests UnitBrokers_5]]
- 2 edges to [[_COMMUNITY_Dhan Broker Integration_1]]
- 2 edges to [[_COMMUNITY_Broker Gateway]]
- 1 edge to [[_COMMUNITY_API Server]]
- 1 edge to [[_COMMUNITY_Domain Events]]
- 1 edge to [[_COMMUNITY_Broker Contracts]]

## Top bridge nodes
- [[DhanWebSocketManager]] - degree 47, connects to 7 communities
- [[._set_status()]] - degree 6, connects to 1 community
- [[.add_subscriber()]] - degree 5, connects to 1 community
- [[._distribute_tick()]] - degree 5, connects to 1 community
- [[._distribute_tick_sync()]] - degree 5, connects to 1 community
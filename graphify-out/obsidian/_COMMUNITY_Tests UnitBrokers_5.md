---
type: community
cohesion: 0.09
members: 38
---

# Tests: Unit/Brokers

**Cohesion:** 0.09 - loosely connected
**Members:** 38 nodes

## Members
- [[.test_add_subscriber_sync()]] - code - tests/unit/brokers/dhan/test_websocket.py
- [[.test_context_manager()]] - code - tests/unit/brokers/dhan/test_websocket.py
- [[.test_distribute_no_subscribers()]] - code - tests/unit/brokers/dhan/test_websocket.py
- [[.test_distribute_to_multiple()]] - code - tests/unit/brokers/dhan/test_websocket.py
- [[.test_get_active_subscriptions()]] - code - tests/unit/brokers/dhan/test_websocket.py
- [[.test_initial_state()]] - code - tests/unit/brokers/dhan/test_websocket.py
- [[.test_last_error()]] - code - tests/unit/brokers/dhan/test_websocket.py
- [[.test_messages_per_second()]] - code - tests/unit/brokers/dhan/test_websocket.py
- [[.test_on_tick_is_alias()]] - code - tests/unit/brokers/dhan/test_websocket.py
- [[.test_reconnect_skips_when_disconnecting()]] - code - tests/unit/brokers/dhan/test_websocket.py
- [[.test_reconnect_skips_when_reconnecting()]] - code - tests/unit/brokers/dhan/test_websocket.py
- [[.test_reconnect_succeeds()]] - code - tests/unit/brokers/dhan/test_websocket.py
- [[.test_records_messages()]] - code - tests/unit/brokers/dhan/test_websocket.py
- [[.test_remove_subscriber_sync()]] - code - tests/unit/brokers/dhan/test_websocket.py
- [[.test_restore_subscriptions()]] - code - tests/unit/brokers/dhan/test_websocket.py
- [[.test_start_connects_and_creates_tasks()]] - code - tests/unit/brokers/dhan/test_websocket.py
- [[.test_start_ignores_duplicate()]] - code - tests/unit/brokers/dhan/test_websocket.py
- [[.test_start_reraises_on_failure()]] - code - tests/unit/brokers/dhan/test_websocket.py
- [[.test_start_restores_subscriptions()]] - code - tests/unit/brokers/dhan/test_websocket.py
- [[.test_start_stop_idempotent()]] - code - tests/unit/brokers/dhan/test_websocket.py
- [[.test_stop_drains_queue()]] - code - tests/unit/brokers/dhan/test_websocket.py
- [[.test_stop_ignores_when_not_running()]] - code - tests/unit/brokers/dhan/test_websocket.py
- [[.test_subscribe_async()]] - code - tests/unit/brokers/dhan/test_websocket.py
- [[.test_subscriber_error_isolated()]] - code - tests/unit/brokers/dhan/test_websocket.py
- [[.test_unsubscribe_async()]] - code - tests/unit/brokers/dhan/test_websocket.py
- [[Helper to create a manager with mocked dependencies.]] - rationale - tests/unit/brokers/dhan/test_websocket.py
- [[TestManagerHealthMonitoring]] - code - tests/unit/brokers/dhan/test_websocket.py
- [[TestManagerLifecycle]] - code - tests/unit/brokers/dhan/test_websocket.py
- [[TestManagerReconnection]] - code - tests/unit/brokers/dhan/test_websocket.py
- [[TestManagerSubscriberManagement]] - code - tests/unit/brokers/dhan/test_websocket.py
- [[TestManagerSubscriptions]] - code - tests/unit/brokers/dhan/test_websocket.py
- [[Tests for addremove subscriber and tick distribution.]] - rationale - tests/unit/brokers/dhan/test_websocket.py
- [[Tests for health status and metrics.]] - rationale - tests/unit/brokers/dhan/test_websocket.py
- [[Tests for reconnection logic.]] - rationale - tests/unit/brokers/dhan/test_websocket.py
- [[Tests for startstop lifecycle.]] - rationale - tests/unit/brokers/dhan/test_websocket.py
- [[Tests for subscribeunsubscribe tracking.]] - rationale - tests/unit/brokers/dhan/test_websocket.py
- [[_make_manager()]] - code - tests/unit/brokers/dhan/test_websocket.py
- [[_make_tick()]] - code - tests/unit/brokers/dhan/test_websocket.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Tests_Unit/Brokers
SORT file.name ASC
```

## Connections to other communities
- 23 edges to [[_COMMUNITY_Market - Data]]
- 6 edges to [[_COMMUNITY_Dhan Broker Integration]]
- 5 edges to [[_COMMUNITY_Dhan Broker Integration_1]]

## Top bridge nodes
- [[TestManagerLifecycle]] - degree 15, connects to 3 communities
- [[TestManagerSubscriberManagement]] - degree 13, connects to 3 communities
- [[TestManagerHealthMonitoring]] - degree 11, connects to 3 communities
- [[TestManagerSubscriptions]] - degree 11, connects to 3 communities
- [[TestManagerReconnection]] - degree 10, connects to 3 communities
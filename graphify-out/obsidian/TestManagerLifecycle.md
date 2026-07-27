---
source_file: "tests/unit/brokers/dhan/test_websocket.py"
type: "code"
community: "Tests: Unit/Brokers"
location: "L101"
tags:
  - graphify/code
  - graphify/EXTRACTED
  - community/Tests_Unit/Brokers
---

# TestManagerLifecycle

## Connections
- [[.test_context_manager()]] - `method` [EXTRACTED]
- [[.test_start_connects_and_creates_tasks()]] - `method` [EXTRACTED]
- [[.test_start_ignores_duplicate()]] - `method` [EXTRACTED]
- [[.test_start_reraises_on_failure()]] - `method` [EXTRACTED]
- [[.test_start_restores_subscriptions()]] - `method` [EXTRACTED]
- [[.test_start_stop_idempotent()]] - `method` [EXTRACTED]
- [[.test_stop_drains_queue()]] - `method` [EXTRACTED]
- [[.test_stop_ignores_when_not_running()]] - `method` [EXTRACTED]
- [[ConnectionStatus]] - `uses` [INFERRED]
- [[DhanWebSocketClient]] - `uses` [INFERRED]
- [[DhanWebSocketManager]] - `uses` [INFERRED]
- [[HealthMetrics]] - `uses` [INFERRED]
- [[Tests for startstop lifecycle.]] - `rationale_for` [EXTRACTED]
- [[Tick]] - `uses` [INFERRED]
- [[test_websocket.py]] - `contains` [EXTRACTED]

#graphify/code #graphify/EXTRACTED #community/Tests_Unit/Brokers
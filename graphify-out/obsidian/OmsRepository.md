---
source_file: "scalpr/oms/persistence.py"
type: "code"
community: "Tests: Unit/Brokers"
location: "L13"
tags:
  - graphify/code
  - graphify/EXTRACTED
  - community/Tests_Unit/Brokers
---

# OmsRepository

## Connections
- [[.__init__()_25]] - `references` [EXTRACTED]
- [[.__init__()_27]] - `method` [EXTRACTED]
- [[._init_db()_1]] - `method` [EXTRACTED]
- [[.repository()]] - `calls` [EXTRACTED]
- [[.restore_orders()]] - `method` [EXTRACTED]
- [[.restore_positions()]] - `method` [EXTRACTED]
- [[.save_fill()]] - `method` [EXTRACTED]
- [[.save_order()]] - `method` [EXTRACTED]
- [[.save_position()]] - `method` [EXTRACTED]
- [[.test_crash_recovery()]] - `calls` [EXTRACTED]
- [[.test_restore_state_with_empty_database()]] - `calls` [EXTRACTED]
- [[ConnectionManager]] - `uses` [INFERRED]
- [[Exchange_4]] - `uses` [INFERRED]
- [[Fill]] - `uses` [INFERRED]
- [[Order]] - `uses` [INFERRED]
- [[OrderManager]] - `uses` [INFERRED]
- [[OrderSide_1]] - `uses` [INFERRED]
- [[OrderState]] - `uses` [INFERRED]
- [[OrderType]] - `uses` [INFERRED]
- [[Position]] - `uses` [INFERRED]
- [[PositionSide]] - `uses` [INFERRED]
- [[PositionState]] - `uses` [INFERRED]
- [[SQLite persistence layer for Order Management System state, with WAL mode enable]] - `rationale_for` [EXTRACTED]
- [[TestOMSPersistenceWiring]] - `uses` [INFERRED]
- [[main.py]] - `imports` [EXTRACTED]
- [[order_manager.py]] - `imports` [EXTRACTED]
- [[persistence.py]] - `contains` [EXTRACTED]
- [[test_oms_repository_save_restore()]] - `calls` [EXTRACTED]
- [[test_oms_risk.py]] - `imports` [EXTRACTED]
- [[test_persistence_wiring.py]] - `imports` [EXTRACTED]

#graphify/code #graphify/EXTRACTED #community/Tests_Unit/Brokers
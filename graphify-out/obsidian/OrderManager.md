---
source_file: "scalpr/oms/order_manager.py"
type: "code"
community: "Oms - Order"
location: "L16"
tags:
  - graphify/code
  - graphify/EXTRACTED
  - community/Oms_-_Order
---

# OrderManager

## Connections
- [[.__init__()_17]] - `references` [EXTRACTED]
- [[.__init__()_25]] - `method` [EXTRACTED]
- [[._log_event()]] - `method` [EXTRACTED]
- [[.add_order()]] - `method` [EXTRACTED]
- [[.get_order()]] - `method` [EXTRACTED]
- [[.get_orders()_2]] - `method` [EXTRACTED]
- [[.order_manager_with_persistence()]] - `calls` [EXTRACTED]
- [[.process_fill()]] - `method` [EXTRACTED]
- [[.restore_state()]] - `method` [EXTRACTED]
- [[.test_crash_recovery()]] - `calls` [EXTRACTED]
- [[.test_persistence_failure_doesnt_break_order_flow()]] - `calls` [EXTRACTED]
- [[.test_restore_state_with_empty_database()]] - `calls` [EXTRACTED]
- [[.update_order_state()]] - `method` [EXTRACTED]
- [[CircuitBreakerTripped_2]] - `uses` [INFERRED]
- [[ConnectionManager]] - `uses` [INFERRED]
- [[Fill]] - `uses` [INFERRED]
- [[Manages order lifecycles, FSM state changes, fill accumulation, and audit trails]] - `rationale_for` [EXTRACTED]
- [[OmsRepository]] - `uses` [INFERRED]
- [[Order]] - `uses` [INFERRED]
- [[OrderRouter]] - `uses` [INFERRED]
- [[OrderState]] - `uses` [INFERRED]
- [[RiskCheckFailed_2]] - `uses` [INFERRED]
- [[TestOMSPersistenceWiring]] - `uses` [INFERRED]
- [[main.py]] - `imports` [EXTRACTED]
- [[order_manager.py]] - `contains` [EXTRACTED]
- [[order_router.py]] - `imports` [EXTRACTED]
- [[test_oms_risk.py]] - `imports` [EXTRACTED]
- [[test_order_manager_fill_accumulation()]] - `calls` [EXTRACTED]
- [[test_persistence_wiring.py]] - `imports` [EXTRACTED]

#graphify/code #graphify/EXTRACTED #community/Oms_-_Order
---
type: community
cohesion: 0.07
members: 28
---

# Tests: Unit/Oms

**Cohesion:** 0.07 - loosely connected
**Members:** 28 nodes

## Members
- [[.order_manager_with_persistence()]] - code - tests/unit/oms/test_persistence_wiring.py
- [[.repository()]] - code - tests/unit/oms/test_persistence_wiring.py
- [[.sample_fill()]] - code - tests/unit/oms/test_persistence_wiring.py
- [[.sample_order()]] - code - tests/unit/oms/test_persistence_wiring.py
- [[.temp_db()]] - code - tests/unit/oms/test_persistence_wiring.py
- [[.test_crash_recovery()]] - code - tests/unit/oms/test_persistence_wiring.py
- [[.test_fill_persisted_on_process()]] - code - tests/unit/oms/test_persistence_wiring.py
- [[.test_get_orders_returns_list()]] - code - tests/unit/oms/test_persistence_wiring.py
- [[.test_multiple_orders_persisted()]] - code - tests/unit/oms/test_persistence_wiring.py
- [[.test_order_persisted_on_add()]] - code - tests/unit/oms/test_persistence_wiring.py
- [[.test_order_update_persisted()]] - code - tests/unit/oms/test_persistence_wiring.py
- [[.test_persistence_failure_doesnt_break_order_flow()]] - code - tests/unit/oms/test_persistence_wiring.py
- [[.test_restore_state_with_empty_database()]] - code - tests/unit/oms/test_persistence_wiring.py
- [[Create OmsRepository instance.]] - rationale - tests/unit/oms/test_persistence_wiring.py
- [[Create OrderManager with persistence.]] - rationale - tests/unit/oms/test_persistence_wiring.py
- [[Create a sample fill.]] - rationale - tests/unit/oms/test_persistence_wiring.py
- [[Create a sample order for testing.]] - rationale - tests/unit/oms/test_persistence_wiring.py
- [[Create temporary database for testing.]] - rationale - tests/unit/oms/test_persistence_wiring.py
- [[Test OMS persistence integration with OrderManager.]] - rationale - tests/unit/oms/test_persistence_wiring.py
- [[Test get_orders returns list of orders.]] - rationale - tests/unit/oms/test_persistence_wiring.py
- [[Test multiple orders are all persisted.]] - rationale - tests/unit/oms/test_persistence_wiring.py
- [[Test restore_state works with empty database.]] - rationale - tests/unit/oms/test_persistence_wiring.py
- [[Test that order state transitions are persisted.]] - rationale - tests/unit/oms/test_persistence_wiring.py
- [[Test that orders survive process restart (crash recovery).]] - rationale - tests/unit/oms/test_persistence_wiring.py
- [[TestOMSPersistenceWiring]] - code - tests/unit/oms/test_persistence_wiring.py
- [[Verify fill is persisted when processed.]] - rationale - tests/unit/oms/test_persistence_wiring.py
- [[Verify order is persisted to database when added.]] - rationale - tests/unit/oms/test_persistence_wiring.py
- [[Verify that persistence failure doesn't break order submission.]] - rationale - tests/unit/oms/test_persistence_wiring.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Tests_Unit/Oms
SORT file.name ASC
```

## Connections to other communities
- 9 edges to [[_COMMUNITY_Tests UnitBrokers]]
- 8 edges to [[_COMMUNITY_Oms - Order]]
- 2 edges to [[_COMMUNITY_Domain Events]]

## Top bridge nodes
- [[TestOMSPersistenceWiring]] - degree 23, connects to 3 communities
- [[.test_crash_recovery()]] - degree 4, connects to 2 communities
- [[.test_restore_state_with_empty_database()]] - degree 4, connects to 2 communities
- [[.order_manager_with_persistence()]] - degree 3, connects to 1 community
- [[.repository()]] - degree 3, connects to 1 community
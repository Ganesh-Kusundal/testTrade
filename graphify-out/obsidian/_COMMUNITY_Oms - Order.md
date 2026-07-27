---
type: community
cohesion: 0.04
members: 110
---

# Oms - Order

**Cohesion:** 0.04 - loosely connected
**Members:** 110 nodes

## Members
- [[.__init__()_17]] - code - scalpr/execution/order_router.py
- [[.__init__()_25]] - code - scalpr/oms/order_manager.py
- [[.__init__()_31]] - code - scalpr/risk/pre_trade.py
- [[.__post_init__()_2]] - code - scalpr/domain/fill.py
- [[.__post_init__()_4]] - code - scalpr/domain/order.py
- [[.__post_init__()_5]] - code - scalpr/domain/position.py
- [[._log_event()]] - code - scalpr/oms/order_manager.py
- [[.add_order()]] - code - scalpr/oms/order_manager.py
- [[.check_order()]] - code - scalpr/risk/pre_trade.py
- [[.get_holdings()]] - code - scalpr/brokers/broker_port.py
- [[.get_holdings()_1]] - code - scalpr/brokers/dhan/gateway.py
- [[.get_order()]] - code - scalpr/oms/order_manager.py
- [[.get_order_status()]] - code - scalpr/brokers/broker_port.py
- [[.get_orders()]] - code - scalpr/brokers/broker_port.py
- [[.get_orders()_2]] - code - scalpr/oms/order_manager.py
- [[.get_positions()]] - code - scalpr/brokers/broker_port.py
- [[.process_fill()]] - code - scalpr/oms/order_manager.py
- [[.save_order()]] - code - scalpr/oms/persistence.py
- [[.save_position()]] - code - scalpr/oms/persistence.py
- [[.submit_order()]] - code - scalpr/execution/order_router.py
- [[.test_circuit_breaker_event_published()]] - code - tests/unit/test_event_bus_wiring.py
- [[.test_full_event_flow_integration()]] - code - tests/unit/test_event_bus_wiring.py
- [[.test_order_placed_event_published()]] - code - tests/unit/test_event_bus_wiring.py
- [[.test_risk_check_failed_event_published()]] - code - tests/unit/test_event_bus_wiring.py
- [[.test_should_skip_zero_quantity_positions()]] - code - tests/unit/brokers/dhan/test_gateway_connection.py
- [[.test_should_use_ltp_as_price_when_available()]] - code - tests/unit/brokers/dhan/test_gateway_connection.py
- [[.test_should_use_zero_price_when_ltp_is_zero()]] - code - tests/unit/brokers/dhan/test_gateway_connection.py
- [[.transition_to()]] - code - scalpr/domain/order.py
- [[.update_order_state()]] - code - scalpr/oms/order_manager.py
- [[A long position for testing.]] - rationale - tests/unit/brokers/dhan/test_gateway_connection.py
- [[A short position for testing.]] - rationale - tests/unit/brokers/dhan/test_gateway_connection.py
- [[A standard BUY LIMIT order.]] - rationale - tests/unit/brokers/dhan/test_gateway_connection.py
- [[Abstract interface for event bus publishsubscribe.]] - rationale - scalpr/domain/events.py
- [[Atomically transition order state and record event.]] - rationale - scalpr/oms/order_manager.py
- [[Check order. Returns (allowed bool, reason str).]] - rationale - scalpr/risk/pre_trade.py
- [[CircuitBreaker_1]] - code
- [[CircuitBreakerTripped_2]] - code - scalpr/execution/order_router.py
- [[Decimal_10]] - code
- [[Decimal_16]] - code
- [[Dhan broker gateway — thin facade over DhanConnection implementing IBrokerGatewa]] - rationale - scalpr/brokers/dhan/gateway.py
- [[Exception]] - code
- [[Fetch current open positions.]] - rationale - scalpr/brokers/broker_port.py
- [[Fetch long-term delivery holdings.]] - rationale - scalpr/brokers/broker_port.py
- [[Fetch long-term delivery holdings.          Returns             List of Positio]] - rationale - scalpr/brokers/dhan/gateway.py
- [[Fetch the current status of an order.]] - rationale - scalpr/brokers/broker_port.py
- [[Fetch the full orderbook.]] - rationale - scalpr/brokers/broker_port.py
- [[Get all orders as a list.]] - rationale - scalpr/oms/order_manager.py
- [[IEventBus]] - code - scalpr/domain/events.py
- [[Integration tests for event bus wiring in production flow.]] - rationale - tests/unit/test_event_bus_wiring.py
- [[Manages order lifecycles, FSM state changes, fill accumulation, and audit trails]] - rationale - scalpr/oms/order_manager.py
- [[Mandatory order submission router that enforces risk gates.          All strateg]] - rationale - scalpr/execution/order_router.py
- [[OmsRepository correctly persists and restores orders and positions in SQLite.]] - rationale - tests/unit/oms/test_oms_risk.py
- [[Order]] - code - scalpr/domain/order.py
- [[Order Router - Enforces mandatory risk checks before order submission.]] - rationale - scalpr/execution/order_router.py
- [[Order represents an order execution request and status.]] - rationale - scalpr/domain/order.py
- [[OrderManager]] - code - scalpr/oms/order_manager.py
- [[OrderManager accumulates partial fills and transitions order to FILLED once comp]] - rationale - tests/unit/oms/test_oms_risk.py
- [[OrderRouter]] - code - scalpr/execution/order_router.py
- [[OrderState FSM with validated transitions raises ValueError on invalid moves.]] - rationale - tests/unit/domain/test_domain.py
- [[PaperOms executes fills and tracks current drawdown based on mark-to-market pric]] - rationale - tests/unit/oms/test_oms_risk.py
- [[Partial execution fill details.]] - rationale - scalpr/domain/fill.py
- [[PartialFill]] - code - scalpr/domain/fill.py
- [[Persist open position parameters.]] - rationale - scalpr/oms/persistence.py
- [[Persist or update an order in the database.]] - rationale - scalpr/oms/persistence.py
- [[Position]] - code - scalpr/domain/position.py
- [[Position PnL is calculated correctly using Decimal only.]] - rationale - tests/unit/domain/test_domain.py
- [[Position tracks open trading contract exposure, average entry, and PnL.]] - rationale - scalpr/domain/position.py
- [[Positions with quantity=0 must be skipped.]] - rationale - tests/unit/brokers/dhan/test_gateway_connection.py
- [[Pre-trade risk gateway that validates order submission against account limits.]] - rationale - scalpr/risk/pre_trade.py
- [[PreTradeRiskGate]] - code - scalpr/risk/pre_trade.py
- [[PreTradeRiskGate validates max positions, capital risk limit, and concentration]] - rationale - tests/unit/oms/test_oms_risk.py
- [[Process execution fill, update average price, and accumulate filled quantity.]] - rationale - scalpr/oms/order_manager.py
- [[Raised when circuit breaker prevents order submission.]] - rationale - scalpr/execution/order_router.py
- [[Raised when pre-trade risk check fails.]] - rationale - scalpr/execution/order_router.py
- [[Register a new order. Deduplicates by order_id.]] - rationale - scalpr/oms/order_manager.py
- [[RiskCheckFailed_2]] - code - scalpr/execution/order_router.py
- [[Square-off order must use position LTP as price when LTP  0.]] - rationale - tests/unit/brokers/dhan/test_gateway_connection.py
- [[Square-off order must use price=0 when position LTP is 0.]] - rationale - tests/unit/brokers/dhan/test_gateway_connection.py
- [[Submit order through mandatory risk gates.                  Args             or]] - rationale - scalpr/execution/order_router.py
- [[Test complete event flow Tick → Order → Fill → Position.]] - rationale - tests/unit/test_event_bus_wiring.py
- [[Test that events are properly published through the production flow.]] - rationale - tests/unit/test_event_bus_wiring.py
- [[TestEventBusWiring]] - code - tests/unit/test_event_bus_wiring.py
- [[Validate FSM transitions and return a new Order copy.]] - rationale - scalpr/domain/order.py
- [[Verify CircuitBreakerTripped event is published when limits exceeded.]] - rationale - tests/unit/test_event_bus_wiring.py
- [[Verify OrderPlaced event is published when order passes risk checks.]] - rationale - tests/unit/test_event_bus_wiring.py
- [[Verify RiskCheckFailed event is published when pre-trade check fails.]] - rationale - tests/unit/test_event_bus_wiring.py
- [[__init__.py_5]] - code - scalpr/execution/__init__.py
- [[broker_port.py]] - code - scalpr/brokers/broker_port.py
- [[circuit_breaker.py]] - code - scalpr/risk/circuit_breaker.py
- [[fill.py]] - code - scalpr/domain/fill.py
- [[gateway.py]] - code - scalpr/brokers/dhan/gateway.py
- [[order.py]] - code - scalpr/domain/order.py
- [[order_manager.py]] - code - scalpr/oms/order_manager.py
- [[order_router.py]] - code - scalpr/execution/order_router.py
- [[paper_oms.py]] - code - scalpr/oms/paper_oms.py
- [[persistence.py]] - code - scalpr/oms/persistence.py
- [[position.py]] - code - scalpr/domain/position.py
- [[pre_trade.py]] - code - scalpr/risk/pre_trade.py
- [[sample_order()]] - code - tests/unit/brokers/dhan/test_gateway_connection.py
- [[sample_position_long()]] - code - tests/unit/brokers/dhan/test_gateway_connection.py
- [[sample_position_short()]] - code - tests/unit/brokers/dhan/test_gateway_connection.py
- [[test_domain.py]] - code - tests/unit/domain/test_domain.py
- [[test_event_bus_wiring.py]] - code - tests/unit/test_event_bus_wiring.py
- [[test_oms_repository_save_restore()]] - code - tests/unit/oms/test_oms_risk.py
- [[test_oms_risk.py]] - code - tests/unit/oms/test_oms_risk.py
- [[test_order_manager_fill_accumulation()]] - code - tests/unit/oms/test_oms_risk.py
- [[test_order_state_invalid_transition_raises()]] - code - tests/unit/domain/test_domain.py
- [[test_paper_oms_drawdown_calculation()]] - code - tests/unit/oms/test_oms_risk.py
- [[test_position_pnl_calculation()]] - code - tests/unit/domain/test_domain.py
- [[test_pre_trade_risk_gate()]] - code - tests/unit/oms/test_oms_risk.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Oms_-_Order
SORT file.name ASC
```

## Connections to other communities
- 151 edges to [[_COMMUNITY_Tests UnitBrokers]]
- 128 edges to [[_COMMUNITY_Domain Events]]
- 72 edges to [[_COMMUNITY_Tests UnitTesting]]
- 34 edges to [[_COMMUNITY_Tests UnitBrokers_1]]
- 26 edges to [[_COMMUNITY_Dhan Broker Integration_2]]
- 21 edges to [[_COMMUNITY_Oms - Paper]]
- 15 edges to [[_COMMUNITY_Signals - Gate]]
- 10 edges to [[_COMMUNITY_API Server]]
- 10 edges to [[_COMMUNITY_Backtester]]
- 9 edges to [[_COMMUNITY_Market - Data]]
- 8 edges to [[_COMMUNITY_Tests UnitOms]]
- 6 edges to [[_COMMUNITY_Domain Position Model]]
- 5 edges to [[_COMMUNITY_Portfolio Management]]
- 4 edges to [[_COMMUNITY_Risk - Session]]
- 4 edges to [[_COMMUNITY_Logging System]]
- 4 edges to [[_COMMUNITY_Dhan Broker Integration_8]]
- 3 edges to [[_COMMUNITY_Market - Data_1]]
- 3 edges to [[_COMMUNITY_Tests UnitBrokers_2]]
- 3 edges to [[_COMMUNITY_Dhan Broker Integration_13]]
- 3 edges to [[_COMMUNITY_Scanner - Options]]
- 3 edges to [[_COMMUNITY_Domain Order Model]]
- 3 edges to [[_COMMUNITY_Tests UnitBrokers_6]]
- 3 edges to [[_COMMUNITY_Risk - Position]]
- 2 edges to [[_COMMUNITY_Broker Registry]]
- 2 edges to [[_COMMUNITY_Tests UnitBrokers_4]]
- 2 edges to [[_COMMUNITY_Tests UnitBrokers_8]]
- 2 edges to [[_COMMUNITY_Tests UnitBrokers_7]]
- 2 edges to [[_COMMUNITY_Tests UnitObservability]]
- 1 edge to [[_COMMUNITY_Brokers - Broker_1]]
- 1 edge to [[_COMMUNITY_Broker Contracts]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers_3]]
- 1 edge to [[_COMMUNITY_Domain Order Model_1]]
- 1 edge to [[_COMMUNITY_Domain Order Model_2]]
- 1 edge to [[_COMMUNITY_Observability - Event]]
- 1 edge to [[_COMMUNITY_Oms - Order_1]]
- 1 edge to [[_COMMUNITY_Risk - Circuit]]

## Top bridge nodes
- [[Order]] - degree 176, connects to 21 communities
- [[Position]] - degree 125, connects to 15 communities
- [[gateway.py]] - degree 24, connects to 9 communities
- [[order.py]] - degree 35, connects to 8 communities
- [[broker_port.py]] - degree 18, connects to 8 communities
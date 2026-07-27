---
source_file: "scalpr/brokers/dhan/gateway.py"
type: "code"
community: "Tests: Unit/Brokers"
location: "L33"
tags:
  - graphify/code
  - graphify/EXTRACTED
  - community/Tests_Unit/Brokers
---

# DhanGateway

## Connections
- [[.__init__()_2]] - `method` [EXTRACTED]
- [[._map_raw_order_to_order()]] - `method` [EXTRACTED]
- [[._map_raw_trade_to_fill()]] - `method` [EXTRACTED]
- [[.cancel_order()_1]] - `method` [EXTRACTED]
- [[.connect()_4]] - `method` [EXTRACTED]
- [[.connection()]] - `method` [EXTRACTED]
- [[.disconnect()_4]] - `method` [EXTRACTED]
- [[.get_fund_limits()_1]] - `method` [EXTRACTED]
- [[.get_holdings()_1]] - `method` [EXTRACTED]
- [[.get_ltp()_1]] - `method` [EXTRACTED]
- [[.get_margins()_1]] - `method` [EXTRACTED]
- [[.get_ohlcv()_1]] - `method` [EXTRACTED]
- [[.get_order_status()_1]] - `method` [EXTRACTED]
- [[.get_orders()_1]] - `method` [EXTRACTED]
- [[.get_positions()_1]] - `method` [EXTRACTED]
- [[.get_quote()_1]] - `method` [EXTRACTED]
- [[.get_tradebook()_1]] - `method` [EXTRACTED]
- [[.is_connected()_2]] - `method` [EXTRACTED]
- [[.modify_order()_1]] - `method` [EXTRACTED]
- [[.place_order()_1]] - `method` [EXTRACTED]
- [[.square_off_all()_1]] - `method` [EXTRACTED]
- [[.test_should_create_dhan_connection_with_config()]] - `calls` [EXTRACTED]
- [[.test_should_instantiate_with_valid_config()]] - `calls` [EXTRACTED]
- [[BrokerError]] - `uses` [INFERRED]
- [[BrokerRegistry]] - `uses` [INFERRED]
- [[ConnectionManager]] - `uses` [INFERRED]
- [[DhanConnection]] - `uses` [INFERRED]
- [[Exchange_4]] - `uses` [INFERRED]
- [[Fill]] - `uses` [INFERRED]
- [[IBrokerGateway]] - `uses` [INFERRED]
- [[MockHttpClient]] - `uses` [INFERRED]
- [[Order]] - `uses` [INFERRED]
- [[OrderSide_1]] - `uses` [INFERRED]
- [[OrderState]] - `uses` [INFERRED]
- [[OrderType]] - `uses` [INFERRED]
- [[Position]] - `uses` [INFERRED]
- [[Production Dhan broker gateway implementing IBrokerGateway.      Thin facade ove]] - `rationale_for` [EXTRACTED]
- [[TestDhanConnectionAdapterProperties]] - `uses` [INFERRED]
- [[TestDhanConnectionConfigValidation]] - `uses` [INFERRED]
- [[TestDhanConnectionHttpClientConfig]] - `uses` [INFERRED]
- [[TestDhanConnectionLifecycle]] - `uses` [INFERRED]
- [[TestDhanConnectionStateTracking]] - `uses` [INFERRED]
- [[TestDhanConnectionThreadSafety]] - `uses` [INFERRED]
- [[TestDhanConnectionTokenRefresh]] - `uses` [INFERRED]
- [[TestDhanGatewayConnectionProperty]] - `uses` [INFERRED]
- [[TestDhanGatewayErrorPropagation]] - `uses` [INFERRED]
- [[TestDhanGatewayFullDelegationChain]] - `uses` [INFERRED]
- [[TestDhanGatewayHistoricalDelegation]] - `uses` [INFERRED]
- [[TestDhanGatewayInterfaceCompliance]] - `uses` [INFERRED]
- [[TestDhanGatewayLifecycleDelegation]] - `uses` [INFERRED]
- [[TestDhanGatewayMarketDataDelegation]] - `uses` [INFERRED]
- [[TestDhanGatewayOrderDelegation]] - `uses` [INFERRED]
- [[TestDhanGatewayOrderMapping]] - `uses` [INFERRED]
- [[TestDhanGatewayPortfolioDelegation]] - `uses` [INFERRED]
- [[TestDhanGatewaySquareOff]] - `uses` [INFERRED]
- [[_make_gateway()]] - `calls` [EXTRACTED]
- [[gateway.py]] - `contains` [EXTRACTED]
- [[main.py]] - `imports` [EXTRACTED]
- [[mocked_gateway_connection()]] - `calls` [EXTRACTED]
- [[registry.py]] - `imports` [EXTRACTED]
- [[test_gateway.py]] - `imports` [EXTRACTED]
- [[test_gateway_connection.py]] - `imports` [EXTRACTED]

#graphify/code #graphify/EXTRACTED #community/Tests_Unit/Brokers
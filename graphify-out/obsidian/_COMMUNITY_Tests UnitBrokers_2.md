---
type: community
cohesion: 0.04
members: 49
---

# Tests: Unit/Brokers

**Cohesion:** 0.04 - loosely connected
**Members:** 49 nodes

## Members
- [[.__init__()_2]] - code - scalpr/brokers/dhan/gateway.py
- [[._map_raw_order_to_order()]] - code - scalpr/brokers/dhan/gateway.py
- [[._map_raw_trade_to_fill()]] - code - scalpr/brokers/dhan/gateway.py
- [[.get_ltp()_1]] - code - scalpr/brokers/dhan/gateway.py
- [[.get_ohlcv()_1]] - code - scalpr/brokers/dhan/gateway.py
- [[.get_orders()_1]] - code - scalpr/brokers/dhan/gateway.py
- [[.get_quote()_1]] - code - scalpr/brokers/dhan/gateway.py
- [[.get_tradebook()_1]] - code - scalpr/brokers/dhan/gateway.py
- [[.modify_order()_1]] - code - scalpr/brokers/dhan/gateway.py
- [[.test_should_default_to_limit_for_unknown_order_type()]] - code - tests/unit/brokers/dhan/test_gateway_connection.py
- [[.test_should_default_to_nse_exchange()]] - code - tests/unit/brokers/dhan/test_gateway_connection.py
- [[.test_should_default_to_pending_for_unknown_status()]] - code - tests/unit/brokers/dhan/test_gateway_connection.py
- [[.test_should_handle_missing_optional_fields()]] - code - tests/unit/brokers/dhan/test_gateway_connection.py
- [[.test_should_map_all_order_states()]] - code - tests/unit/brokers/dhan/test_gateway_connection.py
- [[.test_should_map_correlation_id()]] - code - tests/unit/brokers/dhan/test_gateway_connection.py
- [[.test_should_map_filled_buy_limit_order()]] - code - tests/unit/brokers/dhan/test_gateway_connection.py
- [[.test_should_map_mcx_exchange()]] - code - tests/unit/brokers/dhan/test_gateway_connection.py
- [[.test_should_map_reject_reason()]] - code - tests/unit/brokers/dhan/test_gateway_connection.py
- [[.test_should_map_sell_market_order()]] - code - tests/unit/brokers/dhan/test_gateway_connection.py
- [[.test_should_map_sl_order_to_stop_loss()]] - code - tests/unit/brokers/dhan/test_gateway_connection.py
- [[.test_should_map_slm_order_to_stop_loss_market()]] - code - tests/unit/brokers/dhan/test_gateway_connection.py
- [[.test_should_map_stop_loss_full_name_to_stop_loss()]] - code - tests/unit/brokers/dhan/test_gateway_connection.py
- [[.test_should_map_stop_loss_market_full_name()]] - code - tests/unit/brokers/dhan/test_gateway_connection.py
- [[A SELL MARKET order must map correctly.]] - rationale - tests/unit/brokers/dhan/test_gateway_connection.py
- [[A filled BUY LIMIT order must map to OrderState.FILLED and OrderSide.BUY.]] - rationale - tests/unit/brokers/dhan/test_gateway_connection.py
- [[All Dhan status strings must map to correct OrderState.]] - rationale - tests/unit/brokers/dhan/test_gateway_connection.py
- [[Any_4]] - code
- [[Correlation ID must be mapped from raw data.]] - rationale - tests/unit/brokers/dhan/test_gateway_connection.py
- [[Decimal_1]] - code
- [[Dhan 'SL' order type must map to OrderType.STOP_LOSS.]] - rationale - tests/unit/brokers/dhan/test_gateway_connection.py
- [[Dhan 'SL-M' order type must map to OrderType.STOP_LOSS_MARKET.]] - rationale - tests/unit/brokers/dhan/test_gateway_connection.py
- [[Dhan 'STOP LOSS MARKET' must map to OrderType.STOP_LOSS_MARKET.]] - rationale - tests/unit/brokers/dhan/test_gateway_connection.py
- [[Dhan 'STOP LOSS' order type must map to OrderType.STOP_LOSS.]] - rationale - tests/unit/brokers/dhan/test_gateway_connection.py
- [[Fetch historical OHLCV candlestick data.          Delegates to HistoricalDataAda]] - rationale - scalpr/brokers/dhan/gateway.py
- [[Fetch the day's tradebook (execution fills) from Dhan.          Returns]] - rationale - scalpr/brokers/dhan/gateway.py
- [[Fetch the full orderbook from Dhan.          Returns             List of Order]] - rationale - scalpr/brokers/dhan/gateway.py
- [[Get Last Traded Price for a symbol.          Args             symbol Trading s]] - rationale - scalpr/brokers/dhan/gateway.py
- [[Get full market quote for a symbol.          Args             symbol Trading s]] - rationale - scalpr/brokers/dhan/gateway.py
- [[Initialise DhanGateway with configuration.          Args             config Co]] - rationale - scalpr/brokers/dhan/gateway.py
- [[MCX exchange segment must map to Exchange.MCX.]] - rationale - tests/unit/brokers/dhan/test_gateway_connection.py
- [[Map a raw orderbook entry to a SCALPR Order domain object.          Args]] - rationale - scalpr/brokers/dhan/gateway.py
- [[Map a raw tradebook entry to a SCALPR Fill domain object.          Args]] - rationale - scalpr/brokers/dhan/gateway.py
- [[Missing optional fields must use sensible defaults.]] - rationale - tests/unit/brokers/dhan/test_gateway_connection.py
- [[Modify an existing order's price, quantity, andor trigger price.          Args]] - rationale - scalpr/brokers/dhan/gateway.py
- [[Reject reason must be mapped from raw data.]] - rationale - tests/unit/brokers/dhan/test_gateway_connection.py
- [[Unknown exchange segment must default to Exchange.NSE.]] - rationale - tests/unit/brokers/dhan/test_gateway_connection.py
- [[Unknown order type must default to OrderType.LIMIT.]] - rationale - tests/unit/brokers/dhan/test_gateway_connection.py
- [[Unknown status string must default to OrderState.PENDING.]] - rationale - tests/unit/brokers/dhan/test_gateway_connection.py
- [[date_1]] - code

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Tests_Unit/Brokers
SORT file.name ASC
```

## Connections to other communities
- 23 edges to [[_COMMUNITY_Tests UnitBrokers]]
- 3 edges to [[_COMMUNITY_Oms - Order]]
- 2 edges to [[_COMMUNITY_Domain Events]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers_3]]
- 1 edge to [[_COMMUNITY_Dhan Broker Integration_13]]
- 1 edge to [[_COMMUNITY_Tests UnitTesting]]

## Top bridge nodes
- [[._map_raw_order_to_order()]] - degree 21, connects to 3 communities
- [[._map_raw_trade_to_fill()]] - degree 6, connects to 2 communities
- [[Decimal_1]] - degree 6, connects to 2 communities
- [[.get_orders()_1]] - degree 4, connects to 2 communities
- [[.get_tradebook()_1]] - degree 4, connects to 2 communities
---
source_file: "scalpr/brokers/dhan/orders.py"
type: "code"
community: "Tests: Unit/Brokers"
location: "L31"
tags:
  - graphify/code
  - graphify/INFERRED
  - community/Tests_Unit/Brokers
---

# OrdersAdapter

## Connections
- [[.__init__()_8]] - `method` [EXTRACTED]
- [[._validate_order()]] - `method` [EXTRACTED]
- [[.cancel_order()_2]] - `method` [EXTRACTED]
- [[.clear_idempotency_cache()]] - `method` [EXTRACTED]
- [[.connect()_3]] - `calls` [EXTRACTED]
- [[.get_orderbook()]] - `method` [EXTRACTED]
- [[.get_tradebook()_2]] - `method` [EXTRACTED]
- [[.modify_order()_2]] - `method` [EXTRACTED]
- [[.orders()]] - `references` [EXTRACTED]
- [[.place_order()_2]] - `method` [EXTRACTED]
- [[.test_limit_order_uses_price_fallback()]] - `calls` [EXTRACTED]
- [[.test_market_order_with_fill_uses_traded_price()]] - `calls` [EXTRACTED]
- [[.test_market_order_with_zero_fill_price_logs_warning()]] - `calls` [EXTRACTED]
- [[.test_mcx_order_uses_correct_segment_and_string_prices()]] - `calls` [EXTRACTED]
- [[.test_modify_order_uses_string_prices()]] - `calls` [EXTRACTED]
- [[.test_orders_api_receives_string_not_float()]] - `calls` [EXTRACTED]
- [[Adapter for order operations against Dhan API.      Provides methods for     -]] - `rationale_for` [EXTRACTED]
- [[DhanConnection]] - `uses` [INFERRED]
- [[DhanHttpClient]] - `uses` [INFERRED]
- [[DhanMapper]] - `uses` [INFERRED]
- [[DhanOrderResponse]] - `uses` [INFERRED]
- [[Fill]] - `uses` [INFERRED]
- [[Order]] - `uses` [INFERRED]
- [[OrderError]] - `uses` [INFERRED]
- [[OrderState]] - `uses` [INFERRED]
- [[OrderType]] - `uses` [INFERRED]
- [[SymbolResolver]] - `uses` [INFERRED]
- [[TestDecimalPrecision]] - `uses` [INFERRED]
- [[TestEndToEndSecurityIdFlow]] - `uses` [INFERRED]
- [[TestHistoricalDataAdapter]] - `uses` [INFERRED]
- [[TestHistoricalSecurityIdUsage]] - `uses` [INFERRED]
- [[TestIntegrationFixes]] - `uses` [INFERRED]
- [[TestMCXSegmentFix]] - `uses` [INFERRED]
- [[TestMarketDataAdapter]] - `uses` [INFERRED]
- [[TestMarketOrderFills]] - `uses` [INFERRED]
- [[TestOptionsScannerSecurityIds]] - `uses` [INFERRED]
- [[TestOrdersAdapter]] - `uses` [INFERRED]
- [[TestOrdersSecurityIdUsage]] - `uses` [INFERRED]
- [[TestPortfolioAdapter]] - `uses` [INFERRED]
- [[TestProfileValidation]] - `uses` [INFERRED]
- [[TestRateLimits]] - `uses` [INFERRED]
- [[TestWebSocketSecurityIdResolution]] - `uses` [INFERRED]
- [[connection.py]] - `imports` [EXTRACTED]
- [[orders.py]] - `contains` [EXTRACTED]
- [[orders_adapter()]] - `calls` [EXTRACTED]
- [[test_adapters.py]] - `imports` [EXTRACTED]
- [[test_critical_fixes.py]] - `imports` [EXTRACTED]
- [[test_security_id_consistency.py]] - `imports` [EXTRACTED]

#graphify/code #graphify/INFERRED #community/Tests_Unit/Brokers
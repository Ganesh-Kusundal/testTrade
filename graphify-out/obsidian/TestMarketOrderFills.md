---
source_file: "tests/unit/brokers/dhan/test_critical_fixes.py"
type: "code"
community: "Tests: Unit/Brokers"
location: "L212"
tags:
  - graphify/code
  - graphify/INFERRED
  - community/Tests_Unit/Brokers
---

# TestMarketOrderFills

## Connections
- [[.test_limit_order_uses_price_fallback()]] - `method` [EXTRACTED]
- [[.test_market_order_with_fill_uses_traded_price()]] - `method` [EXTRACTED]
- [[.test_market_order_with_zero_fill_price_logs_warning()]] - `method` [EXTRACTED]
- [[BrokerError]] - `uses` [INFERRED]
- [[DhanConnection]] - `uses` [INFERRED]
- [[DhanMapper]] - `uses` [INFERRED]
- [[Exchange_4]] - `uses` [INFERRED]
- [[Order]] - `uses` [INFERRED]
- [[OrderSide_1]] - `uses` [INFERRED]
- [[OrderState]] - `uses` [INFERRED]
- [[OrderType]] - `uses` [INFERRED]
- [[OrdersAdapter]] - `uses` [INFERRED]
- [[Verify MARKET orders handle fill price correctly.]] - `rationale_for` [EXTRACTED]
- [[test_critical_fixes.py]] - `contains` [EXTRACTED]

#graphify/code #graphify/INFERRED #community/Tests_Unit/Brokers
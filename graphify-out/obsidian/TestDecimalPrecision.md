---
source_file: "tests/unit/brokers/dhan/test_critical_fixes.py"
type: "code"
community: "Tests: Unit/Brokers"
location: "L68"
tags:
  - graphify/code
  - graphify/INFERRED
  - community/Tests_Unit/Brokers
---

# TestDecimalPrecision

## Connections
- [[.test_modify_order_uses_string_prices()]] - `method` [EXTRACTED]
- [[.test_orders_api_receives_string_not_float()]] - `method` [EXTRACTED]
- [[BrokerError]] - `uses` [INFERRED]
- [[DhanConnection]] - `uses` [INFERRED]
- [[DhanMapper]] - `uses` [INFERRED]
- [[Exchange_4]] - `uses` [INFERRED]
- [[Order]] - `uses` [INFERRED]
- [[OrderSide_1]] - `uses` [INFERRED]
- [[OrderState]] - `uses` [INFERRED]
- [[OrderType]] - `uses` [INFERRED]
- [[OrdersAdapter]] - `uses` [INFERRED]
- [[Verify order payloads use strings, not floats, for prices.]] - `rationale_for` [EXTRACTED]
- [[test_critical_fixes.py]] - `contains` [EXTRACTED]

#graphify/code #graphify/INFERRED #community/Tests_Unit/Brokers
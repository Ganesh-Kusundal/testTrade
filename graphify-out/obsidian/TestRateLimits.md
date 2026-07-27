---
source_file: "tests/unit/brokers/dhan/test_critical_fixes.py"
type: "code"
community: "Tests: Unit/Brokers"
location: "L320"
tags:
  - graphify/code
  - graphify/INFERRED
  - community/Tests_Unit/Brokers
---

# TestRateLimits

## Connections
- [[.test_charts_rate_limit_is_5_per_second()]] - `method` [EXTRACTED]
- [[.test_ltp_api_rate_limit_is_5_per_second()]] - `method` [EXTRACTED]
- [[.test_ohlc_api_rate_limit_is_5_per_second()]] - `method` [EXTRACTED]
- [[.test_option_chain_rate_limit_is_1_per_second()]] - `method` [EXTRACTED]
- [[.test_order_api_rate_limit_is_10_per_second()]] - `method` [EXTRACTED]
- [[.test_quote_api_rate_limit_is_1_per_second()]] - `method` [EXTRACTED]
- [[BrokerError]] - `uses` [INFERRED]
- [[DhanConnection]] - `uses` [INFERRED]
- [[DhanMapper]] - `uses` [INFERRED]
- [[Exchange_4]] - `uses` [INFERRED]
- [[Order]] - `uses` [INFERRED]
- [[OrderSide_1]] - `uses` [INFERRED]
- [[OrderState]] - `uses` [INFERRED]
- [[OrderType]] - `uses` [INFERRED]
- [[OrdersAdapter]] - `uses` [INFERRED]
- [[Verify rate limits match Dhan API specifications.]] - `rationale_for` [EXTRACTED]
- [[test_critical_fixes.py]] - `contains` [EXTRACTED]

#graphify/code #graphify/INFERRED #community/Tests_Unit/Brokers
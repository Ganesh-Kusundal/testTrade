---
source_file: "tests/unit/brokers/dhan/test_critical_fixes.py"
type: "rationale"
community: "Tests: Unit/Brokers"
location: "L252"
tags:
  - graphify/rationale
  - graphify/EXTRACTED
  - community/Tests_Unit/Brokers
---

# LIMIT orders should use order.price as fallback if no fill yet.

## Connections
- [[.test_limit_order_uses_price_fallback()]] - `rationale_for` [EXTRACTED]

#graphify/rationale #graphify/EXTRACTED #community/Tests_Unit/Brokers
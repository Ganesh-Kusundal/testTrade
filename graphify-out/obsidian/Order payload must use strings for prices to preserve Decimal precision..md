---
source_file: "tests/unit/brokers/dhan/test_critical_fixes.py"
type: "rationale"
community: "Tests: Unit/Brokers"
location: "L72"
tags:
  - graphify/rationale
  - graphify/EXTRACTED
  - community/Tests_Unit/Brokers
---

# Order payload must use strings for prices to preserve Decimal precision.

## Connections
- [[.test_orders_api_receives_string_not_float()]] - `rationale_for` [EXTRACTED]

#graphify/rationale #graphify/EXTRACTED #community/Tests_Unit/Brokers
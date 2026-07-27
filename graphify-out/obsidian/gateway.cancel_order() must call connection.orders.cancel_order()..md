---
source_file: "tests/unit/brokers/dhan/test_gateway_connection.py"
type: "rationale"
community: "Tests: Unit/Brokers"
location: "L799"
tags:
  - graphify/rationale
  - graphify/EXTRACTED
  - community/Tests_Unit/Brokers
---

# gateway.cancel_order() must call connection.orders.cancel_order().

## Connections
- [[.test_should_delegate_cancel_order_to_orders_adapter()]] - `rationale_for` [EXTRACTED]

#graphify/rationale #graphify/EXTRACTED #community/Tests_Unit/Brokers
---
source_file: "tests/unit/brokers/dhan/test_gateway_connection.py"
type: "rationale"
community: "Tests: Unit/Brokers"
location: "L751"
tags:
  - graphify/rationale
  - graphify/EXTRACTED
  - community/Tests_Unit/Brokers
---

# gateway.get_quote() must call connection.market_data.get_quote().

## Connections
- [[.test_should_delegate_get_quote_to_market_data_adapter()]] - `rationale_for` [EXTRACTED]

#graphify/rationale #graphify/EXTRACTED #community/Tests_Unit/Brokers
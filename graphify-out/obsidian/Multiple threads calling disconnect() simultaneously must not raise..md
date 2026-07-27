---
source_file: "tests/unit/brokers/dhan/test_gateway_connection.py"
type: "rationale"
community: "Tests: Unit/Brokers"
location: "L444"
tags:
  - graphify/rationale
  - graphify/EXTRACTED
  - community/Tests_Unit/Brokers
---

# Multiple threads calling disconnect() simultaneously must not raise.

## Connections
- [[.test_should_handle_concurrent_disconnect_calls_safely()]] - `rationale_for` [EXTRACTED]

#graphify/rationale #graphify/EXTRACTED #community/Tests_Unit/Brokers
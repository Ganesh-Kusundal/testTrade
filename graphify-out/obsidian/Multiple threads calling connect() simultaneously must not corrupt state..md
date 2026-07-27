---
source_file: "tests/unit/brokers/dhan/test_gateway_connection.py"
type: "rationale"
community: "Tests: Unit/Brokers"
location: "L416"
tags:
  - graphify/rationale
  - graphify/EXTRACTED
  - community/Tests_Unit/Brokers
---

# Multiple threads calling connect() simultaneously must not corrupt state.

## Connections
- [[.test_should_handle_concurrent_connect_calls_safely()]] - `rationale_for` [EXTRACTED]

#graphify/rationale #graphify/EXTRACTED #community/Tests_Unit/Brokers
---
source_file: "tests/unit/brokers/dhan/test_gateway_connection.py"
type: "rationale"
community: "Tests: Unit/Brokers"
location: "L280"
tags:
  - graphify/rationale
  - graphify/EXTRACTED
  - community/Tests_Unit/Brokers
---

# Second connect() call must be a no-op, not reinitialise.

## Connections
- [[.test_should_be_idempotent_when_connect_called_twice()]] - `rationale_for` [EXTRACTED]

#graphify/rationale #graphify/EXTRACTED #community/Tests_Unit/Brokers
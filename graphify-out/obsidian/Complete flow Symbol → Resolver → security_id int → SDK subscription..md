---
source_file: "tests/unit/brokers/dhan/test_security_id_consistency.py"
type: "rationale"
community: "Tests: Unit/Brokers"
location: "L242"
tags:
  - graphify/rationale
  - graphify/EXTRACTED
  - community/Tests_Unit/Brokers
---

# Complete flow: Symbol → Resolver → security_id int → SDK subscription.

## Connections
- [[.test_full_subscription_flow_reliance()]] - `rationale_for` [EXTRACTED]

#graphify/rationale #graphify/EXTRACTED #community/Tests_Unit/Brokers
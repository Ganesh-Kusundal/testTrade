---
source_file: "tests/unit/brokers/dhan/test_security_id_consistency.py"
type: "code"
community: "Tests: Unit/Brokers"
location: "L163"
tags:
  - graphify/code
  - graphify/INFERRED
  - community/Tests_Unit/Brokers
---

# TestOrdersSecurityIdUsage

## Connections
- [[.test_orders_code_uses_security_id_field()]] - `method` [EXTRACTED]
- [[DhanWebSocketClient]] - `uses` [INFERRED]
- [[Exchange_4]] - `uses` [INFERRED]
- [[HistoricalDataAdapter]] - `uses` [INFERRED]
- [[Instrument]] - `uses` [INFERRED]
- [[OptionsScanner]] - `uses` [INFERRED]
- [[OrdersAdapter]] - `uses` [INFERRED]
- [[Segment_2]] - `uses` [INFERRED]
- [[Verify orders code uses inst.security_id, not inst.symbol.]] - `rationale_for` [EXTRACTED]
- [[test_security_id_consistency.py]] - `contains` [EXTRACTED]

#graphify/code #graphify/INFERRED #community/Tests_Unit/Brokers
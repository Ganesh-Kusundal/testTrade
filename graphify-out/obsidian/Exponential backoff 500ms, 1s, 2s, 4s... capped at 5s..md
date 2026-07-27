---
source_file: "scalpr/brokers/dhan/http_client.py"
type: "rationale"
community: "Dhan Broker Integration"
location: "L291"
tags:
  - graphify/rationale
  - graphify/EXTRACTED
  - community/Dhan_Broker_Integration
---

# Exponential backoff: 500ms, 1s, 2s, 4s... capped at 5s.

## Connections
- [[._backoff_delay()]] - `rationale_for` [EXTRACTED]

#graphify/rationale #graphify/EXTRACTED #community/Dhan_Broker_Integration
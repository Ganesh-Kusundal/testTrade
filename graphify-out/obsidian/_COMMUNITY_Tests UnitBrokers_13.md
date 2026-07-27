---
type: community
cohesion: 1.00
members: 2
---

# Tests: Unit/Brokers

**Cohesion:** 1.00 - tightly connected
**Members:** 2 nodes

## Members
- [[Provide a MagicMock DhanHttpClient.]] - rationale - tests/unit/brokers/dhan/test_adapters.py
- [[mock_http_client()]] - code - tests/unit/brokers/dhan/test_adapters.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Tests_Unit/Brokers
SORT file.name ASC
```

## Connections to other communities
- 1 edge to [[_COMMUNITY_Dhan Broker Integration_2]]

## Top bridge nodes
- [[mock_http_client()]] - degree 2, connects to 1 community
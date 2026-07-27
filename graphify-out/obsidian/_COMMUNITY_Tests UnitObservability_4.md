---
type: community
cohesion: 1.00
members: 2
---

# Tests: Unit/Observability

**Cohesion:** 1.00 - tightly connected
**Members:** 2 nodes

## Members
- [[.test_checkpoint_restore_invalid_position()]] - code - tests/unit/observability/test_event_store.py
- [[Test that invalid checkpoint raises error.]] - rationale - tests/unit/observability/test_event_store.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Tests_Unit/Observability
SORT file.name ASC
```

## Connections to other communities
- 1 edge to [[_COMMUNITY_Domain Events]]

## Top bridge nodes
- [[.test_checkpoint_restore_invalid_position()]] - degree 2, connects to 1 community
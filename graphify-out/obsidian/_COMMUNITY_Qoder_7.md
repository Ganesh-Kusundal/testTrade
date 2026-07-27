---
type: community
cohesion: 0.25
members: 8
---

# Qoder

**Cohesion:** 0.25 - loosely connected
**Members:** 8 nodes

## Members
- [[Fetch and cache the Dhan security master.      The SDK downloads the CSV locally]] - rationale - .qoder/skills/dhanhq/scripts/dhan_helpers.py
- [[Resolve a cash-market symbol to a security ID using the security master.]] - rationale - .qoder/skills/dhanhq/scripts/dhan_helpers.py
- [[Resolve a derivative contract from the security master.]] - rationale - .qoder/skills/dhanhq/scripts/dhan_helpers.py
- [[Return lot size from the security master when possible.]] - rationale - .qoder/skills/dhanhq/scripts/dhan_helpers.py
- [[get_lot_size()]] - code - .qoder/skills/dhanhq/scripts/dhan_helpers.py
- [[get_security_master()]] - code - .qoder/skills/dhanhq/scripts/dhan_helpers.py
- [[resolve_derivative()]] - code - .qoder/skills/dhanhq/scripts/dhan_helpers.py
- [[resolve_symbol()]] - code - .qoder/skills/dhanhq/scripts/dhan_helpers.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Qoder
SORT file.name ASC
```

## Connections to other communities
- 4 edges to [[_COMMUNITY_Qoder_2]]
- 2 edges to [[_COMMUNITY_Qoder_5]]
- 1 edge to [[_COMMUNITY_Qoder_9]]

## Top bridge nodes
- [[get_security_master()]] - degree 6, connects to 2 communities
- [[resolve_derivative()]] - degree 4, connects to 2 communities
- [[resolve_symbol()]] - degree 4, connects to 2 communities
- [[get_lot_size()]] - degree 3, connects to 1 community
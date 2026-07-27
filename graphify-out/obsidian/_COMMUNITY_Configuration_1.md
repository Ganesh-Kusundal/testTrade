---
type: community
cohesion: 0.13
members: 16
---

# Configuration

**Cohesion:** 0.13 - loosely connected
**Members:** 16 nodes

## Members
- [[Broker-agnostic index metadata.]] - rationale - config/indices.py
- [[Check if symbol is a known index (case-insensitive).]] - rationale - config/indices.py
- [[Hardcoded index symbol mapping — single source of truth for all indices.  Both D]] - rationale - config/indices.py
- [[Return class`_IndexEntry` for symbol, or ``None`` if not an index.]] - rationale - config/indices.py
- [[Return Dhan exchange name (``INDEX``) if symbol is an index, else ``None``.]] - rationale - config/indices.py
- [[Return Upstox segment (e.g. ``NSE_INDEX``) if symbol is an index, else ``Non]] - rationale - config/indices.py
- [[Return a human-readable list of all registered indices.]] - rationale - config/indices.py
- [[Return the Upstox instrument_key for symbol (e.g. ``NSE_INDEXNifty 50``).]] - rationale - config/indices.py
- [[_IndexEntry]] - code - config/indices.py
- [[dhan_index_exchange()]] - code - config/indices.py
- [[get_index_entry()]] - code - config/indices.py
- [[index_upstox_key()]] - code - config/indices.py
- [[indices.py]] - code - config/indices.py
- [[is_index()]] - code - config/indices.py
- [[list_indices()]] - code - config/indices.py
- [[upstox_index_segment()]] - code - config/indices.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Configuration
SORT file.name ASC
```

---
type: community
cohesion: 0.13
members: 23
---

# Dhan Broker Integration

**Cohesion:** 0.13 - loosely connected
**Members:** 23 nodes

## Members
- [[._cleanup_old_cache()]] - code - scalpr/brokers/dhan/loader.py
- [[._compact_to_rows()]] - code - scalpr/brokers/dhan/loader.py
- [[.load_cached()]] - code - scalpr/brokers/dhan/loader.py
- [[.load_from_file()]] - code - scalpr/brokers/dhan/loader.py
- [[.load_from_url()]] - code - scalpr/brokers/dhan/loader.py
- [[Convert DataFrame to list of row dicts with standardized fields.]] - rationale - scalpr/brokers/dhan/loader.py
- [[Downloads and parses Dhan instrument master with daily caching.          Feature]] - rationale - scalpr/brokers/dhan/loader.py
- [[Instrument master CSV loader with daily caching.  Downloads Dhan instrument mast]] - rationale - scalpr/brokers/dhan/loader.py
- [[InstrumentLoader]] - code - scalpr/brokers/dhan/loader.py
- [[Load instrument master rows with daily caching.                  Args]] - rationale - scalpr/brokers/dhan/loader.py
- [[Load instruments from a URL.]] - rationale - scalpr/brokers/dhan/loader.py
- [[Load instruments from a local CSV file.]] - rationale - scalpr/brokers/dhan/loader.py
- [[Path]] - code
- [[Purge cached files older than N days.]] - rationale - scalpr/brokers/dhan/loader.py
- [[Safely get float value from row.]] - rationale - scalpr/brokers/dhan/loader.py
- [[Safely get optional float value from row.]] - rationale - scalpr/brokers/dhan/loader.py
- [[Safely get optional string value from row.]] - rationale - scalpr/brokers/dhan/loader.py
- [[Safely get string value from row.]] - rationale - scalpr/brokers/dhan/loader.py
- [[_safe_float()]] - code - scalpr/brokers/dhan/loader.py
- [[_safe_opt_float()]] - code - scalpr/brokers/dhan/loader.py
- [[_safe_opt_str()]] - code - scalpr/brokers/dhan/loader.py
- [[_safe_str()]] - code - scalpr/brokers/dhan/loader.py
- [[loader.py]] - code - scalpr/brokers/dhan/loader.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Dhan_Broker_Integration
SORT file.name ASC
```

## Connections to other communities
- 2 edges to [[_COMMUNITY_Tests UnitBrokers]]
- 2 edges to [[_COMMUNITY_Tests UnitTesting]]
- 1 edge to [[_COMMUNITY_Configuration_2]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers_3]]
- 1 edge to [[_COMMUNITY_Dhan Broker Integration_10]]
- 1 edge to [[_COMMUNITY_Logging System]]
- 1 edge to [[_COMMUNITY_Dhan Broker Integration_2]]

## Top bridge nodes
- [[loader.py]] - degree 11, connects to 5 communities
- [[InstrumentLoader]] - degree 10, connects to 3 communities
- [[.load_cached()]] - degree 6, connects to 1 community
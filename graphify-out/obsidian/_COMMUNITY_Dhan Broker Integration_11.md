---
type: community
cohesion: 0.18
members: 12
---

# Dhan Broker Integration

**Cohesion:** 0.18 - loosely connected
**Members:** 12 nodes

## Members
- [[._row_to_instrument()]] - code - scalpr/brokers/dhan/resolver.py
- [[.load_from_rows()]] - code - scalpr/brokers/dhan/resolver.py
- [[Convert CSV row to Instrument.]] - rationale - scalpr/brokers/dhan/resolver.py
- [[Decimal_6]] - code
- [[Generate alternate symbol formats for flexible lookup.]] - rationale - scalpr/brokers/dhan/resolver.py
- [[Load instruments from CSV rows with atomic swap.                  Args]] - rationale - scalpr/brokers/dhan/resolver.py
- [[Safely convert value to Decimal.]] - rationale - scalpr/brokers/dhan/resolver.py
- [[Safely convert value to int.]] - rationale - scalpr/brokers/dhan/resolver.py
- [[Segment_1]] - code
- [[_generate_alternate_keys()]] - code - scalpr/brokers/dhan/resolver.py
- [[_safe_decimal()]] - code - scalpr/brokers/dhan/resolver.py
- [[_safe_int()]] - code - scalpr/brokers/dhan/resolver.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Dhan_Broker_Integration
SORT file.name ASC
```

## Connections to other communities
- 5 edges to [[_COMMUNITY_Dhan Broker Integration_2]]
- 3 edges to [[_COMMUNITY_Dhan Broker Integration_6]]
- 1 edge to [[_COMMUNITY_Scanner - Options]]

## Top bridge nodes
- [[._row_to_instrument()]] - degree 7, connects to 2 communities
- [[_generate_alternate_keys()]] - degree 6, connects to 1 community
- [[_safe_decimal()]] - degree 4, connects to 1 community
- [[.load_from_rows()]] - degree 4, connects to 1 community
- [[Decimal_6]] - degree 3, connects to 1 community
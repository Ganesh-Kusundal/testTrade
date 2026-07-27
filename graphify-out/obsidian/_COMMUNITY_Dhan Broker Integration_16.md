---
type: community
cohesion: 0.50
members: 4
---

# Dhan Broker Integration

**Cohesion:** 0.50 - moderately connected
**Members:** 4 nodes

## Members
- [[._estimate_lookback_days()]] - code - scalpr/brokers/dhan/historical.py
- [[._timeframe_to_minutes()]] - code - scalpr/brokers/dhan/historical.py
- [[Convert timeframe string to minutes, or None for daily+.]] - rationale - scalpr/brokers/dhan/historical.py
- [[Estimate how many calendar days are needed to get ``count`` candles.          Ac]] - rationale - scalpr/brokers/dhan/historical.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Dhan_Broker_Integration
SORT file.name ASC
```

## Connections to other communities
- 3 edges to [[_COMMUNITY_Dhan Broker Integration_5]]

## Top bridge nodes
- [[._estimate_lookback_days()]] - degree 4, connects to 1 community
- [[._timeframe_to_minutes()]] - degree 3, connects to 1 community
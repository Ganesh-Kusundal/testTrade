---
type: community
cohesion: 0.40
members: 5
---

# Market - Data

**Cohesion:** 0.40 - moderately connected
**Members:** 5 nodes

## Members
- [[.__init__()_20]] - code - scalpr/market_data/historical.py
- [[.load_history()]] - code - scalpr/market_data/historical.py
- [[Fetch historical bars from DhanHQ. (Mocked implementation for local run).]] - rationale - scalpr/market_data/historical.py
- [[HistoricalLoader]] - code - scalpr/market_data/historical.py
- [[Loads historical OHLCV candles from the broker.]] - rationale - scalpr/market_data/historical.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Market_-_Data
SORT file.name ASC
```

## Connections to other communities
- 2 edges to [[_COMMUNITY_Tests UnitBrokers]]
- 2 edges to [[_COMMUNITY_Backtester]]
- 1 edge to [[_COMMUNITY_Market - Data]]
- 1 edge to [[_COMMUNITY_Market - Data_1]]

## Top bridge nodes
- [[HistoricalLoader]] - degree 7, connects to 4 communities
- [[.load_history()]] - degree 3, connects to 1 community
- [[.__init__()_20]] - degree 2, connects to 1 community
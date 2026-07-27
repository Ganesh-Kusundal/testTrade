---
type: community
cohesion: 0.33
members: 6
---

# Brokers - Broker

**Cohesion:** 0.33 - loosely connected
**Members:** 6 nodes

## Members
- [[.get_ohlcv()]] - code - scalpr/brokers/broker_port.py
- [[.get_quote()]] - code - scalpr/brokers/broker_port.py
- [[Any_2]] - code
- [[Fetch historical OHLCV candlestick data.]] - rationale - scalpr/brokers/broker_port.py
- [[Get full market quote for a symbol.]] - rationale - scalpr/brokers/broker_port.py
- [[date]] - code

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Brokers_-_Broker
SORT file.name ASC
```

## Connections to other communities
- 2 edges to [[_COMMUNITY_Tests UnitBrokers]]

## Top bridge nodes
- [[.get_ohlcv()]] - degree 4, connects to 1 community
- [[.get_quote()]] - degree 3, connects to 1 community
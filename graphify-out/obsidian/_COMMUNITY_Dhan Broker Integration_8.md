---
type: community
cohesion: 0.10
members: 22
---

# Dhan Broker Integration

**Cohesion:** 0.10 - loosely connected
**Members:** 22 nodes

## Members
- [[._calculate_unrealised_pnl()]] - code - scalpr/brokers/dhan/portfolio.py
- [[._extract_list()]] - code - scalpr/brokers/dhan/portfolio.py
- [[._is_open()]] - code - scalpr/brokers/dhan/portfolio.py
- [[._map_fund_limits()]] - code - scalpr/brokers/dhan/portfolio.py
- [[._map_holding()]] - code - scalpr/brokers/dhan/portfolio.py
- [[._normalise_exchange()]] - code - scalpr/brokers/dhan/portfolio.py
- [[.get_fund_limits()_2]] - code - scalpr/brokers/dhan/portfolio.py
- [[.get_holdings()_2]] - code - scalpr/brokers/dhan/portfolio.py
- [[.get_position()]] - code - scalpr/brokers/dhan/portfolio.py
- [[.get_positions()_2]] - code - scalpr/brokers/dhan/portfolio.py
- [[Calculate unrealised P&L using Decimal arithmetic.          Long  qty  (ltp -]] - rationale - scalpr/brokers/dhan/portfolio.py
- [[Check if a position record represents an open (non-flat) position.]] - rationale - scalpr/brokers/dhan/portfolio.py
- [[Convert Dhan fund limit response to a clean dict.          Dhan API returns fund]] - rationale - scalpr/brokers/dhan/portfolio.py
- [[Convert a raw Dhan holding dict to a SCALPR Position.          Holdings are long]] - rationale - scalpr/brokers/dhan/portfolio.py
- [[Decimal_5]] - code
- [[Exchange_1]] - code
- [[Fetch active (intradayF&O) positions with P&L.          Returns             Li]] - rationale - scalpr/brokers/dhan/portfolio.py
- [[Fetch available margin, used margin, and total balance.          Returns]] - rationale - scalpr/brokers/dhan/portfolio.py
- [[Fetch long-term holdings (delivery positions).          Returns             Lis]] - rationale - scalpr/brokers/dhan/portfolio.py
- [[Look up a single position by symbol and exchange.          Args             sym]] - rationale - scalpr/brokers/dhan/portfolio.py
- [[Normalise exchange string to Exchange enum.          Uses segment mapping for Dh]] - rationale - scalpr/brokers/dhan/portfolio.py
- [[Safely extract a list of records from API response.          Dhan API may return]] - rationale - scalpr/brokers/dhan/portfolio.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Dhan_Broker_Integration
SORT file.name ASC
```

## Connections to other communities
- 15 edges to [[_COMMUNITY_Dhan Broker Integration_2]]
- 4 edges to [[_COMMUNITY_Oms - Order]]

## Top bridge nodes
- [[.get_positions()_2]] - degree 7, connects to 2 communities
- [[._map_holding()]] - degree 7, connects to 2 communities
- [[.get_holdings()_2]] - degree 5, connects to 2 communities
- [[.get_position()]] - degree 5, connects to 2 communities
- [[._normalise_exchange()]] - degree 6, connects to 1 community
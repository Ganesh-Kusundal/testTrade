---
type: community
cohesion: 0.15
members: 20
---

# Dhan Broker Integration

**Cohesion:** 0.15 - loosely connected
**Members:** 20 nodes

## Members
- [[.__init__()_7]] - code - scalpr/brokers/dhan/market_data.py
- [[._resolve_segment()_1]] - code - scalpr/brokers/dhan/market_data.py
- [[.get_batch_ltp()]] - code - scalpr/brokers/dhan/market_data.py
- [[.get_batch_quote()]] - code - scalpr/brokers/dhan/market_data.py
- [[.get_depth()]] - code - scalpr/brokers/dhan/market_data.py
- [[.get_ltp()_2]] - code - scalpr/brokers/dhan/market_data.py
- [[.get_quote()_2]] - code - scalpr/brokers/dhan/market_data.py
- [[.market_data()]] - code - scalpr/brokers/dhan/connection.py
- [[Access market data adapter.          Raises             BrokerError If not con]] - rationale - scalpr/brokers/dhan/connection.py
- [[Adapter for fetching market data from Dhan API.          Provides methods for]] - rationale - scalpr/brokers/dhan/market_data.py
- [[Any_8]] - code
- [[Decimal_3]] - code
- [[Get LTP for multiple symbols in one call.                  Args             sym]] - rationale - scalpr/brokers/dhan/market_data.py
- [[Get Last Traded Price for a symbol.                  Args             symbol T]] - rationale - scalpr/brokers/dhan/market_data.py
- [[Get full quote for a symbol.                  Args             symbol Trading]] - rationale - scalpr/brokers/dhan/market_data.py
- [[Get market depth for a symbol.                  Args             symbol Tradin]] - rationale - scalpr/brokers/dhan/market_data.py
- [[Get quotes for multiple symbols in one call.                  Args]] - rationale - scalpr/brokers/dhan/market_data.py
- [[MarketDataAdapter]] - code - scalpr/brokers/dhan/market_data.py
- [[Resolve symbol to numeric security_id and segment.]] - rationale - scalpr/brokers/dhan/market_data.py
- [[market_adapter()]] - code - tests/unit/brokers/dhan/test_adapters.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Dhan_Broker_Integration
SORT file.name ASC
```

## Connections to other communities
- 4 edges to [[_COMMUNITY_Tests UnitTesting]]
- 4 edges to [[_COMMUNITY_Dhan Broker Integration_2]]
- 2 edges to [[_COMMUNITY_Tests UnitBrokers_3]]
- 2 edges to [[_COMMUNITY_Dhan Broker Integration_6]]
- 1 edge to [[_COMMUNITY_Dhan Broker Integration_10]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers_4]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers_8]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers_6]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers_7]]

## Top bridge nodes
- [[MarketDataAdapter]] - degree 22, connects to 10 communities
- [[.market_data()]] - degree 4, connects to 2 communities
- [[.__init__()_7]] - degree 3, connects to 2 communities
- [[Decimal_3]] - degree 6, connects to 1 community
- [[market_adapter()]] - degree 2, connects to 1 community
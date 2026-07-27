---
type: community
cohesion: 0.10
members: 31
---

# Dhan Broker Integration

**Cohesion:** 0.10 - loosely connected
**Members:** 31 nodes

## Members
- [[._derive_side_and_state()]] - code - scalpr/brokers/dhan/portfolio.py
- [[._map_position()]] - code - scalpr/brokers/dhan/portfolio.py
- [[._map_position_manual()]] - code - scalpr/brokers/dhan/portfolio.py
- [[.portfolio()]] - code - scalpr/brokers/dhan/connection.py
- [[.restore_positions()]] - code - scalpr/oms/persistence.py
- [[Access portfolio adapter.          Raises             BrokerError If not conne]] - rationale - scalpr/brokers/dhan/connection.py
- [[Adapter for Dhan portfoliopositions API to SCALPR domain types.      Responsibi]] - rationale - scalpr/brokers/dhan/portfolio.py
- [[Comprehensive unit tests for Dhan broker adapters.  Tests cover MarketDataAdapte]] - rationale - tests/unit/brokers/dhan/test_adapters.py
- [[Convert Dhan wire segment to Exchange enum.          Args         segment Dhan]] - rationale - scalpr/brokers/dhan/segments.py
- [[Convert a raw Dhan position dict to a SCALPR Position.          Delegates to Dha]] - rationale - scalpr/brokers/dhan/portfolio.py
- [[Derive PositionSide and PositionState from signed quantity.]] - rationale - scalpr/brokers/dhan/portfolio.py
- [[Dhan segment adapter — exchange and segment mappings.  Provides mappings between]] - rationale - scalpr/brokers/dhan/segments.py
- [[Enum]] - code
- [[Manual position mapping as fallback.          Dr. Venkat A system that is fast]] - rationale - scalpr/brokers/dhan/portfolio.py
- [[Market data adapter — LTP, Quote, Depth, OHLC.  Provides methods to fetch market]] - rationale - scalpr/brokers/dhan/market_data.py
- [[O(1) symbol → Instrument resolver backed by dictionaries.  Provides fast instrum]] - rationale - scalpr/brokers/dhan/resolver.py
- [[OptionType]] - code - scalpr/domain/instrument.py
- [[OrderSide]] - code - scalpr/brokers/contracts.py
- [[Portfolio adapter — positions, holdings, and fund limits.  Provides a clean boun]] - rationale - scalpr/brokers/dhan/portfolio.py
- [[PortfolioAdapter]] - code - scalpr/brokers/dhan/portfolio.py
- [[PositionState]] - code - scalpr/domain/position.py
- [[Restore all position records from database.]] - rationale - scalpr/oms/persistence.py
- [[instrument.py]] - code - scalpr/domain/instrument.py
- [[market_data.py]] - code - scalpr/brokers/dhan/market_data.py
- [[orders_adapter()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[portfolio.py]] - code - scalpr/brokers/dhan/portfolio.py
- [[portfolio_adapter()]] - code - tests/unit/brokers/dhan/test_adapters.py
- [[resolver.py]] - code - scalpr/brokers/dhan/resolver.py
- [[segment_to_exchange()]] - code - scalpr/brokers/dhan/segments.py
- [[segments.py]] - code - scalpr/brokers/dhan/segments.py
- [[test_adapters.py]] - code - tests/unit/brokers/dhan/test_adapters.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Dhan_Broker_Integration
SORT file.name ASC
```

## Connections to other communities
- 34 edges to [[_COMMUNITY_Tests UnitBrokers]]
- 27 edges to [[_COMMUNITY_Tests UnitTesting]]
- 26 edges to [[_COMMUNITY_Oms - Order]]
- 15 edges to [[_COMMUNITY_Dhan Broker Integration_8]]
- 13 edges to [[_COMMUNITY_Tests UnitBrokers_1]]
- 8 edges to [[_COMMUNITY_Scanner - Options]]
- 7 edges to [[_COMMUNITY_Domain Events]]
- 6 edges to [[_COMMUNITY_Dhan Broker Integration_6]]
- 5 edges to [[_COMMUNITY_Tests UnitBrokers_8]]
- 5 edges to [[_COMMUNITY_Dhan Broker Integration_11]]
- 4 edges to [[_COMMUNITY_Dhan Broker Integration_9]]
- 4 edges to [[_COMMUNITY_Tests UnitBrokers_6]]
- 4 edges to [[_COMMUNITY_Signals - Gate]]
- 3 edges to [[_COMMUNITY_Logging System]]
- 3 edges to [[_COMMUNITY_Tests UnitBrokers_4]]
- 3 edges to [[_COMMUNITY_Tests UnitBrokers_7]]
- 2 edges to [[_COMMUNITY_Broker Contracts]]
- 2 edges to [[_COMMUNITY_Tests UnitBrokers_3]]
- 2 edges to [[_COMMUNITY_Dhan Broker Integration_5]]
- 2 edges to [[_COMMUNITY_Dhan Broker Integration_18]]
- 1 edge to [[_COMMUNITY_Market - Data]]
- 1 edge to [[_COMMUNITY_Dhan Broker Integration_10]]
- 1 edge to [[_COMMUNITY_Dhan Broker Integration_7]]
- 1 edge to [[_COMMUNITY_Dhan Broker Integration_25]]
- 1 edge to [[_COMMUNITY_Dhan Broker Integration_3]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers_10]]
- 1 edge to [[_COMMUNITY_Simulation - Replay]]
- 1 edge to [[_COMMUNITY_Oms - Paper]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers_13]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers_14]]

## Top bridge nodes
- [[test_adapters.py]] - degree 38, connects to 13 communities
- [[PortfolioAdapter]] - degree 33, connects to 12 communities
- [[PositionState]] - degree 35, connects to 11 communities
- [[instrument.py]] - degree 30, connects to 9 communities
- [[resolver.py]] - degree 20, connects to 8 communities
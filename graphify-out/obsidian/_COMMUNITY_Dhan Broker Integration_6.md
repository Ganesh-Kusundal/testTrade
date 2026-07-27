---
type: community
cohesion: 0.10
members: 26
---

# Dhan Broker Integration

**Cohesion:** 0.10 - loosely connected
**Members:** 26 nodes

## Members
- [[.__init__()_3]] - code - scalpr/brokers/dhan/historical.py
- [[.__init__()_8]] - code - scalpr/brokers/dhan/orders.py
- [[.__init__()_9]] - code - scalpr/brokers/dhan/portfolio.py
- [[.__init__()_10]] - code - scalpr/brokers/dhan/resolver.py
- [[._find()]] - code - scalpr/brokers/dhan/resolver.py
- [[._normalise_exchange()_1]] - code - scalpr/brokers/dhan/resolver.py
- [[.all_instruments()]] - code - scalpr/brokers/dhan/resolver.py
- [[.get_by_security_id()]] - code - scalpr/brokers/dhan/resolver.py
- [[.get_by_symbol()]] - code - scalpr/brokers/dhan/resolver.py
- [[.get_lot_size()]] - code - scalpr/brokers/dhan/resolver.py
- [[.resolve()]] - code - scalpr/brokers/dhan/resolver.py
- [[.resolver()]] - code - scalpr/brokers/dhan/connection.py
- [[.stats()]] - code - scalpr/brokers/dhan/resolver.py
- [[Access symbol resolver.          Raises             BrokerError If not connect]] - rationale - scalpr/brokers/dhan/connection.py
- [[Exchange_2]] - code
- [[Find instrument with progressive lookup.]] - rationale - scalpr/brokers/dhan/resolver.py
- [[Get all loaded instruments.]] - rationale - scalpr/brokers/dhan/resolver.py
- [[Get instrument by security_id, returns None if not found.]] - rationale - scalpr/brokers/dhan/resolver.py
- [[Get instrument by symbol, returns None if not found.]] - rationale - scalpr/brokers/dhan/resolver.py
- [[Get lot size for an instrument.]] - rationale - scalpr/brokers/dhan/resolver.py
- [[Get resolver statistics.]] - rationale - scalpr/brokers/dhan/resolver.py
- [[Initialise OrdersAdapter.          Args             client Configured DhanHttp]] - rationale - scalpr/brokers/dhan/orders.py
- [[Normalize exchange string to Exchange enum.]] - rationale - scalpr/brokers/dhan/resolver.py
- [[Resolve symbol to Instrument.                  Args             symbol Trading]] - rationale - scalpr/brokers/dhan/resolver.py
- [[SymbolResolver]] - code - scalpr/brokers/dhan/resolver.py
- [[Thread-safe O(1) symbol → Instrument resolver.          Provides fast instrument]] - rationale - scalpr/brokers/dhan/resolver.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Dhan_Broker_Integration
SORT file.name ASC
```

## Connections to other communities
- 7 edges to [[_COMMUNITY_Scanner - Options]]
- 6 edges to [[_COMMUNITY_Tests UnitTesting]]
- 6 edges to [[_COMMUNITY_Dhan Broker Integration_2]]
- 3 edges to [[_COMMUNITY_Tests UnitBrokers]]
- 3 edges to [[_COMMUNITY_Dhan Broker Integration_11]]
- 2 edges to [[_COMMUNITY_Tests UnitBrokers_3]]
- 2 edges to [[_COMMUNITY_Tests UnitBrokers_8]]
- 2 edges to [[_COMMUNITY_Dhan Broker Integration_5]]
- 2 edges to [[_COMMUNITY_Dhan Broker Integration_9]]
- 1 edge to [[_COMMUNITY_Dhan Broker Integration_10]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers_1]]

## Top bridge nodes
- [[SymbolResolver]] - degree 34, connects to 11 communities
- [[.resolve()]] - degree 7, connects to 2 communities
- [[.resolver()]] - degree 4, connects to 2 communities
- [[.__init__()_8]] - degree 4, connects to 2 communities
- [[.__init__()_3]] - degree 3, connects to 2 communities
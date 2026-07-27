---
type: community
cohesion: 0.14
members: 22
---

# Broker Contracts

**Cohesion:** 0.14 - loosely connected
**Members:** 22 nodes

## Members
- [[Canonical contract models for broker-agnostic data exchange.  These models defin]] - rationale - scalpr/brokers/contracts.py
- [[Canonical funds and margin model.      Returned by Gateway.funds().]] - rationale - scalpr/brokers/contracts.py
- [[Canonical holdings model for long-term delivery positions.      Returned by Gate]] - rationale - scalpr/brokers/contracts.py
- [[Canonical market depth model with bidask levels.      Returned by Gateway.depth]] - rationale - scalpr/brokers/contracts.py
- [[Canonical market quote model.      Returned by Gateway.quote() and Gateway.ltp()]] - rationale - scalpr/brokers/contracts.py
- [[Canonical tradeexecution fill model.      Returned by Gateway.trades().]] - rationale - scalpr/brokers/contracts.py
- [[Declares supported operations and features for a broker gateway.      Each gatew]] - rationale - scalpr/brokers/capabilities.py
- [[DepthLevel]] - code - scalpr/brokers/contracts.py
- [[Funds]] - code - scalpr/brokers/contracts.py
- [[Gateway capability declarations for broker feature discovery.]] - rationale - scalpr/brokers/capabilities.py
- [[GatewayCapabilities]] - code - scalpr/brokers/capabilities.py
- [[High-level Gateway wrapper with intelligent defaults and simplified API.  This m]] - rationale - scalpr/brokers/gateway.py
- [[Holding]] - code - scalpr/brokers/contracts.py
- [[MarketDepth]] - code - scalpr/brokers/contracts.py
- [[Quote_1]] - code - scalpr/brokers/contracts.py
- [[Single price level in market depth.]] - rationale - scalpr/brokers/contracts.py
- [[Trade_1]] - code - scalpr/brokers/contracts.py
- [[TradeX Gateway - High-level broker-agnostic trading API.]] - rationale - scalpr/brokers/__init__.py
- [[__init__.py_1]] - code - scalpr/brokers/__init__.py
- [[capabilities.py]] - code - scalpr/brokers/capabilities.py
- [[contracts.py]] - code - scalpr/brokers/contracts.py
- [[gateway.py_1]] - code - scalpr/brokers/gateway.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Broker_Contracts
SORT file.name ASC
```

## Connections to other communities
- 9 edges to [[_COMMUNITY_Broker Gateway]]
- 6 edges to [[_COMMUNITY_Broker Registry]]
- 5 edges to [[_COMMUNITY_Scripts - Validate - Gateway]]
- 2 edges to [[_COMMUNITY_Dhan Broker Integration_2]]
- 2 edges to [[_COMMUNITY_Broker Gateway_1]]
- 1 edge to [[_COMMUNITY_Oms - Order]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers]]
- 1 edge to [[_COMMUNITY_Dhan Broker Integration]]
- 1 edge to [[_COMMUNITY_Logging System]]
- 1 edge to [[_COMMUNITY_Market - Data_1]]
- 1 edge to [[_COMMUNITY_Market - Data]]
- 1 edge to [[_COMMUNITY_CLI Commands_1]]
- 1 edge to [[_COMMUNITY_CLI Commands]]
- 1 edge to [[_COMMUNITY_Scripts - Validate - Streaming]]

## Top bridge nodes
- [[gateway.py_1]] - degree 24, connects to 13 communities
- [[Funds]] - degree 7, connects to 3 communities
- [[__init__.py_1]] - degree 13, connects to 2 communities
- [[Holding]] - degree 7, connects to 2 communities
- [[Quote_1]] - degree 6, connects to 2 communities
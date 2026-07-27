---
type: community
cohesion: 0.25
members: 8
---

# Broker Gateway

**Cohesion:** 0.25 - loosely connected
**Members:** 8 nodes

## Members
- [[.funds()]] - code - scalpr/brokers/gateway.py
- [[.ltp()]] - code - scalpr/brokers/gateway.py
- [[.quote()]] - code - scalpr/brokers/gateway.py
- [[Decimal_7]] - code
- [[Fetch available margin limits and fund details.          Returns             Fu]] - rationale - scalpr/brokers/gateway.py
- [[Get Last Traded Price for a symbol.          Args             symbol Trading s_1]] - rationale - scalpr/brokers/gateway.py
- [[Get full market quote for a symbol.          Args             symbol Trading s_1]] - rationale - scalpr/brokers/gateway.py
- [[Quote_2]] - code

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Broker_Gateway
SORT file.name ASC
```

## Connections to other communities
- 3 edges to [[_COMMUNITY_Broker Gateway]]
- 2 edges to [[_COMMUNITY_Broker Contracts]]

## Top bridge nodes
- [[.funds()]] - degree 4, connects to 2 communities
- [[.quote()]] - degree 4, connects to 1 community
- [[Decimal_7]] - degree 4, connects to 1 community
- [[.ltp()]] - degree 3, connects to 1 community
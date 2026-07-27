---
type: community
cohesion: 0.11
members: 26
---

# Dhan Broker Integration

**Cohesion:** 0.11 - loosely connected
**Members:** 26 nodes

## Members
- [[._encode_params()]] - code - scalpr/brokers/dhan/historical.py
- [[._map_timeframe()]] - code - scalpr/brokers/dhan/historical.py
- [[._parse_candles()]] - code - scalpr/brokers/dhan/historical.py
- [[._parse_single_candle()]] - code - scalpr/brokers/dhan/historical.py
- [[._parse_timestamp()]] - code - scalpr/brokers/dhan/historical.py
- [[._resolve_segment()]] - code - scalpr/brokers/dhan/historical.py
- [[._validate_inputs()]] - code - scalpr/brokers/dhan/historical.py
- [[.get_ohlcv()_2]] - code - scalpr/brokers/dhan/historical.py
- [[.get_ohlcv_latest()]] - code - scalpr/brokers/dhan/historical.py
- [[.historical()]] - code - scalpr/brokers/dhan/connection.py
- [[Access historical data adapter.          Raises             BrokerError If not]] - rationale - scalpr/brokers/dhan/connection.py
- [[Adapter for fetching historical OHLCV data from Dhan API.      Responsibilities]] - rationale - scalpr/brokers/dhan/historical.py
- [[Any_5]] - code
- [[Fetch historical candlestick data for a date range.          Args             s]] - rationale - scalpr/brokers/dhan/historical.py
- [[Fetch the latest N candles for a symbol.          Computes a date range that sho]] - rationale - scalpr/brokers/dhan/historical.py
- [[HistoricalDataAdapter]] - code - scalpr/brokers/dhan/historical.py
- [[Map SCALPR timeframe string to Dhan API interval value.]] - rationale - scalpr/brokers/dhan/historical.py
- [[Parse Dhan API response into standard candle dicts.          Expected Dhan respo]] - rationale - scalpr/brokers/dhan/historical.py
- [[Parse a single raw candle dict from the API response.]] - rationale - scalpr/brokers/dhan/historical.py
- [[Parse timestamp string to timezone-aware datetime (UTC).          Handles format]] - rationale - scalpr/brokers/dhan/historical.py
- [[Resolve symbol to (security_id, segment) tuple.          Returns             (s]] - rationale - scalpr/brokers/dhan/historical.py
- [[URL-encode query parameters.]] - rationale - scalpr/brokers/dhan/historical.py
- [[Validate all inputs before making an API call.]] - rationale - scalpr/brokers/dhan/historical.py
- [[date_2]] - code
- [[datetime_1]] - code
- [[historical_adapter()]] - code - tests/unit/brokers/dhan/test_adapters.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Dhan_Broker_Integration
SORT file.name ASC
```

## Connections to other communities
- 5 edges to [[_COMMUNITY_Tests UnitTesting]]
- 3 edges to [[_COMMUNITY_Dhan Broker Integration_16]]
- 2 edges to [[_COMMUNITY_Tests UnitBrokers_3]]
- 2 edges to [[_COMMUNITY_Dhan Broker Integration_6]]
- 2 edges to [[_COMMUNITY_Dhan Broker Integration_2]]
- 2 edges to [[_COMMUNITY_Tests UnitBrokers_10]]
- 1 edge to [[_COMMUNITY_Dhan Broker Integration_10]]
- 1 edge to [[_COMMUNITY_Dhan Broker Integration_17]]
- 1 edge to [[_COMMUNITY_Backtester]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers_4]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers_8]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers_6]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers_7]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers_12]]
- 1 edge to [[_COMMUNITY_Scanner - Options]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers_11]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers_9]]

## Top bridge nodes
- [[HistoricalDataAdapter]] - degree 34, connects to 17 communities
- [[.historical()]] - degree 4, connects to 2 communities
- [[.get_ohlcv_latest()]] - degree 5, connects to 1 community
- [[datetime_1]] - degree 2, connects to 1 community
- [[historical_adapter()]] - degree 2, connects to 1 community
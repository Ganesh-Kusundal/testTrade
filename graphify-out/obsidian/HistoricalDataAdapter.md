---
source_file: "scalpr/brokers/dhan/historical.py"
type: "code"
community: "Dhan Broker Integration"
location: "L51"
tags:
  - graphify/code
  - graphify/EXTRACTED
  - community/Dhan_Broker_Integration
---

# HistoricalDataAdapter

## Connections
- [[.__init__()_3]] - `method` [EXTRACTED]
- [[._encode_params()]] - `method` [EXTRACTED]
- [[._estimate_lookback_days()]] - `method` [EXTRACTED]
- [[._map_timeframe()]] - `method` [EXTRACTED]
- [[._parse_candles()]] - `method` [EXTRACTED]
- [[._parse_single_candle()]] - `method` [EXTRACTED]
- [[._parse_timestamp()]] - `method` [EXTRACTED]
- [[._resolve_segment()]] - `method` [EXTRACTED]
- [[._timeframe_to_minutes()]] - `method` [EXTRACTED]
- [[._validate_inputs()]] - `method` [EXTRACTED]
- [[.connect()_3]] - `calls` [EXTRACTED]
- [[.get_ohlcv()_2]] - `method` [EXTRACTED]
- [[.get_ohlcv_latest()]] - `method` [EXTRACTED]
- [[.historical()]] - `references` [EXTRACTED]
- [[.validate_timeframe()]] - `method` [EXTRACTED]
- [[Adapter for fetching historical OHLCV data from Dhan API.      Responsibilities]] - `rationale_for` [EXTRACTED]
- [[DhanConnection]] - `uses` [INFERRED]
- [[DhanHttpClient]] - `uses` [INFERRED]
- [[OHLCV]] - `uses` [INFERRED]
- [[SymbolResolver]] - `uses` [INFERRED]
- [[TestEndToEndSecurityIdFlow]] - `uses` [INFERRED]
- [[TestHistoricalDataAdapter]] - `uses` [INFERRED]
- [[TestHistoricalSecurityIdUsage]] - `uses` [INFERRED]
- [[TestMarketDataAdapter]] - `uses` [INFERRED]
- [[TestOptionsScannerSecurityIds]] - `uses` [INFERRED]
- [[TestOrdersAdapter]] - `uses` [INFERRED]
- [[TestOrdersSecurityIdUsage]] - `uses` [INFERRED]
- [[TestPortfolioAdapter]] - `uses` [INFERRED]
- [[TestWebSocketSecurityIdResolution]] - `uses` [INFERRED]
- [[connection.py]] - `imports` [EXTRACTED]
- [[historical.py]] - `contains` [EXTRACTED]
- [[historical_adapter()]] - `calls` [EXTRACTED]
- [[test_adapters.py]] - `imports` [EXTRACTED]
- [[test_security_id_consistency.py]] - `imports` [EXTRACTED]

#graphify/code #graphify/EXTRACTED #community/Dhan_Broker_Integration
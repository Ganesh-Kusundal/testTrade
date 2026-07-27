---
type: community
cohesion: 0.09
members: 32
---

# Market - Data

**Cohesion:** 0.09 - loosely connected
**Members:** 32 nodes

## Members
- [[.__init__()_18]] - code - scalpr/market_data/aggregator.py
- [[.__init__()_21]] - code - scalpr/market_data/historical.py
- [[.__init__()_22]] - code - scalpr/market_data/validators.py
- [[._get_bar_start_time()]] - code - scalpr/market_data/aggregator.py
- [[.process_tick()]] - code - scalpr/market_data/aggregator.py
- [[Calculate the bar start time in IST, returning as a UTC tz-aware datetime.]] - rationale - scalpr/market_data/aggregator.py
- [[Process a tick. Returns a closed OHLCV bar if rollover occurred, otherwise None.]] - rationale - scalpr/market_data/aggregator.py
- [[SeamStitcher]] - code - scalpr/market_data/historical.py
- [[SeamStitcher drops any tick with exchange_timestamp = history_end.]] - rationale - tests/unit/market_data/test_market_data.py
- [[Stitches historical and live data, preventing overlap and gaps.]] - rationale - scalpr/market_data/historical.py
- [[Thread-safe Tick-to-OHLCV candle aggregator.]] - rationale - scalpr/market_data/aggregator.py
- [[TickAggregator]] - code - scalpr/market_data/aggregator.py
- [[TickAggregator mutates current candle for ticks within the same bar boundary.]] - rationale - tests/unit/market_data/test_market_data.py
- [[TickAggregator rolls over to a new candle when tick crosses the bar boundary.]] - rationale - tests/unit/market_data/test_market_data.py
- [[TickAggregator sums tick.delta_volume instead of using cumulative_volume in OHLC]] - rationale - tests/unit/market_data/test_market_data.py
- [[TickValidator]] - code - scalpr/market_data/validators.py
- [[TickValidator rejects a tick if exchange_timestamp is older than 5 seconds.]] - rationale - tests/unit/market_data/test_market_data.py
- [[TickValidator rejects ticks with identical or older exchange_timestamp for same]] - rationale - tests/unit/market_data/test_market_data.py
- [[Validates real-time market ticks for deduplication, staleness, and price sanity.]] - rationale - scalpr/market_data/validators.py
- [[aggregator.py]] - code - scalpr/market_data/aggregator.py
- [[datetime_2]] - code
- [[datetime_3]] - code
- [[historical.py_1]] - code - scalpr/market_data/historical.py
- [[test_aggregator_mutates_last_candle_not_push_new()]] - code - tests/unit/market_data/test_market_data.py
- [[test_aggregator_rolls_over_at_bar_boundary()]] - code - tests/unit/market_data/test_market_data.py
- [[test_market_data.py]] - code - tests/unit/market_data/test_market_data.py
- [[test_seam_stitcher_drops_ticks_before_history_end()]] - code - tests/unit/market_data/test_market_data.py
- [[test_validator_deduplicates_same_exchange_timestamp()]] - code - tests/unit/market_data/test_market_data.py
- [[test_validator_rejects_stale_tick()]] - code - tests/unit/market_data/test_market_data.py
- [[test_volume_delta_not_cumulative_in_ohlcv()]] - code - tests/unit/market_data/test_market_data.py
- [[tick.py]] - code - scalpr/domain/tick.py
- [[validators.py]] - code - scalpr/market_data/validators.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Market_-_Data
SORT file.name ASC
```

## Connections to other communities
- 21 edges to [[_COMMUNITY_Market - Data]]
- 10 edges to [[_COMMUNITY_Backtester]]
- 4 edges to [[_COMMUNITY_Signals - Gate]]
- 3 edges to [[_COMMUNITY_Oms - Order]]
- 3 edges to [[_COMMUNITY_Domain Events]]
- 3 edges to [[_COMMUNITY_Simulation - Replay]]
- 2 edges to [[_COMMUNITY_Tests UnitBrokers]]
- 2 edges to [[_COMMUNITY_Tests UnitTesting]]
- 2 edges to [[_COMMUNITY_Broker Registry]]
- 2 edges to [[_COMMUNITY_Dhan Broker Integration_1]]
- 2 edges to [[_COMMUNITY_Market - Data_2]]
- 1 edge to [[_COMMUNITY_API Server]]
- 1 edge to [[_COMMUNITY_Dhan Broker Integration_3]]
- 1 edge to [[_COMMUNITY_Broker Contracts]]
- 1 edge to [[_COMMUNITY_CLI Commands_1]]
- 1 edge to [[_COMMUNITY_Portfolio Management]]
- 1 edge to [[_COMMUNITY_Scripts - Validate - Streaming]]
- 1 edge to [[_COMMUNITY_Market - Data_3]]
- 1 edge to [[_COMMUNITY_Logging System]]

## Top bridge nodes
- [[tick.py]] - degree 37, connects to 15 communities
- [[historical.py_1]] - degree 9, connects to 5 communities
- [[test_market_data.py]] - degree 17, connects to 3 communities
- [[SeamStitcher]] - degree 9, connects to 3 communities
- [[TickAggregator]] - degree 11, connects to 2 communities
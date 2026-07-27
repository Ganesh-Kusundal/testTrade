---
source_file: "tests/unit/market_data/test_market_data.py"
type: "code"
community: "Market - Data"
location: "L109"
tags:
  - graphify/code
  - graphify/EXTRACTED
  - community/Market_-_Data
---

# test_volume_delta_not_cumulative_in_ohlcv()

## Connections
- [[DhanMarketFeed]] - `calls` [EXTRACTED]
- [[TickAggregator]] - `calls` [EXTRACTED]
- [[TickAggregator sums tick.delta_volume instead of using cumulative_volume in OHLC]] - `rationale_for` [EXTRACTED]
- [[test_market_data.py]] - `contains` [EXTRACTED]

#graphify/code #graphify/EXTRACTED #community/Market_-_Data
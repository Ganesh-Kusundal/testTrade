---
type: community
cohesion: 0.17
members: 12
---

# Configuration

**Cohesion:** 0.17 - loosely connected
**Members:** 12 nodes

## Members
- [[._v3()]] - code - config/endpoints.py
- [[.gtt_orders_url()]] - code - config/endpoints.py
- [[.historical_candle_v3_url()]] - code - config/endpoints.py
- [[.intraday_candle_v3_url()]] - code - config/endpoints.py
- [[.market_quote_full_v3_url()]] - code - config/endpoints.py
- [[.market_quote_ltp_v3_url()]] - code - config/endpoints.py
- [[.market_quote_option_greeks_v3_url()]] - code - config/endpoints.py
- [[.mtf_positions_v3_url()]] - code - config/endpoints.py
- [[.token_request_v3_url()]] - code - config/endpoints.py
- [[.user_fund_margin_v3_url()]] - code - config/endpoints.py
- [[Build the v3 historical-candle URL.          V3 supports custom intervals 1-300]] - rationale - config/endpoints.py
- [[Build the v3 intraday-candle URL.          V3 intraday differs from v2 in that i]] - rationale - config/endpoints.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Configuration
SORT file.name ASC
```

## Connections to other communities
- 10 edges to [[_COMMUNITY_Configuration]]

## Top bridge nodes
- [[._v3()]] - degree 10, connects to 1 community
- [[.historical_candle_v3_url()]] - degree 3, connects to 1 community
- [[.intraday_candle_v3_url()]] - degree 3, connects to 1 community
- [[.gtt_orders_url()]] - degree 2, connects to 1 community
- [[.market_quote_full_v3_url()]] - degree 2, connects to 1 community
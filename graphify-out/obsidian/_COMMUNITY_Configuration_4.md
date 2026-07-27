---
type: community
cohesion: 0.17
members: 12
---

# Configuration

**Cohesion:** 0.17 - loosely connected
**Members:** 12 nodes

## Members
- [[._hft()]] - code - config/endpoints.py
- [[.cancel_order_v3_url()]] - code - config/endpoints.py
- [[.feed_authorize_v3_url()]] - code - config/endpoints.py
- [[.gtt_cancel_url()]] - code - config/endpoints.py
- [[.gtt_modify_url()]] - code - config/endpoints.py
- [[.gtt_order_details_url()]] - code - config/endpoints.py
- [[.gtt_place_url()]] - code - config/endpoints.py
- [[.modify_order_v3_url()]] - code - config/endpoints.py
- [[.order_details_url()]] - code - config/endpoints.py
- [[.order_history_url()]] - code - config/endpoints.py
- [[.place_order_v3_url()]] - code - config/endpoints.py
- [[.trades_for_day_url()]] - code - config/endpoints.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Configuration
SORT file.name ASC
```

## Connections to other communities
- 12 edges to [[_COMMUNITY_Configuration]]

## Top bridge nodes
- [[._hft()]] - degree 12, connects to 1 community
- [[.cancel_order_v3_url()]] - degree 2, connects to 1 community
- [[.feed_authorize_v3_url()]] - degree 2, connects to 1 community
- [[.gtt_cancel_url()]] - degree 2, connects to 1 community
- [[.gtt_modify_url()]] - degree 2, connects to 1 community
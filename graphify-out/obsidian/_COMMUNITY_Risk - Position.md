---
type: community
cohesion: 0.25
members: 9
---

# Risk - Position

**Cohesion:** 0.25 - loosely connected
**Members:** 9 nodes

## Members
- [[.__init__()_30]] - code - scalpr/risk/position_sizer.py
- [[.calculate_quantity()]] - code - scalpr/risk/position_sizer.py
- [[ATR-based fixed risk position sizer that aligns quantity to contract lot sizes.]] - rationale - scalpr/risk/position_sizer.py
- [[AtrPositionSizer]] - code - scalpr/risk/position_sizer.py
- [[AtrPositionSizer computes contract lot size aligned trading quantity based on AT]] - rationale - tests/unit/oms/test_oms_risk.py
- [[Calculate quantity floor(risk_amount  (atr  multiplier  lot_size))  lot_siz]] - rationale - scalpr/risk/position_sizer.py
- [[Decimal_15]] - code
- [[position_sizer.py]] - code - scalpr/risk/position_sizer.py
- [[test_atr_position_sizer()]] - code - tests/unit/oms/test_oms_risk.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Risk_-_Position
SORT file.name ASC
```

## Connections to other communities
- 3 edges to [[_COMMUNITY_Oms - Order]]

## Top bridge nodes
- [[AtrPositionSizer]] - degree 6, connects to 1 community
- [[position_sizer.py]] - degree 3, connects to 1 community
- [[test_atr_position_sizer()]] - degree 3, connects to 1 community
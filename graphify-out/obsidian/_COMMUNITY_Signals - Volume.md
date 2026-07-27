---
type: community
cohesion: 0.19
members: 13
---

# Signals - Volume

**Cohesion:** 0.19 - loosely connected
**Members:** 13 nodes

## Members
- [[.__init__()_36]] - code - scalpr/signals/volume_profile.py
- [[._recalculate()]] - code - scalpr/signals/volume_profile.py
- [[.is_lvn()]] - code - scalpr/signals/volume_profile.py
- [[.reset()_2]] - code - scalpr/signals/volume_profile.py
- [[.update()]] - code - scalpr/signals/volume_profile.py
- [[Anchor reset for session open or structure breaks.]] - rationale - scalpr/signals/volume_profile.py
- [[Calculates POC, VAH, VAL, and LVNHVN zones from aggregated bars.]] - rationale - scalpr/signals/volume_profile.py
- [[Decimal_21]] - code
- [[Incorporate a closed OHLCV bar into the profile.]] - rationale - scalpr/signals/volume_profile.py
- [[Returns True if price is in a Low Volume Node area.]] - rationale - scalpr/signals/volume_profile.py
- [[VolumeProfile]] - code - scalpr/signals/volume_profile.py
- [[VolumeProfile accumulates volumes and correctly identifies POC and LVNs.]] - rationale - tests/unit/strategy_sim/test_strategy_sim.py
- [[test_volume_profile_calculations()]] - code - tests/unit/strategy_sim/test_strategy_sim.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Signals_-_Volume
SORT file.name ASC
```

## Connections to other communities
- 7 edges to [[_COMMUNITY_Signals - Gate]]
- 3 edges to [[_COMMUNITY_Backtester]]

## Top bridge nodes
- [[VolumeProfile]] - degree 13, connects to 2 communities
- [[test_volume_profile_calculations()]] - degree 4, connects to 2 communities
- [[Decimal_21]] - degree 4, connects to 1 community
- [[.update()]] - degree 4, connects to 1 community
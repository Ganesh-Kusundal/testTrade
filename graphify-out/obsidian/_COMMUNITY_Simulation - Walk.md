---
type: community
cohesion: 0.25
members: 9
---

# Simulation - Walk

**Cohesion:** 0.25 - loosely connected
**Members:** 9 nodes

## Members
- [[.__init__()_40]] - code - scalpr/simulation/walk_forward.py
- [[.generate_windows()]] - code - scalpr/simulation/walk_forward.py
- [[Generate rolling traintest windows across date bounds.]] - rationale - scalpr/simulation/walk_forward.py
- [[Manages walk-forward optimization segments for robust parameter validation.]] - rationale - scalpr/simulation/walk_forward.py
- [[WalkForwardValidator]] - code - scalpr/simulation/walk_forward.py
- [[WalkForwardValidator splits historical ranges into rolling training and testing]] - rationale - tests/unit/strategy_sim/test_strategy_sim.py
- [[datetime_6]] - code
- [[test_walk_forward_validator()]] - code - tests/unit/strategy_sim/test_strategy_sim.py
- [[walk_forward.py]] - code - scalpr/simulation/walk_forward.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Simulation_-_Walk
SORT file.name ASC
```

## Connections to other communities
- 3 edges to [[_COMMUNITY_Signals - Gate]]
- 1 edge to [[_COMMUNITY_Logging System]]

## Top bridge nodes
- [[walk_forward.py]] - degree 4, connects to 2 communities
- [[WalkForwardValidator]] - degree 6, connects to 1 community
- [[test_walk_forward_validator()]] - degree 3, connects to 1 community
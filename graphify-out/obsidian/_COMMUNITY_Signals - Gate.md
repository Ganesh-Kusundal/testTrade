---
type: community
cohesion: 0.10
members: 35
---

# Signals - Gate

**Cohesion:** 0.10 - loosely connected
**Members:** 35 nodes

## Members
- [[.__init__()_34]] - code - scalpr/signals/cvd.py
- [[.__init__()_35]] - code - scalpr/signals/gate_fsm.py
- [[.__init__()_42]] - code - scalpr/strategy/scalpr_amt.py
- [[.evaluate()]] - code - scalpr/signals/gate_fsm.py
- [[.get_status()]] - code - scalpr/strategy/scalpr_amt.py
- [[.is_diverged()]] - code - scalpr/signals/cvd.py
- [[.on_tick()_5]] - code - scalpr/strategy/scalpr_amt.py
- [[.reset()_1]] - code - scalpr/signals/cvd.py
- [[CvdTracker]] - code - scalpr/signals/cvd.py
- [[CvdTracker correctly accumulates delta and identifies divergence from price.]] - rationale - tests/unit/strategy_sim/test_strategy_sim.py
- [[Decimal_19]] - code
- [[Detect divergence between CVD slope and price slope over lookback window.]] - rationale - scalpr/signals/cvd.py
- [[Evaluate Gates 01 to 08 in strict sequential order. Short-circuits on failure.]] - rationale - scalpr/signals/gate_fsm.py
- [[Evaluates sequential filter Gates 01-08 for trade entry short-circuiting.]] - rationale - scalpr/signals/gate_fsm.py
- [[EventDrivenBacktester executes historical simulation and charges trading fees.]] - rationale - tests/unit/strategy_sim/test_strategy_sim.py
- [[Fabio Valentini AMT Intraday Options Scalping Strategy.]] - rationale - scalpr/strategy/scalpr_amt.py
- [[GateFSM]] - code - scalpr/signals/gate_fsm.py
- [[GateFSM Gate 03 blocks falling CVD when not at LVN, but passes when at LVN.]] - rationale - tests/unit/strategy_sim/test_strategy_sim.py
- [[GateResult]] - code - scalpr/signals/gate_fsm.py
- [[GateState]] - code - scalpr/signals/gate_fsm.py
- [[Process live tick, feed CVD, evaluate Gate FSM, and trigger buysell orders.]] - rationale - scalpr/strategy/scalpr_amt.py
- [[Represents the market state evaluated by the Gates.]] - rationale - scalpr/signals/gate_fsm.py
- [[Result of evaluating a single filter gate.]] - rationale - scalpr/signals/gate_fsm.py
- [[Return strategy status for observability endpoint.]] - rationale - scalpr/strategy/scalpr_amt.py
- [[ScalprAmtStrategy]] - code - scalpr/strategy/scalpr_amt.py
- [[Tracks Cumulative Volume Delta (CVD) and divergence from price action.]] - rationale - scalpr/signals/cvd.py
- [[cvd.py]] - code - scalpr/signals/cvd.py
- [[datetime_5]] - code
- [[gate_fsm.py]] - code - scalpr/signals/gate_fsm.py
- [[scalpr_amt.py]] - code - scalpr/strategy/scalpr_amt.py
- [[test_cvd_tracker_divergence()]] - code - tests/unit/strategy_sim/test_strategy_sim.py
- [[test_event_driven_backtester()]] - code - tests/unit/strategy_sim/test_strategy_sim.py
- [[test_gate_fsm_gate_03_logic()]] - code - tests/unit/strategy_sim/test_strategy_sim.py
- [[test_strategy_sim.py]] - code - tests/unit/strategy_sim/test_strategy_sim.py
- [[volume_profile.py]] - code - scalpr/signals/volume_profile.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Signals_-_Gate
SORT file.name ASC
```

## Connections to other communities
- 15 edges to [[_COMMUNITY_Oms - Order]]
- 13 edges to [[_COMMUNITY_Tests UnitBrokers]]
- 12 edges to [[_COMMUNITY_Backtester]]
- 8 edges to [[_COMMUNITY_Market - Data]]
- 7 edges to [[_COMMUNITY_Signals - Volume]]
- 5 edges to [[_COMMUNITY_Scanner - Options]]
- 5 edges to [[_COMMUNITY_Simulation - Replay]]
- 4 edges to [[_COMMUNITY_Dhan Broker Integration_2]]
- 4 edges to [[_COMMUNITY_Market - Data_1]]
- 3 edges to [[_COMMUNITY_Portfolio Management]]
- 3 edges to [[_COMMUNITY_Technical Indicators]]
- 3 edges to [[_COMMUNITY_Simulation - Walk]]
- 2 edges to [[_COMMUNITY_API Server]]
- 2 edges to [[_COMMUNITY_Domain Events]]
- 2 edges to [[_COMMUNITY_Oms - Paper]]
- 2 edges to [[_COMMUNITY_Portfolio Analytics]]
- 1 edge to [[_COMMUNITY_Logging System]]

## Top bridge nodes
- [[test_strategy_sim.py]] - degree 56, connects to 15 communities
- [[scalpr_amt.py]] - degree 25, connects to 9 communities
- [[ScalprAmtStrategy]] - degree 23, connects to 7 communities
- [[test_event_driven_backtester()]] - degree 7, connects to 3 communities
- [[volume_profile.py]] - degree 6, connects to 3 communities
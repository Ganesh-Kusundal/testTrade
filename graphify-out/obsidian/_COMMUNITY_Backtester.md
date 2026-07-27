---
type: community
cohesion: 0.09
members: 35
---

# Backtester

**Cohesion:** 0.09 - loosely connected
**Members:** 35 nodes

## Members
- [[.__init__()_37]] - code - scalpr/simulation/backtester.py
- [[.__init__()_38]] - code - scalpr/simulation/fill_simulator.py
- [[.__post_init__()_8]] - code - scalpr/domain/tick.py
- [[._charge_fees()]] - code - scalpr/simulation/backtester.py
- [[._safe_on_bar()]] - code - scalpr/strategy/executor.py
- [[.check_limit_fill()]] - code - scalpr/simulation/fill_simulator.py
- [[.on_bar()]] - code - scalpr/strategy/executor.py
- [[.on_bar()_1]] - code - scalpr/strategy/scalpr_amt.py
- [[.on_bar()_2]] - code - scalpr/strategy/strategy_port.py
- [[.run()]] - code - scalpr/simulation/backtester.py
- [[.simulate_market_fill()]] - code - scalpr/simulation/fill_simulator.py
- [[Abstract Port representing the contract every strategy must satisfy.]] - rationale - scalpr/strategy/strategy_port.py
- [[Calculate market order fill price incorporating slippage.]] - rationale - scalpr/simulation/fill_simulator.py
- [[Charge brokerage + Securities Transaction Tax (STT) at Indian market rates.]] - rationale - scalpr/simulation/backtester.py
- [[Check if a limit order would be filled by the OHLCV bar.]] - rationale - scalpr/simulation/fill_simulator.py
- [[Decimal_22]] - code
- [[Decimal_23]] - code
- [[EventDrivenBacktester]] - code - scalpr/simulation/backtester.py
- [[Execute single strategy bar handler with timeout and error isolation.]] - rationale - scalpr/strategy/executor.py
- [[FillSimulator]] - code - scalpr/simulation/fill_simulator.py
- [[Handle completed historicallive candle bar.]] - rationale - scalpr/strategy/strategy_port.py
- [[Historical backtest simulator executing strategies over OHLCV sequences.]] - rationale - scalpr/simulation/backtester.py
- [[Historical or aggregated OHLCV candle bar.]] - rationale - scalpr/domain/tick.py
- [[IStrategy]] - code - scalpr/strategy/strategy_port.py
- [[Incorporate closed bar into the volume profile.]] - rationale - scalpr/strategy/scalpr_amt.py
- [[OHLCV]] - code - scalpr/domain/tick.py
- [[OHLCV bar boundary open time is stored in UTC timezone-aware format.]] - rationale - tests/unit/domain/test_domain.py
- [[OrderSide_3]] - code
- [[Route incoming candle bar to all strategies with timeout protection.]] - rationale - scalpr/strategy/executor.py
- [[Run backtest. Feeds bars to strategy sequentially.]] - rationale - scalpr/simulation/backtester.py
- [[Simulates realistic limit and market order executions under slippage and cost mo]] - rationale - scalpr/simulation/fill_simulator.py
- [[backtester.py]] - code - scalpr/simulation/backtester.py
- [[fill_simulator.py]] - code - scalpr/simulation/fill_simulator.py
- [[strategy_port.py]] - code - scalpr/strategy/strategy_port.py
- [[test_ohlcv_bar_boundary_is_utc()]] - code - tests/unit/domain/test_domain.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Backtester
SORT file.name ASC
```

## Connections to other communities
- 23 edges to [[_COMMUNITY_Domain Events]]
- 18 edges to [[_COMMUNITY_Tests UnitTesting]]
- 12 edges to [[_COMMUNITY_Signals - Gate]]
- 10 edges to [[_COMMUNITY_Oms - Order]]
- 10 edges to [[_COMMUNITY_Tests UnitBrokers]]
- 10 edges to [[_COMMUNITY_Market - Data_1]]
- 9 edges to [[_COMMUNITY_Simulation - Replay]]
- 5 edges to [[_COMMUNITY_Market - Data]]
- 3 edges to [[_COMMUNITY_Signals - Volume]]
- 3 edges to [[_COMMUNITY_Oms - Paper]]
- 2 edges to [[_COMMUNITY_Market - Data_3]]
- 2 edges to [[_COMMUNITY_Chaos Testing]]
- 1 edge to [[_COMMUNITY_Dhan Broker Integration_5]]

## Top bridge nodes
- [[OHLCV]] - degree 71, connects to 10 communities
- [[IStrategy]] - degree 26, connects to 5 communities
- [[backtester.py]] - degree 15, connects to 5 communities
- [[strategy_port.py]] - degree 8, connects to 4 communities
- [[EventDrivenBacktester]] - degree 14, connects to 3 communities
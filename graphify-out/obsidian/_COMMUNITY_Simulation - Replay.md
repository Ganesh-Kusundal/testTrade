---
type: community
cohesion: 0.05
members: 44
---

# Simulation - Replay

**Cohesion:** 0.05 - loosely connected
**Members:** 44 nodes

## Members
- [[.__class__()]] - code - tests/unit/strategy/test_async_executor.py
- [[.__init__()_39]] - code - scalpr/simulation/replay_engine.py
- [[.__init__()_41]] - code - scalpr/strategy/executor.py
- [[.__init__()_52]] - code - tests/unit/strategy/test_async_executor.py
- [[._safe_on_tick()]] - code - scalpr/strategy/executor.py
- [[.get_strategy_info()]] - code - scalpr/strategy/executor.py
- [[.load_from_events()]] - code - scalpr/simulation/replay_engine.py
- [[.on_tick()_4]] - code - scalpr/strategy/executor.py
- [[.on_tick()_7]] - code - tests/unit/strategy/test_async_executor.py
- [[.register_strategy()]] - code - scalpr/strategy/executor.py
- [[.restore_checkpoint()]] - code - scalpr/simulation/replay_engine.py
- [[.save_checkpoint()]] - code - scalpr/simulation/replay_engine.py
- [[.setup_replay()]] - code - tests/unit/observability/test_event_store.py
- [[.start()_2]] - code - scalpr/simulation/replay_engine.py
- [[.stop()_1]] - code - scalpr/simulation/replay_engine.py
- [[.test_async_executor_with_multiple_failures()]] - code - tests/unit/testing/test_chaos.py
- [[.test_crashing_strategy_isolated()]] - code - tests/unit/testing/test_chaos.py
- [[.test_slow_strategy()]] - code - tests/unit/testing/test_chaos.py
- [[.test_slow_strategy_with_timeout()]] - code - tests/unit/testing/test_chaos.py
- [[Checkpoint index saving.]] - rationale - scalpr/simulation/replay_engine.py
- [[Checkpoint restoring.]] - rationale - scalpr/simulation/replay_engine.py
- [[Execute single strategy with timeout and error isolation.]] - rationale - scalpr/strategy/executor.py
- [[Historical tick replayer for backtesting and logic debugging.]] - rationale - scalpr/simulation/replay_engine.py
- [[Historical tick replayer for backtesting and logic debugging.  Extended to suppo]] - rationale - scalpr/simulation/replay_engine.py
- [[Load ticks from event store for replay.                  Args             event]] - rationale - scalpr/simulation/replay_engine.py
- [[Orchestrates strategy execution by routing market ticks and bars to registered s]] - rationale - scalpr/strategy/executor.py
- [[ReplayEngine]] - code - scalpr/simulation/replay_engine.py
- [[ReplayEngine streams ticks and preserves checkpoint saverestore locations.]] - rationale - tests/unit/strategy_sim/test_strategy_sim.py
- [[Return list of registered strategies with their identifiers.]] - rationale - scalpr/strategy/executor.py
- [[Route incoming tick to all strategies with timeout protection.]] - rationale - scalpr/strategy/executor.py
- [[Setup replay engine with event store.]] - rationale - tests/unit/observability/test_event_store.py
- [[SlowStrategy]] - code - tests/unit/strategy/test_async_executor.py
- [[Start streaming ticks to strategy executor.]] - rationale - scalpr/simulation/replay_engine.py
- [[Strategy that sleeps to simulate slow execution.]] - rationale - tests/unit/strategy/test_async_executor.py
- [[StrategyExecutor]] - code - scalpr/strategy/executor.py
- [[Test async executor handles multiple simultaneous failures.]] - rationale - tests/unit/testing/test_chaos.py
- [[Test slow strategy creation.]] - rationale - tests/unit/testing/test_chaos.py
- [[Test that async executor handles slow strategy with timeout.]] - rationale - tests/unit/testing/test_chaos.py
- [[Test that crashing strategy doesn't block others.]] - rationale - tests/unit/testing/test_chaos.py
- [[Tests for async strategy executor with timeouts.]] - rationale - tests/unit/strategy/test_async_executor.py
- [[executor.py]] - code - scalpr/strategy/executor.py
- [[replay_engine.py]] - code - scalpr/simulation/replay_engine.py
- [[test_async_executor.py]] - code - tests/unit/strategy/test_async_executor.py
- [[test_replay_engine_checkpoints()]] - code - tests/unit/strategy_sim/test_strategy_sim.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Simulation_-_Replay
SORT file.name ASC
```

## Connections to other communities
- 20 edges to [[_COMMUNITY_Tests UnitStrategy]]
- 19 edges to [[_COMMUNITY_Tests UnitTesting]]
- 10 edges to [[_COMMUNITY_Market - Data]]
- 9 edges to [[_COMMUNITY_Domain Events]]
- 9 edges to [[_COMMUNITY_Backtester]]
- 5 edges to [[_COMMUNITY_Signals - Gate]]
- 4 edges to [[_COMMUNITY_API Server]]
- 3 edges to [[_COMMUNITY_Market - Data_1]]
- 2 edges to [[_COMMUNITY_Tests UnitBrokers]]
- 2 edges to [[_COMMUNITY_Logging System]]
- 2 edges to [[_COMMUNITY_Tests UnitObservability]]
- 1 edge to [[_COMMUNITY_Dhan Broker Integration_2]]
- 1 edge to [[_COMMUNITY_Tracing]]

## Top bridge nodes
- [[StrategyExecutor]] - degree 50, connects to 8 communities
- [[executor.py]] - degree 13, connects to 8 communities
- [[replay_engine.py]] - degree 10, connects to 6 communities
- [[ReplayEngine]] - degree 18, connects to 5 communities
- [[test_async_executor.py]] - degree 12, connects to 5 communities
---
source_file: "scalpr/strategy/executor.py"
type: "code"
community: "Simulation - Replay"
location: "L15"
tags:
  - graphify/code
  - graphify/EXTRACTED
  - community/Simulation_-_Replay
---

# StrategyExecutor

## Connections
- [[.__init__()_39]] - `references` [EXTRACTED]
- [[.__init__()_41]] - `method` [EXTRACTED]
- [[._safe_on_bar()]] - `method` [EXTRACTED]
- [[._safe_on_tick()]] - `method` [EXTRACTED]
- [[.get_strategy_info()]] - `method` [EXTRACTED]
- [[.on_bar()]] - `method` [EXTRACTED]
- [[.on_tick()_4]] - `method` [EXTRACTED]
- [[.register_strategy()]] - `method` [EXTRACTED]
- [[.test_async_executor_with_multiple_failures()]] - `calls` [EXTRACTED]
- [[.test_crashing_strategy_isolated()]] - `calls` [EXTRACTED]
- [[.test_fast_strategy_completes()]] - `calls` [EXTRACTED]
- [[.test_metrics_recorded()]] - `calls` [EXTRACTED]
- [[.test_multiple_strategies_execute()]] - `calls` [EXTRACTED]
- [[.test_no_strategies_no_error()]] - `calls` [EXTRACTED]
- [[.test_slow_strategy_times_out()]] - `calls` [EXTRACTED]
- [[.test_slow_strategy_with_timeout()]] - `calls` [EXTRACTED]
- [[.test_strategy_error_counter_incremented()]] - `calls` [EXTRACTED]
- [[.test_strategy_error_doesnt_block_others()]] - `calls` [EXTRACTED]
- [[.test_strategy_timeout_counter_incremented()]] - `calls` [EXTRACTED]
- [[.test_timeout_records_metrics()]] - `calls` [EXTRACTED]
- [[ConnectionManager]] - `uses` [INFERRED]
- [[FailingStrategy]] - `uses` [INFERRED]
- [[FastStrategy]] - `uses` [INFERRED]
- [[IStrategy]] - `uses` [INFERRED]
- [[MockTick]] - `uses` [INFERRED]
- [[OHLCV]] - `uses` [INFERRED]
- [[Orchestrates strategy execution by routing market ticks and bars to registered s]] - `rationale_for` [EXTRACTED]
- [[ReplayEngine]] - `uses` [INFERRED]
- [[SlowStrategy]] - `uses` [INFERRED]
- [[TestAsyncStrategyExecutor]] - `uses` [INFERRED]
- [[TestBrokerFailureInjector]] - `uses` [INFERRED]
- [[TestChaosMonkey]] - `uses` [INFERRED]
- [[TestChaosTestSuite]] - `uses` [INFERRED]
- [[TestCircuitBreakerValidator]] - `uses` [INFERRED]
- [[TestEventStore]] - `uses` [INFERRED]
- [[TestIntegrationChaosScenarios]] - `uses` [INFERRED]
- [[TestMarketDataDisruptor]] - `uses` [INFERRED]
- [[TestOrderFailureInjector]] - `uses` [INFERRED]
- [[TestPersistenceFailureInjector]] - `uses` [INFERRED]
- [[TestReplayEngineWithEvents]] - `uses` [INFERRED]
- [[TestStrategyFaultInjector]] - `uses` [INFERRED]
- [[Tick]] - `uses` [INFERRED]
- [[executor.py]] - `contains` [EXTRACTED]
- [[main.py]] - `imports` [EXTRACTED]
- [[replay_engine.py]] - `imports` [EXTRACTED]
- [[test_async_executor.py]] - `imports` [EXTRACTED]
- [[test_chaos.py]] - `imports` [EXTRACTED]
- [[test_event_store.py]] - `imports` [EXTRACTED]
- [[test_replay_engine_checkpoints()]] - `calls` [EXTRACTED]
- [[test_strategy_sim.py]] - `imports` [EXTRACTED]

#graphify/code #graphify/EXTRACTED #community/Simulation_-_Replay
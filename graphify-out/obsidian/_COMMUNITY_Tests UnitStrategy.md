---
type: community
cohesion: 0.10
members: 33
---

# Tests: Unit/Strategy

**Cohesion:** 0.10 - loosely connected
**Members:** 33 nodes

## Members
- [[.__class__()_2]] - code - tests/unit/strategy/test_async_executor.py
- [[.__class__()_1]] - code - tests/unit/strategy/test_async_executor.py
- [[.__init__()_54]] - code - tests/unit/strategy/test_async_executor.py
- [[.__init__()_53]] - code - tests/unit/strategy/test_async_executor.py
- [[.__init__()_51]] - code - tests/unit/strategy/test_async_executor.py
- [[.on_tick()_9]] - code - tests/unit/strategy/test_async_executor.py
- [[.on_tick()_8]] - code - tests/unit/strategy/test_async_executor.py
- [[.test_fast_strategy_completes()]] - code - tests/unit/strategy/test_async_executor.py
- [[.test_metrics_recorded()]] - code - tests/unit/strategy/test_async_executor.py
- [[.test_multiple_strategies_execute()]] - code - tests/unit/strategy/test_async_executor.py
- [[.test_no_strategies_no_error()]] - code - tests/unit/strategy/test_async_executor.py
- [[.test_slow_strategy_times_out()]] - code - tests/unit/strategy/test_async_executor.py
- [[.test_strategy_error_counter_incremented()]] - code - tests/unit/strategy/test_async_executor.py
- [[.test_strategy_error_doesnt_block_others()]] - code - tests/unit/strategy/test_async_executor.py
- [[.test_strategy_timeout_counter_incremented()]] - code - tests/unit/strategy/test_async_executor.py
- [[.test_timeout_records_metrics()]] - code - tests/unit/strategy/test_async_executor.py
- [[FailingStrategy]] - code - tests/unit/strategy/test_async_executor.py
- [[FastStrategy]] - code - tests/unit/strategy/test_async_executor.py
- [[Mock tick for testing.]] - rationale - tests/unit/strategy/test_async_executor.py
- [[MockTick]] - code - tests/unit/strategy/test_async_executor.py
- [[Strategy that executes quickly.]] - rationale - tests/unit/strategy/test_async_executor.py
- [[Strategy that raises exceptions.]] - rationale - tests/unit/strategy/test_async_executor.py
- [[Test async strategy execution with timeouts.]] - rationale - tests/unit/strategy/test_async_executor.py
- [[TestAsyncStrategyExecutor]] - code - tests/unit/strategy/test_async_executor.py
- [[Verify error counter is incremented on exception.]] - rationale - tests/unit/strategy/test_async_executor.py
- [[Verify execution metrics are recorded.]] - rationale - tests/unit/strategy/test_async_executor.py
- [[Verify executor handles empty strategy list.]] - rationale - tests/unit/strategy/test_async_executor.py
- [[Verify fast strategy completes within timeout.]] - rationale - tests/unit/strategy/test_async_executor.py
- [[Verify multiple strategies all execute.]] - rationale - tests/unit/strategy/test_async_executor.py
- [[Verify one strategy error doesn't prevent others from executing.]] - rationale - tests/unit/strategy/test_async_executor.py
- [[Verify slow strategy times out (timeout prevents blocking, not thread cancellati]] - rationale - tests/unit/strategy/test_async_executor.py
- [[Verify timeout counter is incremented on timeout.]] - rationale - tests/unit/strategy/test_async_executor.py
- [[Verify timeout is recorded in metrics even if thread continues.]] - rationale - tests/unit/strategy/test_async_executor.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Tests_Unit/Strategy
SORT file.name ASC
```

## Connections to other communities
- 20 edges to [[_COMMUNITY_Simulation - Replay]]
- 4 edges to [[_COMMUNITY_Tests UnitBrokers]]
- 4 edges to [[_COMMUNITY_Market - Data]]

## Top bridge nodes
- [[MockTick]] - degree 15, connects to 3 communities
- [[TestAsyncStrategyExecutor]] - degree 14, connects to 3 communities
- [[FastStrategy]] - degree 12, connects to 3 communities
- [[FailingStrategy]] - degree 10, connects to 3 communities
- [[.test_strategy_error_doesnt_block_others()]] - degree 7, connects to 1 community
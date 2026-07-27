---
type: community
cohesion: 0.06
members: 45
---

# Chaos Testing

**Cohesion:** 0.06 - loosely connected
**Members:** 45 nodes

## Members
- [[.__init__()_47]] - code - scalpr/testing/chaos.py
- [[._test_broker_failures()]] - code - scalpr/testing/chaos.py
- [[._test_circuit_breakers()]] - code - scalpr/testing/chaos.py
- [[._test_market_data_disruption()]] - code - scalpr/testing/chaos.py
- [[._test_order_failures()]] - code - scalpr/testing/chaos.py
- [[._test_persistence_failures()]] - code - scalpr/testing/chaos.py
- [[.generate_malformed_ticks()]] - code - scalpr/testing/chaos.py
- [[.generate_out_of_order_ticks()]] - code - scalpr/testing/chaos.py
- [[.generate_stale_ticks()]] - code - scalpr/testing/chaos.py
- [[.inject_http_error()]] - code - scalpr/testing/chaos.py
- [[.patch_broker_http()]] - code - scalpr/testing/chaos.py
- [[.run_all()]] - code - scalpr/testing/chaos.py
- [[.simulate_db_locked()]] - code - scalpr/testing/chaos.py
- [[.test_circuit_breaker_results()]] - code - tests/unit/testing/test_chaos.py
- [[.test_daily_loss_trip()]] - code - scalpr/testing/chaos.py
- [[.test_daily_loss_trip_validation()]] - code - tests/unit/testing/test_chaos.py
- [[.test_drawdown_trip()]] - code - scalpr/testing/chaos.py
- [[.test_drawdown_trip_validation()]] - code - tests/unit/testing/test_chaos.py
- [[.test_manual_halt()]] - code - scalpr/testing/chaos.py
- [[.test_manual_halt_validation()]] - code - tests/unit/testing/test_chaos.py
- [[.test_run_all_scenarios()]] - code - tests/unit/testing/test_chaos.py
- [[Any_18]] - code
- [[ChaosTestSuite]] - code - scalpr/testing/chaos.py
- [[Complete chaos test suite running all scenarios.          Usage         suite =]] - rationale - scalpr/testing/chaos.py
- [[Context manager to patch broker HTTP calls with failures.                  Args]] - rationale - scalpr/testing/chaos.py
- [[Create mock that raises HTTP error after N successful calls.                  Ar]] - rationale - scalpr/testing/chaos.py
- [[Decimal_24]] - code
- [[Generate ticks with identical timestamps (stale data).]] - rationale - scalpr/testing/chaos.py
- [[Generate ticks with missinginvalid fields.]] - rationale - scalpr/testing/chaos.py
- [[Generate ticks with non-monotonic timestamps.]] - rationale - scalpr/testing/chaos.py
- [[Run all chaos test scenarios.]] - rationale - scalpr/testing/chaos.py
- [[Simulate SQLite database locked error.]] - rationale - scalpr/testing/chaos.py
- [[Test broker failure handling.]] - rationale - scalpr/testing/chaos.py
- [[Test circuit breaker chaos results.]] - rationale - tests/unit/testing/test_chaos.py
- [[Test circuit breaker resilience.]] - rationale - scalpr/testing/chaos.py
- [[Test daily loss circuit breaker trip.]] - rationale - tests/unit/testing/test_chaos.py
- [[Test drawdown circuit breaker trip.]] - rationale - tests/unit/testing/test_chaos.py
- [[Test manual halt override.]] - rationale - tests/unit/testing/test_chaos.py
- [[Test market data disruption handling.]] - rationale - scalpr/testing/chaos.py
- [[Test order failure handling.]] - rationale - scalpr/testing/chaos.py
- [[Test persistence failure handling.]] - rationale - scalpr/testing/chaos.py
- [[Test running all chaos scenarios.]] - rationale - tests/unit/testing/test_chaos.py
- [[Validate circuit breaker trips on daily loss.]] - rationale - scalpr/testing/chaos.py
- [[Validate circuit breaker trips on drawdown.]] - rationale - scalpr/testing/chaos.py
- [[Validate manual halt override.]] - rationale - scalpr/testing/chaos.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Chaos_Testing
SORT file.name ASC
```

## Connections to other communities
- 37 edges to [[_COMMUNITY_Tests UnitTesting]]
- 4 edges to [[_COMMUNITY_Market - Data]]
- 2 edges to [[_COMMUNITY_Backtester]]
- 1 edge to [[_COMMUNITY_Domain Events]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers]]
- 1 edge to [[_COMMUNITY_Market - Data_2]]

## Top bridge nodes
- [[ChaosTestSuite]] - degree 30, connects to 6 communities
- [[.generate_malformed_ticks()]] - degree 5, connects to 2 communities
- [[.generate_out_of_order_ticks()]] - degree 5, connects to 2 communities
- [[.generate_stale_ticks()]] - degree 5, connects to 2 communities
- [[._test_market_data_disruption()]] - degree 9, connects to 1 community
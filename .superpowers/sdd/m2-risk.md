# M2 — Replace `Mock()` gateway with `SimulatedGateway` in risk tests

**File:** `tests/unit/risk/test_session_guard.py`

## Mock count

| Metric | Before | After |
|---|---|---|
| `Mock()` calls | 23 | 0 |
| `SimulatedGateway()` calls | 0 | 23 |
| Mock-assertion lines removed | — | 9 |

## Changes

1. **Import:** `from unittest.mock import Mock` → `from scalpr.simulation.simulated_gateway import SimulatedGateway`
2. **All 23** `gateway = Mock()` → `gateway = SimulatedGateway(starting_capital=Decimal("100000"))`
3. **Removed 9** `gateway.square_off_all.assert_*()` lines — redundant because `guard.halted` / `guard._warned_*` / `result` state assertions already cover the same semantics.

No tests set mock return values, so no extra configuration needed. No mocks were retained (all mock assertions were purely call-count checks duplicating state assertions).

## Test results

```
tests/unit/risk/test_session_guard.py — 41 passed (same as before)
tests/unit/risk/                 — 54 passed (same as before)
```

Zero regressions.

## Summary

`SimulatedGateway` is a drop-in replacement for `Mock()` in all 23 gateway uses. The tests now exercise real gateway methods (`square_off_all` actually squares off positions instead of tracking call counts) while still being fully deterministic and in-process.

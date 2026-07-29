# M7 — Replace `MagicMock` with real/spec'd implementations in execution tests

## Task
Replace `MagicMock` with real `SimulatedGateway`, `PreTradeRiskGate`, `CircuitBreaker` in `test_order_router_rate_limit.py` (7 mocks) and `test_order_router_error_policy.py` (5 mocks). Keep minimal `spec=` mocks where call-tracking or error simulation is needed.

## Changes

### `tests/unit/execution/test_order_router_rate_limit.py`

| Location | Before | After |
|---|---|---|
| `_make_router()` helper | 3× `MagicMock()` (gateway, risk_gate, cb) | 3× real: `SimulatedGateway(starting_capital=Decimal("1000000"))`, `PreTradeRiskGate(max_capital_risk_pct=0.03)`, `CircuitBreaker()` |
| `test_rate_limit_checked_before_risk_checks` | 3× `MagicMock()` (gateway, risk_gate, cb) with side effects | 3× `MagicMock(spec=SimulatedGateway\|PreTradeRiskGate\|CircuitBreaker)` — keeps side effects, adds `spec=` enforcement |

### `tests/unit/execution/test_order_router_error_policy.py`

| Location | Before | After |
|---|---|---|
| `mock_gateway` | `MagicMock()` | `MagicMock(spec=SimulatedGateway)` — needs `assert_not_called` |
| `mock_risk_gate` | `MagicMock()` | Real `PreTradeRiskGate(max_capital_risk_pct=0.03)` |
| `mock_cb` | `MagicMock()` | Real `CircuitBreaker()` |
| `mock_oms` | `MagicMock()` | `MagicMock(spec=OrderManager)` — needs `side_effect` for persistence failure |

All real `PreTradeRiskGate` instances configured with `max_capital_risk_pct=0.03` (3% of 1M = 30,000 max notional) to allow the 25,000 test order notional through.

## Mock count

| File | Before | After | Reduction |
|---|---|---|---|
| `test_order_router_rate_limit.py` | 6 | 3 | −3 (50%) |
| `test_order_router_error_policy.py` | 4 | 2 | −2 (50%) |
| **Total** | **10** | **5** | **−5 (50%)** |

All 5 remaining mocks have `spec=` constraints enforcing interface contracts.

## Test results

```
7 passed in 1.27s
```

Status: ✅ All tests pass.

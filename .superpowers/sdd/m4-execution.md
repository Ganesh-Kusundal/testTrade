# M4 — Replace MagicMock with SimulatedGateway

**Status:** ✅ Complete (13/13 passed)

## Files modified

| File | MagicMock before | MagicMock after | Delta |
|------|------------------|-----------------|-------|
| `tests/unit/execution/test_order_router_persistence.py` | 8 | 5 | **-3** |
| `tests/unit/brokers/dhan/test_security_id_consistency.py` | 9 | 0 | **-9** |
| **Total** | **17** | **5** | **-12** |

## Changes

### `test_order_router_persistence.py` — 3 gateway mocks → `SimulatedGateway`

- Added `_GatewaySpy(SimulatedGateway)` — wraps real gateway with call-tracking for assertions while running real order lifecycle.
- 3 `mock_gateway = MagicMock()` → `_GatewaySpy(call_order)` / `_GatewaySpy()`.
- Removed `.return_value`, `.side_effect`, and manual `Fill` construction (SimulatedGateway produces real fills).
- `mock_gateway.place_order.assert_not_called()` → `assert not gateway.place_order_called`.
- Remaining 5 `MagicMock()` instances: `mock_risk_gate`(x1), `mock_cb`(x1), `mock_oms`(x3) — these are not gateway mocks and stay as-is.

### `test_security_id_consistency.py` — 9 mocks → hand-written stubs

- `from unittest.mock import MagicMock` removed entirely.
- `_CallRecorder` — call-recording function object replacing `MagicMock` call tracking.
- `_FakeFeed` — minimal SDK feed stub with `subscribe_symbols = _CallRecorder()`.
- `_FakeResolver` — resolver stub with real `Instrument` objects; provides `resolve()`, `wire_segment_of()`, `assert_resolve_called_once_with()`.
- `mock_resolver` fixture → `fake_resolver` fixture using `_FakeResolver`.
- All `mock_feed = MagicMock()` → `feed = _FakeFeed()`.
- `test_scanner_accepts_resolver_parameter`: `MagicMock()` → `_FakeResolver()`.
- `mock_resolver.resolve.assert_called_once_with(...)` → `fake_resolver.assert_resolve_called_once_with(...)`.
- `mock_resolver.resolve.side_effect = ValueError(...)` path removed — `_FakeResolver` raises `ValueError` for unknown symbols natively.

## Test results

```
13 passed in 1.06s
```

All original assertions preserved — no semantics changed, only mock infrastructure.

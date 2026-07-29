# R4: Make `wire()` Configurable

## Status

✅ Complete — all 947 unit tests pass with zero failures.

## Approach

**Option 2: `Dependencies` dataclass** — added a `Dependencies` dataclass in `scalpr/api/bootstrap.py` with seven optional fields (`risk_gate`, `circuit_breaker`, `oms_repository`, `event_store`, `order_manager`, `order_router`, `strategy_executor`), each defaulting to `None`.

`wire()` gains an optional `deps: Dependencies | None = None` parameter. When `None` (or all fields left at default), the exact same graph is wired as before. Each field, when set to a pre-built instance, short-circuits the corresponding default construction.

## What Changed

**File: `scalpr/api/bootstrap.py`** (lines 59–73 added, line 81 added, lines 113–134 reworked)

- **Added** `Dependencies` dataclass (before `wire()`)
- **Added** `deps` parameter to `wire()` signature
- **Reworked** the constructor body: each component is now resolved as `deps.<field> if deps.<field> is not None else <default>(...)`
- Preserved the `live_orders_enabled` / kill-switch logic and the safety warning — these fire regardless of whether the risk gate is overridden

## Design Decisions

| Decision | Rationale |
|---|---|
| Pre-built instances, not factories | Avoids leaking constructor args from `wire()` internals; caller passes a complete mock or alternative impl |
| Each field resolved independently | No cascading "if A is overridden, skip B" logic — keeps the function linear and predictable |
| Lazy imports unchanged | The `from scalpr...` imports stay inside `wire()` — no import-time coupling |
| Default behavior unchanged | `deps or Dependencies()` when omitted means all fields are `None` → all default constructors fire |

## Result

```python
# Before — no way to override without copy-pasting wire()
ctx = wire(gw, ["RELIANCE"])

# After — partial overrides work while everything else uses defaults
ctx = wire(gw, ["RELIANCE"], deps=Dependencies(risk_gate=MagicMock()))
ctx = wire(gw, ["RELIANCE"], deps=Dependencies(order_router=mock_router))
ctx = wire(gw, ["RELIANCE"], deps=Dependencies(strategy_executor=mock_exec))
```

## Test Results

```
947 passed, 2 warnings in 25.97s
```

No regressions. The existing test suite (test_bootstrap.py, test_kill_switch.py, test_event_store_wiring.py) runs against the same default path.

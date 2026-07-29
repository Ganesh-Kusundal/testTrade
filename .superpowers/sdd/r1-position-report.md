# R1 — Decompose `Position.with_fill()`

## Status

**Complete** — all tests pass with zero behavioural change.

## Methods extracted

From `with_fill` (was ~70 lines, now 36 lines of orchestrator):

| Method | Kind | Responsibility |
|---|---|---|
| `_validate_fill_params` | instance method | Type-checks `quantity` (int) and `price` (Decimal) |
| `_compute_new_quantity` | `@staticmethod` | `old_qty + delta` — separate even though trivial, names intent |
| `_compute_avg_realised_and_state` | `@staticmethod` | Core branching: fresh position, adding, reducing, reversing, closing. Returns `(new_avg, new_realised, new_state)` |
| `_resolve_side_and_state` | `@staticmethod` | Maps `new_qty` to `PositionSide` and upgrades state from FLAT/REDUCING to OPEN when unchanged |
| `_compute_unrealised_pnl` | `@staticmethod` | Long/short/zero unrealised PnL calculation at fill price |

## Orchestrator flow (lines 65–100)

```
validate → compute_new_qty → compute_avg_realised_and_state → resolve_side_and_state → compute_unrealised_pnl → replace
```

Each method returns a single responsibility; the orchestrator only wires results into `dataclasses.replace()`.

## Test results

```
pytest tests/unit/domain/ -q --tb=short  →  34 passed
pytest tests/ -q --tb=short -k position  →  34 passed (unit + contract)
```

## Files changed

- `scalpr/domain/position.py` — 151 → 188 lines (added 5 private/static methods, shorter orchestrator)

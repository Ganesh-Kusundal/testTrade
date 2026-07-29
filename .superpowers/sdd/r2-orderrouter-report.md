# R2 — OrderRouter Dhan-Specific Import Removal

## Status: ✅ NO-OP (already fixed)

## What was changed

**Nothing.** The `Dhan` / `IBrokerGateway` → `ITradingPort` migration for
`order_router.py` was already completed in commit `99667b8`
("fix(brokers): TOTP cooldown death spiral + dead code removal + simplification").

### Evidence

| Check                          | Result |
|--------------------------------|--------|
| `grep Dhan scalpr/execution/order_router.py` | 0 matches |
| `grep Dhan tests/unit/execution/`           | 0 matches |
| Import on line 9              | `from scalpr.brokers.broker_port import ITradingPort` |
| `__init__` type hint          | `gateway: ITradingPort` (line 52) |
| Diff from prior commit        | `IBrokerGateway` → `ITradingPort` already applied |

The `__init__` at lines 50–57 already uses `ITradingPort` — no Dhan-specific
classes (`DhanOrderRequest`, `DhanGateway`, etc.) appear anywhere in the file.

## Test results

```
$ pytest tests/unit/execution/ -q --tb=short
10 passed in 1.42s
```

All 10 execution unit tests pass. No regressions.

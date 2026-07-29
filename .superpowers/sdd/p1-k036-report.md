# P1-K036 — Delete dead `TokenRefreshScheduler` class

**Status:** ✅ Done

## What was deleted

| Item | Location | Lines removed |
|------|----------|--------------|
| `TokenRefreshScheduler` class | `scalpr/brokers/dhan/_token_lifecycle.py` | 68 (lines 68–138) |
| `import threading` (unused dep) | same file | 1 (line 11) |
| Module docstring mentioning scheduler | same file | rewritten (shorter, broadcast-only) |
| Test file | `tests/unit/brokers/dhan/test_token_scheduler.py` | 84 lines (entire file) |

## Import verification

`grep TokenRefreshScheduler scalpr/ --include="*.py"` — **zero matches** in production code. Only docs/plans referenced it.

## Test results

```
pytest tests/unit/brokers/dhan/test_token_broadcast.py -q --tb=short
8 passed in 0.57s

pytest tests/unit/brokers/dhan/ -q --tb=short --timeout=30
417 passed in 1.61s
```

All 417 tests pass with no regressions.

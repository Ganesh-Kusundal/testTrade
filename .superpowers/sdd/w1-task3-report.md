# Task 1.3 — Remove `PartialFill` dead code

**Status:** DONE

## Files referencing `PartialFill` and actions taken

| File | Action |
|------|--------|
| `scalpr/domain/fill.py` (line 30-45) | **Removed** the `PartialFill` dataclass definition |
| `scalpr/domain/__init__.py` (line 25) | **Removed** `PartialFill` from the import statement |
| `scalpr/domain/__init__.py` (line 56) | **Removed** `PartialFill` from `__all__` |
| `tests/` | **No references found** — no test changes needed |
| `docs/` or `.md` files | Left untouched (plan docs, not code) |

## Test results

```
947 passed, 2 warnings in 23.47s
```

No regressions. `PartialFill` was truly dead code.

# P2-K038 — Remove unnecessary static wrapper methods from `http_client.py`

## Status: ✅ Complete

## Changes made

**File:** `scalpr/brokers/dhan/http_client.py`

| Change | Description |
|--------|-------------|
| Removed `_bucket_for()` static method (was lines 148–151) | Delegated to `bucket_for()` from `_http_common` — called exactly once in `_request()` |
| Removed `_backoff_delay()` static method (was lines 247–250) | Delegated to `backoff_delay()` from `_http_common` — never called anywhere in the codebase |
| `_request()` line 159: `self._bucket_for(endpoint)` → `bucket_for(endpoint)` | Direct call to the already-imported function |

Both `bucket_for` and `backoff_delay` were already imported at the top of the file (line 20–21 of the import block from `_http_common`). No other callers referenced either static method.

## Test results

```
417 passed in 1.43s
```

All existing tests pass with zero regressions.

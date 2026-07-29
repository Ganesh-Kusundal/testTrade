# P2-K039: Module merge report

## Merge 1: `_http_common.py` → `http_client.py`

**Moved** (83 lines → inlined at `http_client.py:39-120`):
- Constants: `_ENDPOINT_BUCKETS`, `_DEFAULT_BUCKET`, `_MAX_RETRIES`, `_BASE_DELAY_MS`, `_MAX_DELAY_MS`, `_ORDERS_ACQUIRE_TIMEOUT_S`
- Functions: `bucket_for()`, `backoff_delay()`, `build_url()`, `classify_response()`

**Changed in `http_client.py`**: Removed `from scalpr.brokers.dhan._http_common import (...)`

**Deleted**: `scalpr/brokers/dhan/_http_common.py`

## Merge 2: `TokenBroadcast` → `auth.py`

**Moved** (`TokenBroadcast` class → inlined at `auth.py:36-96`):
- Full class with `register`, `unregister`, `unregister_all`, `broadcast`, `receiver_count`

**Changed in `auth.py`**:
- Removed `from scalpr.brokers.dhan._token_lifecycle import TokenBroadcast` (was line 23)
- Added `from collections.abc import Callable` (needed by `TokenBroadcast`)

**Deleted**: `scalpr/brokers/dhan/_token_lifecycle.py`

## Test import updated

`tests/unit/brokers/dhan/test_token_broadcast.py:7`:
- `from scalpr.brokers.dhan._token_lifecycle import TokenBroadcast` → `from scalpr.brokers.dhan.auth import TokenBroadcast`

No other test imports referenced the deleted modules.

## Test results

```
pytest tests/unit/brokers/dhan/ -q --tb=short
417 passed in 1.43s
```

All 417 tests pass with zero failures.

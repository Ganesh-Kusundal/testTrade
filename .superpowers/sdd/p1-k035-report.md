# K-035 Report: Remove dead `token_refresh_fn` parameter

**Status**: ✅ Complete — 47/47 tests passing

## Files modified

### 1. `scalpr/brokers/dhan/ws_client.py`
- Removed `token_refresh_fn` parameter from `__init__()` signature (was line 174)
- Removed `self._token_refresh_fn = token_refresh_fn` store (was line 191)
- Removed entire `_maybe_refresh_token()` method (was lines 219–237)
- Removed `self._maybe_refresh_token()` call in `connect()` (was line 257)
- Removed associated docstring entries (was lines 183–185)

### 2. `scalpr/brokers/dhan/ws_manager.py`
- Removed `token_refresh_fn` parameter from `__init__()` signature (was line 114)
- Removed `self._token_refresh_fn = token_refresh_fn` store + comment (was lines 123–124)
- Removed `token_refresh_fn=self._token_refresh_fn` from `DhanWebSocketClient(...)` pass-through in `_ensure_components()` (was line 681)

### 3. `scalpr/brokers/gateway/_streaming.py`
- Removed `token_refresh_fn=self._config.get("token_refresh_fn")` from `DhanWebSocketManager(...)` call in `_init_websocket_manager()` (was line 231)

### 4. `scalpr/api/bootstrap.py`
- Removed `token_refresh_fn=lambda: ensure_fresh_token(force=True),` from `DhanWebSocketManager(...)` call in `_start_trading()` (was line 165)

### 5. `tests/unit/brokers/dhan/test_ws_token_refresh.py`
- **Deleted** — entire file tested removed `_maybe_refresh_token()` plumbing (95 lines, 7 test cases, all failing after removal)

## Test results

```
47 passed in 0.84s
```

All existing WebSocket tests in `test_websocket.py` and `test_ws_subscribe_honest.py` pass unchanged. The deleted test file's 7 cases are no longer applicable (tested dead functionality).

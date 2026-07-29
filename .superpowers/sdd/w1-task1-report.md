# Task 1 Report: Replace `os.environ.get` with `SecretsManager` in `scalpr/api/bootstrap.py`

## Status: DONE

## Changes

### 1. Added import (line 25)
```python
from config.secrets_manager import SecretsManager
```

### 2. Replaced `os.environ.get` calls (lines 133-136)

**Before:**
```python
    feed = DhanWebSocketManager(
        access_token=os.environ.get("DHAN_ACCESS_TOKEN", ""),
        client_id=os.environ.get("DHAN_CLIENT_ID", ""),
```

**After:**
```python
    sm = SecretsManager()
    feed = DhanWebSocketManager(
        access_token=sm.get_dhan_access_token() or "",
        client_id=sm.get_dhan_client_id() or "",
```

### 3. `import os` retained
`os` is still used on lines 88, 113, 208, and 263 (`os.environ.get` for `SCALPR_LIVE_ORDERS`, `SCALPR_WATCHLIST`, `SCALPR_TRADING_ENABLED`, `SCALPR_JWT_SECRET`), so the import was kept.

## Test Results

```
pytest tests/unit/brokers/dhan/ -q --tb=short
426 passed in 1.28s
```

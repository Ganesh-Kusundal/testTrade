# Task 3.2: Decompose `_verify_connection`

**Status:** DONE — 95/95 tests passing

## Summary

Decomposed `_verify_connection` (previously 53 lines, lines 291–362) into four focused methods, retaining the orchestrator pattern.

## Extracted methods and responsibilities

### `_fetch_profile()` — auth-aware profile call
- GET `/profile` with 3-attempt retry loop on `AuthenticationError`
- On 401/TOTP cooldown: calls `ensure_fresh_token(force=True, wait_for_cooldown=True)`, updates client token, retries
- Raises `AuthenticationError` after exhaustion (including `TokenRefreshThrottled`)
- Raises `BrokerError` if HTTP client is unavailable

### `_validate_data_plan(profile)` — data plan check
- Reads `dataPlan` from profile dict; logs warning if not `"active"`
- Does not raise — user may only need order APIs

### `_log_connection_status(profile)` — status logging
- Warns if `dataValidity` is missing
- Logs `dhan_connection_verified` with name, dataPlan, activeSegments, tokenValidity

### `_verify_connection()` — orchestrator (unchanged contract)
```python
def _verify_connection(self) -> None:
    profile = self._fetch_profile()
    self._validate_data_plan(profile)
    self._log_connection_status(profile)
```

## Test results
```
95 passed in 0.94s
```

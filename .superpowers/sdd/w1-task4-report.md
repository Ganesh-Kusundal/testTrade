# Task 1.4 — Fix stale annotation: test_verify_connection_retry.py

## Status: DONE

## What was found

Three checks were performed on the file:

1. **Docstrings/comments reflect current K-027 behavior?** — YES. The module docstring correctly states "401 always forces token regeneration" and "Cooldown waiting is owned by auth.py (ensure_fresh_token with wait_for_cooldown=True)". All class/method docstrings match the implementation.

2. **`TotpRateLimitError` import path correct?** — YES. Still lives at `scalpr/brokers/dhan/_totp_cooldown.py:24` (inherits `TokenRefreshThrottled` from `scalpr/brokers/errors.py`). Import `from scalpr.brokers.dhan._totp_cooldown import TotpRateLimitError` resolves correctly.

3. **`from scalpr.brokers.dhan.exceptions import AuthenticationError` resolves?** — YES. `scalpr/brokers/dhan/exceptions.py` exists and aliases `AuthenticationError = DhanAuthenticationError` at line 66.

**Root cause of "stale" flag:** The kanban manifest's `purpose` string was wrong:
```
Old: "Verify-retry policy: same-token retry on 401, mint only when stale"
```
This contradicts the actual K-027 behavior where `ensure_fresh_token(force=True, wait_for_cooldown=True)` is called on *every* 401 — the token is always regenerated, never reused.

## What was changed

Only the kanban annotation (not the test file itself):
- Ran `kanban file set-purpose` to update the description to: `"Verify-retry policy: force mint on each 401 with wait_for_cooldown"`
- This reset `annotated_hash` to match current `hash`, clearing the stale flag.

## Test results

```
pytest tests/unit/brokers/dhan/test_verify_connection_retry.py -v --tb=short
→ 6 passed in 0.58s (all green)
```

## Kanban stale check

```
kanban stale
→ No stale annotations.
```

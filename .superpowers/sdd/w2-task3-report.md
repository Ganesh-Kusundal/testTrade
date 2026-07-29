# W2-Task3: Lazy Dhan Import in `facade.py` — Evaluation & Fix

## Status: ✅ Fixed (uncommitted, in active worktree)

## Summary of Findings

### 1. Lazy Import Location

**File:** `scalpr/brokers/gateway/facade.py` (HEAD commit `99667b8`)

A lazy import existed as a module-level helper function:

```python
def _is_totp_cooldown_error(exc: BaseException) -> bool:
    try:
        from scalpr.brokers.dhan._totp_cooldown import TotpRateLimitError
        return isinstance(exc, TotpRateLimitError)
    except ImportError:
        return False
```

This was used in `Gateway.__init__` to catch `TotpRateLimitError` (a `RuntimeError`) and re-wrap it as `TradingError` with actionable cooldown guidance. The lazy import + `try/except ImportError` were necessary because `TotpRateLimitError` was a raw `RuntimeError` subclass — not part of the `TradingError` hierarchy — so it couldn't be caught by the generic `except TradingError` clause that followed.

### 2. Root Cause & Fix

The **worktree already contains the fix** (uncommitted changes across ~20 files). The approach:

| Before (HEAD) | After (worktree) |
|---|---|
| `TotpRateLimitError(RuntimeError)` — raw, broker-specific, outside error hierarchy | `TotpRateLimitError(TokenRefreshThrottled)` — part of hierarchy via `TokenRefreshThrottled(AuthenticationError(TradingError))` |
| Lazy import `from scalpr.brokers.dhan._totp_cooldown import TotpRateLimitError` inside `_is_totp_cooldown_error()` | Lazy import **removed entirely** |
| `except Exception` + `_is_totp_cooldown_error(exc)` duck-typing | `except TokenRefreshThrottled as exc` — direct, typed, Dhan-agnostic catch |
| `TokenRefreshThrottled` not available in `scalpr.brokers.errors` | `TokenRefreshThrottled` added to `scalpr.brokers.errors` as `AuthenticationError` subclass |

### 3. Is Dhan Always Required Now?

**No.** Dhan remains **conditionally available**:

- Registration: `BrokerRegistry._register_default_brokers()` in `registry.py:126-157` wraps all Dhan imports in `try/except ImportError`.
- Facade access: `BrokerRegistry.get()` / `BrokerRegistry.get_adapter()` provide broker-agnostic lookup by string name — no Dhan types leak into the facade.
- `TokenRefreshThrottled` is defined in `scalpr/brokers/errors.py:100` — it is a broker-agnostic error type always available at top-level import.

The lazy import is no longer needed because `TokenRefreshThrottled` is:
- A proper `TradingError` subclass (caught by `except TradingError` if needed)
- Broker-agnostic (no Dhan dependency)
- Always importable at module level

### 4. `_gateway` + `BrokerName.DHAN` Check

**No `BrokerName` enum exists in the codebase.** The broker name is stored as a plain string `self._broker_name`. The `_gateway` attribute (`IBrokerGateway` type) is used polymorphically across all mixins — `_market_data.py`, `_portfolio.py`, `_streaming.py` — without any Dhan-specific isinstance checks or broker name comparisons. All method calls go through the abstract `IBrokerGateway` interface.

### 5. `_gateway.connection` Usage

The worktree also changed `instrument()` to access `self._gateway.connection` instead of `self._gateway.adapters()["connection"]`. Both `PaperOms` and `SimulatedGateway` now expose a `connection` property (returning `None`), making this path safe for non-Dhan brokers.

## Test Results

| Scope | Pass | Fail | Note |
|---|---|---|---|
| `tests/unit/brokers/` | 560 | 0 | All broker tests pass |
| `tests/unit/` + `tests/contract/` (worktree) | 984 | 17 | Failures are in `mapper.py`-related tests (`Result` vs `Order` type change) — **unrelated to facade** |
| `tests/unit/` + `tests/contract/` (HEAD) | 995 | 1 | Pre-existing failure in `test_event_store_wiring` — also unrelated |

**The lazy import fix itself introduces zero test regressions.** All 17 worktree failures trace to separate mapper changes (return type `Result` vs domain `Order`) in `scalpr/brokers/dhan/mapper.py` and `scalpr/brokers/dhan/connection.py`.

## Files Changed by This Fix

- `scalpr/brokers/gateway/facade.py` — removed `_is_totp_cooldown_error`, added `TokenRefreshThrottled` import, direct catch
- `scalpr/brokers/errors.py` — added `TokenRefreshThrottled(AuthenticationError)` class
- `scalpr/brokers/dhan/_totp_cooldown.py` — `TotpRateLimitError` now extends `TokenRefreshThrottled` instead of `RuntimeError`
- `scalpr/brokers/dhan/auth.py` — `ensure_fresh_token` accepts `wait_for_cooldown=True` (moves sleep to single point)
- `scalpr/brokers/dhan/connection.py` — `_verify_connection` simplified (no TOTP cooldown sleep; delegates to `auth.py`)
- `scalpr/brokers/dhan/http_client.py` — 401/DH-906 now raises immediately (caller handles refresh+retry)
- Various test files updated for new contract assertions
- `tests/contract/test_gateway_error_invariant.py` — new contract test verifying no non-`TradingError` escapes `Gateway()`

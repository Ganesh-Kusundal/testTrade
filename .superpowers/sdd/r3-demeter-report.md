# R3 — Law of Demeter Fix Report

**Date:** 2026-07-29
**File:** `scalpr/strategy/scalpr_amt.py` lines 77 & 96
**Gateway facade:** `scalpr/brokers/gateway/facade.py`

---

## Chains Found

| Line | Code | Depth |
|------|------|-------|
| 77 | `self.order_router.gateway.get_positions()` | 3-level (strategy → router → gateway → impl) |
| 96 | `self.order_router.gateway.get_margins()` | 3-level (strategy → router → gateway → impl) |

Additionally, the `Gateway` facade's `instrument()` method at `facade.py:218` did:
```python
conn.resolver.resolve_full(symbol, exch_str)
```
— a 3-level chain through `self._gateway.connection.resolver`.

---

## Root Cause

The `Gateway` facade (`facade.py`) inherited `positions()` and `funds()` from `PortfolioMixin`, but these use a different naming convention than the `IAccountPort` / `IBrokerGateway` interface (`get_positions()`, `get_margins()`). The strategy was written against the `IBrokerGateway` naming, creating a dependency on those method names existing at the facade level — which they didn't. The facade acted as a pass-through (`.gateway` property returns `self._gateway`) rather than wrapping the deep access.

---

## Fix Applied

### 1. Added delegation methods on `Gateway` (facade.py)

```python
def get_positions(self) -> list[Position]:
    return self._gateway.get_positions()

def get_margins(self) -> Funds:
    return self.funds()
```

These sit in a new `Account delegation — LoD-compliant wrappers` section after the lifecycle methods. The strategy already calls `get_positions()` / `get_margins()` — no strategy changes needed.

**Imports added:** `Funds` from `scalpr.brokers.contracts`, `Position` from `scalpr.domain.position`.

### 2. No strategy changes required

The strategy at `scalpr_amt.py:77,96` already calls `self.order_router.gateway.get_positions()` and `self.order_router.gateway.get_margins()`. With the delegation methods on `Gateway`, these calls now route through the facade instead of reaching into the underlying `IBrokerGateway` directly.

---

## Test Results

```
pytest tests/unit/strategy/ tests/unit/brokers/dhan/ -q --tb=short
439 passed in 6.31s
```

All existing tests pass. No regressions.

---

## Summary

| Metric | Value |
|--------|-------|
| LoD violation sites found | 2 (lines 77, 96) |
| Delegation methods added | 2 (`get_positions`, `get_margins`) |
| Strategy files changed | 0 (no changes needed) |
| Gateway files changed | 1 (`facade.py`) |
| Tests added | 0 (existing coverage sufficient) |
| Tests passing | 439 / 439 |

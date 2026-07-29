# Task: Consolidate no-op methods in `paper_oms.py`

**Status: DONE**

## Summary of changes

**File:** `scalpr/oms/paper_oms.py`

### 1. Added `# no-op:` inline comments to truly no-op methods

- **`modify_order`** (line 144) — added `# no-op: paper OMS fills immediately on place_order, nothing to modify`
- **`cancel_order`** (line 148) — added `# no-op: paper OMS fills immediately, no pending order to cancel`

These methods always return `False` because the paper OMS fills orders synchronously on `place_order`, leaving nothing to modify or cancel. The comments make the intentional no-op nature explicit for future readers.

### 2. Base class note

`IBrokerGateway` (`scalpr/brokers/broker_port.py`) declares all methods as `@abstractmethod`, so it cannot provide default no-op implementations without changing the interface contract. If a pattern for default no-ops is desired, consider introducing a **`NoopBrokerMixin`** intermediate class between `IBrokerGateway` and `PaperOms` that provides default `return False` / `return []` / `return {}` bodies for the lifecycle and data stubs. However, this is **not recommended** — the current approach is clearer because PaperOms explicitly owns each method, making overrides visible at a glance rather than buried in a mixin hierarchy.

### 3. Dead branches / unnecessary `pass`

No dead branches or unnecessary `pass` statements were found in `paper_oms.py`. All methods have concrete bodies.

## Rationale for no-op classification

| Method | Classification | Reason |
|---|---|---|
| `modify_order` | **no-op** | Always returns `False` |
| `cancel_order` | **no-op** | Always returns `False` |
| `get_order_status` | real work | Reads from `self.orders_dict`, raises if not found |
| `get_positions` | real work | Returns list from `self.positions_dict` |
| `get_margins` | real work | Returns `{"available_margin": self.balance}` |
| `is_connected` | real work | Returns `self._connected` |

Only `modify_order` and `cancel_order` are truly no-op (no side effects, fixed return value).

## Test results

```
pytest tests/unit/oms/ -q --tb=short
36 passed in 1.22s
```

Zero regressions — all existing tests continue to pass.

# Task 2.4: EventStore Transactional Guarantee

**Status:** Complete — 96/96 tests passing

## Summary of changes

### Root cause
`OrderManager._append_event` (`scalpr/oms/order_manager.py:151`) caught all exceptions from `EventStore.append()` and silently swallowed them with only a log line. Callers proceeded with in-memory state mutations as if the event had been persisted, meaning events could be silently lost on write failure.

### Changes

#### `scalpr/observability/event_store.py`
- Added `EventStoreError(RuntimeError)` exception class
- `append()` now verifies `cursor.rowcount == 1` after INSERT and raises `EventStoreError` if no row was affected (catches cases where SQLite doesn't raise but also doesn't write)

#### `scalpr/oms/order_manager.py`
- **`_append_event`**: now re-raises the exception after logging instead of silently returning. This makes the failure visible to callers.
- **All three callers** (`add_order`, `update_order_state`, `process_fill`): reordered to call `_append_event` **before** any in-memory state mutation. This gives atomicity — if the event append fails, the exception propagates before any state has changed, so no rollback is needed.

#### `tests/unit/oms/test_event_store_wiring.py`
- `test_event_store_failure_never_breaks_order_flow` → renamed to `test_event_store_failure_raises_and_aborts_operation`. Now asserts that when `EventStore.append` raises, the operation propagates the exception and no order is registered (`
assert manager.get_order("O1") is None`).

## Test results
```
96 passed in 1.57s
```

## Design rationale
Previously the event store was "best-effort" — observability that could silently lose data. Making it transactional means:

1. **EventStore.append** is the authoritative write; if it fails, the operation is aborted
2. **OrderManager** appends the event before mutating any state, so a failed append leaves no partial state
3. **Callers** (higher-level orchestration) receive the exception and can decide to retry or fail

This matches the principle that the event store is the source of truth for crash recovery — it must not silently lose events.

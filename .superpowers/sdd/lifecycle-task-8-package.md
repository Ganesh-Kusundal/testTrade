# Task 8 review package — OrderWatcher

## Independent verification

| Check | Expected | Actual | Pass? |
|-------|----------|--------|-------|
| HEAD | c7fc087 | c7fc087 | YES |
| Tests | 1713 passed | 1713 passed | YES |
| lint-imports | 7 kept, 0 broken | 7 kept, 0 broken | YES |
| Files staged | 3 new | _order_watcher.py, _mapper_orders.py, test_order_watcher.py | YES |

## Index tree diff

Base tree (post-Task 7): f32c34205a1c3eb73a5b4a7b32a8245a9b1b7cb9
New tree (post-Task 8): c55e526515fa3046aea184546749da30bcb97e72

## Spec compliance checklist

1. **TRANSIT added to _DHAN_STATUS_TO_STATE** — line 52 of _mapper_orders.py: `"TRANSIT": OrderState.PENDING`
2. **transaction_type_to_side added** — inverse of `transaction_type_from_side`, raises `InvalidValueError` on unknown
3. **order_book_entry_to_fill added** — takes `entry`, `local_order_id`, `delta_quantity`; returns `Fill` with `Decimal` price
4. **OrderWatcher created** — `__init__(http, bus, clock, registry)`, method `poll_once() -> None`
5. **Delta accounting** — `_seen_filled: dict[str, int]` tracks cumulative; only positive deltas published
6. **Terminal state dedup** — `_terminal: set[str]` prevents re-publishing REJECTED/CANCELLED/EXPIRED/FILLED
7. **Unmapped orders ignored** — `local_id()` returns None → skip
8. **HTTP failure swallowed** — try/except around `http.get()`, logged and returns
9. **Unknown status skipped** — `order_status_from_dhan` exception caught, logged, skipped
10. **10 tests across 3 classes** — TestOrderWatcherFills (4), TestOrderWatcherTerminalStates (3), TestOrderWatcherRobustness (3)

## Context for reviewer

- This is the final task of an 8-task plan making the Dhan adapter's order lifecycle tell the truth.
- Tasks 1-7 are already approved. This review covers ONLY the 3 files in the Task 8 diff.
- The `datetime.now(timezone.utc)` in `order_book_entry_to_fill` is the plan's verbatim code. The `Clock` is used for event timestamps (the important ones on the bus); the `Fill.timestamp` records observation time.
- `threading.Lock` in `OrderRegistry` (Task 3, already approved) is justified by multi-threaded codebase (_ws.py WebSocket thread, message_bus.py, _http.py, _auth.py, _resolver.py all use threading).
- The brief's `OrderWatcher` imports `OrderFilled`, `OrderRejected`, `OrderCancelled` from `execution_engine.py` — these were added/modified by Tasks 4-7.

## Files to review

1. `scalpr/adapters/dhan/_order_watcher.py` (NEW, 136 lines)
2. `scalpr/adapters/dhan/_mapper_orders.py` (MODIFIED, +39 lines)
3. `tests/unit/adapters/dhan/test_order_watcher.py` (NEW, 132 lines)

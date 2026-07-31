# Task 1: Fix Event Topic Routing (K-153)

## Context

The `ExecutionEngine` subscribes to generic event topics (`exec.event.fill`, `exec.event.accepted`, `exec.event.rejected`, `exec.event.cancelled`) but `DhanClient._on_submit()` publishes on broker-specific topics (`exec.event.filled.dhan`, `exec.event.rejected.dhan`, `exec.event.cancelled.dhan`). This mismatch means the engine's order state machine **never receives events from the Dhan adapter** — orders placed via the bus sit in PENDING state forever.

Additionally, `_on_submit` fabricates a `Fill` from the order placement response (which only contains `orderId`), creating phantom fills. Order placement should publish `OrderAccepted` (order acknowledged by broker), not `OrderFilled`.

## Requirements

1. `ExecutionEngine.start()` must subscribe to broker-specific topics:
   - `exec.event.accepted.dhan` → `_on_accepted`
   - `exec.event.filled.dhan` → `_on_fill`
   - `exec.event.rejected.dhan` → `_on_rejected`
   - `exec.event.cancelled.dhan` → `_on_cancelled`

2. `DhanClient._on_submit()` must publish `exec.event.accepted.dhan` with `OrderAccepted` (not `OrderFilled` with a fabricated `Fill`)

3. `OrderAccepted` dataclass must exist in `scalpr/engine/execution_engine.py`

4. `_on_accepted` handler must transition order from PENDING to OPEN

## Files to Modify

- `scalpr/engine/execution_engine.py` — fix subscriptions in `start()`, add `OrderAccepted` dataclass, add `_on_accepted` handler
- `scalpr/adapters/dhan/client.py` — fix `_on_submit` to publish `OrderAccepted` instead of `OrderFilled`, add `OrderAccepted` import

## Files to Create

- `tests/unit/engine/test_execution_engine.py` — add test for broker-specific topic routing and OrderAccepted flow

## Testing

Run: `.venv/bin/python -m pytest tests/unit/engine/test_execution_engine.py tests/unit/adapters/dhan/test_client.py -v`
Expected: All pass, 0 failures

## Constraints

- TDD: Write failing test first, then implement
- No mocking — use RecordingBus and real ExecutionEngine
- Keep existing tests passing
- Commit after verification

# Task 5 brief — Cancel addresses the broker's id and announces failure

## Global Constraints (verbatim from the plan)

- Money is `Decimal`. Never `float` in a domain object. `Fill.price` and `Order.price` raise `TypeError` on non-`Decimal`.
- `Order`, `Fill`, and all `exec.*` payloads are `@dataclass(frozen=True)`. Mutation means `dataclasses.replace`.
- Time comes from the injected `Clock` (`clock.timestamp()` / `clock.utc_now()`). Never call `datetime.now()` in adapter or engine code paths added by this plan.
- Topic convention is `{domain}.{verb}.{broker}` for broker-directed and broker-emitted messages: commands `exec.command.<verb>.dhan`, events `exec.event.<verb>.dhan`. Engine-internal domain events stay unsuffixed (`domain.order.placed`, `domain.fill.received`).
- Never import a private module across a package boundary. `scalpr.adapters.dhan._http` is internal to the Dhan adapter.
- Production modules outside `scalpr/adapters/dhan/` must not import `DhanClient` concretely — depend on a Protocol from `scalpr.domain.contracts`.
- Staging discipline from `AGENTS.md`: `git add` only. **Never `git commit`** unless the user explicitly asks. Every staged state must pass `pytest tests/unit/ tests/contract/` with 0 failures.
- After any code change, re-run `python3 .qoder/skills/kanban.cli/scripts/kanban.py scan`.

## Task 5 (verbatim from the plan, lines 672-810)

R2 and half of R4. `DELETE /orders/{msg.order_id}` currently sends the local UUID, and a failure is swallowed with no event — so the engine, which has already marked the order CANCELLED, never learns the truth.

**Files:**
- Modify: `scalpr/engine/execution_engine.py` (add `OrderCancelRejected`)
- Modify: `scalpr/adapters/dhan/client.py` (`_on_cancel`)
- Modify: `tests/unit/adapters/dhan/test_client.py`

**Interfaces:**
- Consumes: `OrderRegistry` (Task 3), the registry populated by `_on_submit` (Task 4).
- Produces: `scalpr.engine.execution_engine.OrderCancelRejected(order_id: str, reason: str, timestamp: datetime)`, published on `exec.event.cancel_rejected.dhan`. Consumed by the engine in Task 7.

### Step 1: Fix the two existing tests that encode the bug

`TestDhanClientOnCancel.setUp` (line 309) never registers a broker id, and two of its tests assert the buggy behaviour:

- `test_sends_delete_request` (line 336) asserts `delete("/orders/ord-1")` — the *local* id.
- `test_publishes_cancelled_event_on_success` (line 340) expects a cancellation the broker never confirmed.

Do not weaken the new assertions to keep these green. Seed the mapping in `setUp` instead, immediately after line 330 (`self.client = DhanClient(...)`):

```python
        self.client.registry.register("ord-1", "ORD123456")
```

and update line 338 to assert the broker's id:

```python
        self.mock_http_client.delete.assert_called_once_with("/orders/ORD123456")
```

### Step 2: Write the failing tests

Append to `class TestDhanClientOnCancel`:

```python
    def test_cancel_of_unmapped_order_publishes_cancel_rejected(self):
        """No mapping means we cannot address the broker. Say so loudly instead
        of letting the engine believe the order is cancelled."""
        self.client.registry.forget("ord-1")

        self.client._on_cancel(self.msg)

        self.mock_http_client.delete.assert_not_called()
        events = self.bus.filter("exec.event.cancel_rejected.dhan")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].payload.order_id, "ord-1")
        self.assertIn("unknown", events[0].payload.reason.lower())

    def test_cancel_http_failure_publishes_cancel_rejected(self):
        """A broker-side cancel failure must reach the engine — the local book
        must not silently diverge from a still-live broker order."""
        self.mock_http_client.delete.side_effect = RuntimeError("DH-906 order not found")

        self.client._on_cancel(self.msg)

        self.assertEqual(len(self.bus.filter("exec.event.cancelled.dhan")), 0)
        events = self.bus.filter("exec.event.cancel_rejected.dhan")
        self.assertEqual(len(events), 1)
        self.assertIn("DH-906", events[0].payload.reason)
```

Add `OrderCancelRejected` to that file's existing `from scalpr.engine.execution_engine import (...)` block (line 21).

### Step 3: Run to verify they fail

```bash
.venv/bin/python -m pytest tests/unit/adapters/dhan/test_client.py -q -k TestDhanClientOnCancel
```

Expected: `test_sends_delete_request` FAILS (still sends the local id), and the two new tests FAIL on `ImportError: cannot import name 'OrderCancelRejected'`.

### Step 4: Add the payload

In `scalpr/engine/execution_engine.py`, add after `OrderCancelled`:

```python
@dataclasses.dataclass(frozen=True)
class OrderCancelRejected:
    order_id: str
    reason: str
    timestamp: datetime
```

### Step 5: Rewrite `_on_cancel`

In `scalpr/adapters/dhan/client.py`, add `OrderCancelRejected` to the existing `from scalpr.engine.execution_engine import (...)` block, then replace `_on_cancel` (currently `client.py:230-242`) with:

```python
    def _on_cancel(self, msg: CancelOrder) -> None:
        broker_order_id = self._registry.broker_id(msg.order_id)
        if broker_order_id is None:
            logger.error("cancel_unmapped: order_id=%s", msg.order_id)
            self._bus.publish(
                "exec.event.cancel_rejected.dhan",
                OrderCancelRejected(
                    order_id=msg.order_id,
                    reason=f"unknown broker order id for {msg.order_id}",
                    timestamp=self._clock.timestamp(),
                ),
            )
            return
        try:
            self._http_client.delete(f"/orders/{broker_order_id}")
        except Exception as exc:
            logger.error("cancel_failed: order_id=%s error=%s", msg.order_id, exc)
            self._bus.publish(
                "exec.event.cancel_rejected.dhan",
                OrderCancelRejected(
                    order_id=msg.order_id,
                    reason=str(exc),
                    timestamp=self._clock.timestamp(),
                ),
            )
            return
        self._bus.publish(
            "exec.event.cancelled.dhan",
            OrderCancelled(
                order_id=msg.order_id,
                timestamp=self._clock.timestamp(),
            ),
        )
```

Note the event carries the **local** `order_id` — the engine's cache is keyed locally. The broker id is an adapter-internal concern.

### Step 6: Run to verify they pass

```bash
.venv/bin/python -m pytest tests/unit/adapters/dhan/test_client.py -q
```

Expected: all pass.

### Step 7: Stage

```bash
git add scalpr/engine/execution_engine.py scalpr/adapters/dhan/client.py tests/unit/adapters/dhan/test_client.py
```

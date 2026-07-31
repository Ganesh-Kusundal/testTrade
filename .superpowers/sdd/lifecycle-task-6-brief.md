# Task 6 brief — Modify addresses the broker's id and always terminates

## Global Constraints (verbatim from the plan)

- Money is `Decimal`. Never `float` in a domain object. `Fill.price` and `Order.price` raise `TypeError` on non-`Decimal`.
- `Order`, `Fill`, and all `exec.*` payloads are `@dataclass(frozen=True)`. Mutation means `dataclasses.replace`.
- Time comes from the injected `Clock` (`clock.timestamp()` / `clock.utc_now()`). Never call `datetime.now()` in adapter or engine code paths added by this plan.
- Topic convention is `{domain}.{verb}.{broker}` for broker-directed and broker-emitted messages: commands `exec.command.<verb>.dhan`, events `exec.event.<verb>.dhan`. Engine-internal domain events stay unsuffixed (`domain.order.placed`, `domain.fill.received`).
- Never import a private module across a package boundary. `scalpr.adapters.dhan._http` is internal to the Dhan adapter.
- Production modules outside `scalpr/adapters/dhan/` must not import `DhanClient` concretely — depend on a Protocol from `scalpr.domain.contracts`.
- Staging discipline from `AGENTS.md`: `git add` only. **Never `git commit`** unless the user explicitly asks. Every staged state must pass `pytest tests/unit/ tests/contract/` with 0 failures.
- After any code change, re-run `python3 .qoder/skills/kanban.cli/scripts/kanban.py scan`.

## Task 6 (verbatim from the plan, lines 813-957)

The other half of R2/R4. `_on_modify` currently sends the local UUID and publishes **nothing at all** — not on success, not on failure. The engine has no way to know a modify landed.

**Files:**
- Modify: `scalpr/engine/execution_engine.py` (add `OrderModified`, `OrderModifyRejected`)
- Modify: `scalpr/adapters/dhan/client.py` (`_on_modify`)
- Modify: `tests/unit/adapters/dhan/test_client.py`

**Interfaces:**
- Consumes: `OrderRegistry` (Task 3), registry populated by `_on_submit` (Task 4).
- Produces: `OrderModified(order_id: str, updates: dict, timestamp: datetime)` on `exec.event.modified.dhan`, and `OrderModifyRejected(order_id: str, reason: str, timestamp: datetime)` on `exec.event.modify_rejected.dhan`. Both consumed by the engine in Task 7.

### Step 1: Fix the existing test that encodes the bug

`TestDhanClientOnModify.setUp` never registers a broker id, and `test_sends_put_request` asserts `put("/orders/ord-1", data={"quantity": 15})` — the *local* id. Seed the mapping in `setUp`, immediately after `self.client = DhanClient(...)`:

```python
        self.client.registry.register("ord-1", "ORD123456")
```

and update the assertion to the broker's id:

```python
        self.mock_http_client.put.assert_called_once_with(
            "/orders/ORD123456", data={"quantity": 15},
        )
```

### Step 2: Write the failing tests

Append to `class TestDhanClientOnModify` in `tests/unit/adapters/dhan/test_client.py`:

```python
    def test_modify_uses_broker_order_id_and_confirms(self):
        self.client._on_modify(self.msg)

        self.mock_http_client.put.assert_called_once_with(
            "/orders/ORD123456", data={"quantity": 15},
        )
        events = self.bus.filter("exec.event.modified.dhan")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].payload.order_id, "ord-1")
        self.assertEqual(events[0].payload.updates, {"quantity": 15})

    def test_modify_of_unmapped_order_publishes_modify_rejected(self):
        """Without a mapping the broker cannot be addressed. Announce it rather
        than leaving the engine to assume the modify landed."""
        self.client.registry.forget("ord-1")

        self.client._on_modify(self.msg)

        self.mock_http_client.put.assert_not_called()
        events = self.bus.filter("exec.event.modify_rejected.dhan")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].payload.order_id, "ord-1")
        self.assertIn("unknown", events[0].payload.reason.lower())

    def test_modify_http_failure_publishes_modify_rejected(self):
        self.mock_http_client.put.side_effect = RuntimeError("DH-905 invalid price")

        self.client._on_modify(self.msg)

        self.assertEqual(len(self.bus.filter("exec.event.modified.dhan")), 0)
        events = self.bus.filter("exec.event.modify_rejected.dhan")
        self.assertEqual(len(events), 1)
        self.assertIn("DH-905", events[0].payload.reason)
```

The existing `test_handles_error_gracefully` still holds — `_on_modify` must not raise — but it now also gets a terminating event, which the new test asserts.

### Step 3: Run to verify they fail

```bash
.venv/bin/python -m pytest tests/unit/adapters/dhan/test_client.py -q -k modify
```

Expected: FAIL — `ImportError: cannot import name 'OrderModified'`.

### Step 4: Add the payloads

In `scalpr/engine/execution_engine.py`, add after `OrderCancelRejected`:

```python
@dataclasses.dataclass(frozen=True)
class OrderModified:
    order_id: str
    updates: dict
    timestamp: datetime


@dataclasses.dataclass(frozen=True)
class OrderModifyRejected:
    order_id: str
    reason: str
    timestamp: datetime
```

### Step 5: Rewrite `_on_modify`

Add `OrderModified` and `OrderModifyRejected` to the `from scalpr.engine.execution_engine import (...)` block in `client.py`, then replace `_on_modify` (currently `client.py:265-269`) with:

```python
    def _on_modify(self, msg: ModifyOrder) -> None:
        broker_order_id = self._registry.broker_id(msg.order_id)
        if broker_order_id is None:
            logger.error("modify_unmapped: order_id=%s", msg.order_id)
            self._bus.publish(
                "exec.event.modify_rejected.dhan",
                OrderModifyRejected(
                    order_id=msg.order_id,
                    reason=f"unknown broker order id for {msg.order_id}",
                    timestamp=self._clock.timestamp(),
                ),
            )
            return
        try:
            self._http_client.put(f"/orders/{broker_order_id}", data=msg.updates)
        except Exception as exc:
            logger.error("modify_failed: order_id=%s error=%s", msg.order_id, exc)
            self._bus.publish(
                "exec.event.modify_rejected.dhan",
                OrderModifyRejected(
                    order_id=msg.order_id,
                    reason=str(exc),
                    timestamp=self._clock.timestamp(),
                ),
            )
            return
        self._bus.publish(
            "exec.event.modified.dhan",
            OrderModified(
                order_id=msg.order_id,
                updates=dict(msg.updates),
                timestamp=self._clock.timestamp(),
            ),
        )
```

### Step 6: Run and stage

```bash
.venv/bin/python -m pytest tests/unit/ tests/contract/ -q
git add scalpr/engine/execution_engine.py scalpr/adapters/dhan/client.py tests/unit/adapters/dhan/test_client.py
```

Expected: all pass (expect `1696 passed` — 1693 + 3 new), including the amended `test_sends_put_request`.

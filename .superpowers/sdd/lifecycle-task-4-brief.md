# Task 4 brief — `_on_submit` captures the broker order id

## Global Constraints (verbatim from the plan)

- Money is `Decimal`. Never `float` in a domain object. `Fill.price` and `Order.price` raise `TypeError` on non-`Decimal`.
- `Order`, `Fill`, and all `exec.*` payloads are `@dataclass(frozen=True)`. Mutation means `dataclasses.replace`.
- Time comes from the injected `Clock` (`clock.timestamp()` / `clock.utc_now()`). Never call `datetime.now()` in adapter or engine code paths added by this plan.
- Topic convention is `{domain}.{verb}.{broker}` for broker-directed and broker-emitted messages: commands `exec.command.<verb>.dhan`, events `exec.event.<verb>.dhan`. Engine-internal domain events stay unsuffixed (`domain.order.placed`, `domain.fill.received`).
- Never import a private module across a package boundary. `scalpr.adapters.dhan._http` is internal to the Dhan adapter.
- Production modules outside `scalpr/adapters/dhan/` must not import `DhanClient` concretely — depend on a Protocol from `scalpr.domain.contracts`.
- Staging discipline from `AGENTS.md`: `git add` only. **Never `git commit`** unless the user explicitly asks. Every staged state must pass `pytest tests/unit/ tests/contract/` with 0 failures.
- After any code change, re-run `python3 .qoder/skills/kanban.cli/scripts/kanban.py scan`.

## Task 4 (verbatim from the plan, lines 510-668)

R1's cure at the call site. The POST response is currently discarded on line 199.

**Files:**
- Modify: `scalpr/engine/execution_engine.py` (add `broker_order_id` to `OrderAccepted`)
- Modify: `scalpr/adapters/dhan/client.py` (`__init__`, `_on_submit`)
- Modify: `tests/unit/adapters/dhan/test_client.py`

**Interfaces:**
- Consumes: `OrderRegistry` from Task 3.
- Produces: `OrderAccepted` gains a field — `OrderAccepted(order_id: str, timestamp: datetime, broker_order_id: str = "")`. `DhanClient` gains a public read-only property `registry -> OrderRegistry`, consumed by `OrderWatcher` in Task 8.

### Step 1: Stop the fixture from masking the bug

`tests/unit/adapters/dhan/test_client.py` is `unittest.TestCase`-based: `TestDhanClientOnSubmit.setUp` (line 182) patches the adapter's collaborators, builds `self.client = DhanClient(self.bus, self.clock, self.config)`, and calls handlers directly as `self.client._on_submit(self.msg)`. Tests use `self.assertEqual` style.

Line 248 currently reads:

```python
        self.mock_http_client.post.return_value = {"orderId": "ord-1", "filledQuantity": 10}
```

The broker id `"ord-1"` is identical to the local `Order.order_id` (line 209), which hides the entire defect — sending the local id to the broker looks correct. Change it to a distinct value:

```python
        self.mock_http_client.post.return_value = {"orderId": "ORD123456", "orderStatus": "TRANSIT"}
```

### Step 2: Write the failing tests

Append to `class TestDhanClientOnSubmit` in `tests/unit/adapters/dhan/test_client.py`:

```python
    def test_submit_registers_broker_order_id(self):
        """POST /orders returns the broker's orderId; it must be captured, not
        discarded, otherwise cancel/modify can never address the real order."""
        self.client._on_submit(self.msg)
        self.assertEqual(self.client.registry.broker_id("ord-1"), "ORD123456")

    def test_accepted_event_carries_broker_order_id(self):
        self.client._on_submit(self.msg)
        events = self.bus.filter("exec.event.accepted.dhan")
        self.assertEqual(len(events), 1)
        ev = events[0].payload
        self.assertEqual(ev.order_id, "ord-1")
        self.assertEqual(ev.broker_order_id, "ORD123456")

    def test_missing_order_id_in_response_is_a_rejection(self):
        """No orderId means we could never cancel it — treat as rejected rather
        than pretending the order is live."""
        self.mock_http_client.post.return_value = {"orderStatus": "TRANSIT"}

        self.client._on_submit(self.msg)

        self.assertIsNone(self.client.registry.broker_id("ord-1"))
        self.assertEqual(len(self.bus.filter("exec.event.accepted.dhan")), 0)
        events = self.bus.filter("exec.event.rejected.dhan")
        self.assertEqual(len(events), 1)
        self.assertIn("orderId", events[0].payload.reason)
```

### Step 3: Run to verify they fail

```bash
.venv/bin/python -m pytest tests/unit/adapters/dhan/test_client.py -q -k "TestDhanClientOnSubmit"
```

Expected: the three new tests FAIL with `AttributeError: 'DhanClient' object has no attribute 'registry'`. The pre-existing `test_publishes_order_accepted_on_success` must still pass — it asserts the *local* id, which does not change.

### Step 4: Add the field to `OrderAccepted`

In `scalpr/engine/execution_engine.py`, replace the `OrderAccepted` definition at lines 70-73:

```python
@dataclasses.dataclass(frozen=True)
class OrderAccepted:
    order_id: str
    timestamp: datetime
    broker_order_id: str = ""
```

The default keeps every existing construction site valid, including `FakeExchange`.

### Step 5: Give the client a registry

In `scalpr/adapters/dhan/client.py`, add the import alongside the other adapter-private imports:

```python
from scalpr.adapters.dhan._order_registry import OrderRegistry
```

In `DhanClient.__init__`, add:

```python
        self._registry = OrderRegistry()
```

and add the property next to the other public accessors:

```python
    @property
    def registry(self) -> OrderRegistry:
        """Local order id <-> Dhan orderId map for this client."""
        return self._registry
```

### Step 6: Capture the id in `_on_submit`

Replace `_on_submit` (currently `client.py:190-216`) with:

```python
    def _on_submit(self, msg: SubmitOrder) -> None:
        order = msg.order
        try:
            self._token_manager.get_token()
            security_id, segment = self._resolve(order.symbol, order.exchange.value)
            req = order_to_dhan_request_v2(
                order, security_id, segment, self._client_id,
                product_type=order.product_type,
            )
            resp = self._http_client.post("/orders", data=req)
            broker_order_id = str(resp.get("orderId") or "")
            if not broker_order_id:
                raise ValueError(f"broker response missing 'orderId': {resp!r}")
            self._registry.register(order.order_id, broker_order_id)
            self._bus.publish(
                "exec.event.accepted.dhan",
                OrderAccepted(
                    order_id=order.order_id,
                    timestamp=self._clock.timestamp(),
                    broker_order_id=broker_order_id,
                ),
            )
        except Exception as exc:
            logger.error("submit_failed: order_id=%s error=%s", order.order_id, exc)
            self._bus.publish(
                "exec.event.rejected.dhan",
                OrderRejected(
                    order_id=order.order_id,
                    reason=str(exc),
                    timestamp=self._clock.timestamp(),
                ),
            )
```

### Step 7: Run to verify they pass

```bash
.venv/bin/python -m pytest tests/unit/adapters/dhan/test_client.py tests/unit/engine/ -q
```

Expected: all pass.

### Step 8: Full suite and stage

```bash
.venv/bin/python -m pytest tests/unit/ tests/contract/ -q
git add scalpr/engine/execution_engine.py scalpr/adapters/dhan/client.py tests/unit/adapters/dhan/test_client.py
```

Expected: `1691 passed` (1688 after Task 3, plus 3).

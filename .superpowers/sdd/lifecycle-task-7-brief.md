# Task 7 brief — The engine waits for confirmation

## Global Constraints (verbatim from the plan)

- Money is `Decimal`. Never `float` in a domain object. `Fill.price` and `Order.price` raise `TypeError` on non-`Decimal`.
- `Order`, `Fill`, and all `exec.*` payloads are `@dataclass(frozen=True)`. Mutation means `dataclasses.replace`.
- Time comes from the injected `Clock` (`clock.timestamp()` / `clock.utc_now()`). Never call `datetime.now()` in adapter or engine code paths added by this plan.
- Topic convention is `{domain}.{verb}.{broker}` for broker-directed and broker-emitted messages: commands `exec.command.<verb>.dhan`, events `exec.event.<verb>.dhan`. Engine-internal domain events stay unsuffixed (`domain.order.placed`, `domain.fill.received`).
- Never import a private module across a package boundary. `scalpr.adapters.dhan._http` is internal to the Dhan adapter.
- Production modules outside `scalpr/adapters/dhan/` must not import `DhanClient` concretely — depend on a Protocol from `scalpr.domain.contracts`.
- Staging discipline from `AGENTS.md`: `git add` only. **Never `git commit`** unless the user explicitly asks. Every staged state must pass `pytest tests/unit/ tests/contract/` with 0 failures.
- After any code change, re-run `python3 .qoder/skills/kanban.cli/scripts/kanban.py scan`.

## Task 7 (verbatim from the plan, lines 961-1200)

R4 and R6. The engine currently marks an order CANCELLED the moment a strategy asks (`execution_engine.py:168-181`), and applies an arbitrary caller dict straight onto the frozen domain object (`execution_engine.py:183-190`) before the broker has agreed. Both make the local book lie.

**Files:**
- Modify: `scalpr/engine/execution_engine.py` (`start`, `_on_cancel`, `_on_modify`, add `_on_cancel_rejected`, `_on_modified`, `_on_modify_rejected`)
- Modify: `tests/unit/engine/test_execution_engine.py`

**Interfaces:**
- Consumes: `OrderCancelRejected` (Task 5), `OrderModified` / `OrderModifyRejected` (Task 6).
- Produces: `ExecutionEngine` subscribes to `exec.event.cancel_rejected.dhan`, `exec.event.modified.dhan`, `exec.event.modify_rejected.dhan`. `MODIFIABLE_FIELDS: frozenset[str]` is the module-level whitelist.

### Step 1: Write the failing tests

Append to `tests/unit/engine/test_execution_engine.py`, following the existing style in that file (it builds `MessageBus()` + `StaticClock()` directly, as at line 68):

```python
class TestConfirmationDrivenLifecycle:
    def _open_order(self, bus, clock, engine, order_id="o1"):
        order = Order(
            order_id=order_id, symbol="RELIANCE", exchange=Exchange.NSE,
            side=OrderSide.BUY, order_type=OrderType.LIMIT,
            quantity=10, price=Decimal("2500.00"),
        )
        bus.publish("exec.command.submit", SubmitOrder(order=order))
        bus.publish(
            "exec.event.accepted.dhan",
            OrderAccepted(order_id=order_id, timestamp=clock.utc_now(), broker_order_id="ORD1"),
        )
        assert engine.cache.order(order_id).state == OrderState.OPEN
        return order

    def _engine(self):
        bus = MessageBus()
        clock = StaticClock()
        engine = ExecutionEngine(bus, clock)
        engine.start()
        return bus, clock, engine

    def test_cancel_command_does_not_transition_before_confirmation(self):
        """Marking CANCELLED on intent means the local book says flat while the
        broker still holds a live order."""
        bus, clock, engine = self._engine()
        self._open_order(bus, clock, engine)

        bus.publish("exec.command.cancel", CancelOrder(order_id="o1"))

        assert engine.cache.order("o1").state == OrderState.OPEN

    def test_cancel_transitions_only_on_broker_confirmation(self):
        bus, clock, engine = self._engine()
        self._open_order(bus, clock, engine)
        bus.publish("exec.command.cancel", CancelOrder(order_id="o1"))

        bus.publish("exec.event.cancelled.dhan",
                    OrderCancelled(order_id="o1", timestamp=clock.utc_now()))

        assert engine.cache.order("o1").state == OrderState.CANCELLED

    def test_cancel_rejected_leaves_order_open(self):
        bus, clock, engine = self._engine()
        self._open_order(bus, clock, engine)
        bus.publish("exec.command.cancel", CancelOrder(order_id="o1"))

        bus.publish("exec.event.cancel_rejected.dhan",
                    OrderCancelRejected(order_id="o1", reason="DH-906",
                                        timestamp=clock.utc_now()))

        assert engine.cache.order("o1").state == OrderState.OPEN

    def test_modify_command_does_not_mutate_before_confirmation(self):
        bus, clock, engine = self._engine()
        self._open_order(bus, clock, engine)

        bus.publish("exec.command.modify",
                    ModifyOrder(order_id="o1", updates={"price": Decimal("2600.00")}))

        assert engine.cache.order("o1").price == Decimal("2500.00")

    def test_modify_applies_on_confirmation(self):
        bus, clock, engine = self._engine()
        self._open_order(bus, clock, engine)
        bus.publish("exec.command.modify",
                    ModifyOrder(order_id="o1", updates={"price": Decimal("2600.00")}))

        bus.publish("exec.event.modified.dhan",
                    OrderModified(order_id="o1", updates={"price": Decimal("2600.00")},
                                  timestamp=clock.utc_now()))

        assert engine.cache.order("o1").price == Decimal("2600.00")

    def test_modify_rejected_leaves_order_untouched(self):
        bus, clock, engine = self._engine()
        self._open_order(bus, clock, engine)
        bus.publish("exec.command.modify",
                    ModifyOrder(order_id="o1", updates={"price": Decimal("2600.00")}))

        bus.publish("exec.event.modify_rejected.dhan",
                    OrderModifyRejected(order_id="o1", reason="DH-905",
                                        timestamp=clock.utc_now()))

        assert engine.cache.order("o1").price == Decimal("2500.00")

    def test_non_whitelisted_modify_field_is_refused(self):
        """An arbitrary caller dict must not be able to rewrite the book of
        record — only price, quantity and trigger_price are modifiable."""
        bus, clock, engine = self._engine()
        self._open_order(bus, clock, engine)

        bus.publish("exec.command.modify",
                    ModifyOrder(order_id="o1", updates={"state": OrderState.FILLED}))
        bus.publish("exec.event.modified.dhan",
                    OrderModified(order_id="o1", updates={"state": OrderState.FILLED},
                                  timestamp=clock.utc_now()))

        assert engine.cache.order("o1").state == OrderState.OPEN
```

Add `OrderCancelRejected`, `OrderModified`, `OrderModifyRejected` to that file's existing import block from `scalpr.engine.execution_engine`.

### Step 2: Run to verify they fail

```bash
.venv/bin/python -m pytest tests/unit/engine/test_execution_engine.py -q -k TestConfirmationDrivenLifecycle
```

Expected: FAIL — the first on `state == OrderState.CANCELLED` (the optimistic transition), the modify ones on the blind `dataclasses.replace`.

### Step 3: Add the whitelist and the three subscriptions

In `scalpr/engine/execution_engine.py`, add at module level after the payload dataclasses:

```python
# Fields a broker modify may legitimately change. Anything else arriving in a
# ModifyOrder.updates dict is a bug or an attack — never let it reach the
# frozen domain object.
MODIFIABLE_FIELDS: frozenset[str] = frozenset({"price", "quantity", "trigger_price"})
```

In `start` (currently `execution_engine.py:134-143`), add after the existing `exec.event.cancelled.dhan` subscription:

```python
        self._bus.subscribe("exec.event.cancel_rejected.dhan", self._on_cancel_rejected)
        self._bus.subscribe("exec.event.modified.dhan", self._on_modified)
        self._bus.subscribe("exec.event.modify_rejected.dhan", self._on_modify_rejected)
```

### Step 4: Make cancel and modify intent-only

Replace `_on_cancel` (currently `execution_engine.py:168-181`) with:

```python
    def _on_cancel(self, cmd: CancelOrder) -> None:
        self._event_store.append(cmd)
        order = self._cache.order(cmd.order_id)
        if order is None:
            return
        if order.state.is_terminal:
            return
        # Route the intent only. The order stays in its current state until the
        # broker confirms on exec.event.cancelled.<broker> — a local book that
        # claims CANCELLED while the broker holds a live order is a real-money
        # divergence.
        self._route("exec.command.cancel", cmd.broker, cmd)
```

Replace `_on_modify` (currently `execution_engine.py:183-190`) with:

```python
    def _on_modify(self, cmd: ModifyOrder) -> None:
        self._event_store.append(cmd)
        order = self._cache.order(cmd.order_id)
        if order is None or order.state.is_terminal:
            return
        # Route the intent only; apply on exec.event.modified.<broker>.
        self._route("exec.command.modify", cmd.broker, cmd)
```

### Step 5: Add the three confirmation handlers

Append to `ExecutionEngine`:

```python
    def _on_cancel_rejected(self, payload: OrderCancelRejected) -> None:
        # The order remains in whatever state it was; record the refusal so the
        # risk layer and any operator can see the cancel did not land.
        self._event_store.append(payload)
        logger.warning(
            "cancel_rejected: order_id=%s reason=%s", payload.order_id, payload.reason
        )

    def _on_modified(self, payload: OrderModified) -> None:
        order = self._cache.order(payload.order_id)
        if order is None:
            return
        applied = {
            key: value
            for key, value in payload.updates.items()
            if key in MODIFIABLE_FIELDS
        }
        rejected_keys = set(payload.updates) - MODIFIABLE_FIELDS
        if rejected_keys:
            logger.warning(
                "modify_fields_refused: order_id=%s fields=%s",
                payload.order_id,
                sorted(rejected_keys),
            )
        if not applied:
            self._event_store.append(payload)
            return
        self._cache.update(dataclasses.replace(order, **applied))
        self._event_store.append(payload)

    def _on_modify_rejected(self, payload: OrderModifyRejected) -> None:
        self._event_store.append(payload)
        logger.warning(
            "modify_rejected: order_id=%s reason=%s", payload.order_id, payload.reason
        )
```

Add a module logger at the top of `execution_engine.py` if one is not already present:

```python
import logging

logger = logging.getLogger(__name__)
```

### Step 6: Run the engine tests

```bash
.venv/bin/python -m pytest tests/unit/engine/test_execution_engine.py -q
```

Expected: all pass. If a pre-existing test asserted the optimistic-cancel behaviour, it encoded the bug — update it to publish `exec.event.cancelled.dhan` before asserting CANCELLED, and note the change in the report.

### Step 7: Full suite and stage

```bash
.venv/bin/python -m pytest tests/unit/ tests/contract/ -q
git add scalpr/engine/execution_engine.py tests/unit/engine/test_execution_engine.py
```

Expected: all pass (expect `1703 passed` — 1696 + 7 new).

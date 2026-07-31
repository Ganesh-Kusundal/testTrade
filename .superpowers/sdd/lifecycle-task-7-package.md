# Review Package — Task 7: The engine waits for confirmation

- Plan: `docs/superpowers/plans/2026-07-31-broker-lifecycle-truth.md` (Task 7 at line 961)
- Brief given to implementer: `.superpowers/sdd/lifecycle-task-7-brief.md`
- Index tree range: `d32ca561757602015fbf8c5f81755410957588a7` .. `f32c34205a1c3eb73a5b4a7b32a8245a9b1b7cb9`
- Implementer status: DONE
- Verified by controller: full suite `1703 passed, 3 warnings in 25.37s`; `lint-imports --no-cache` = `7 kept, 0 broken`; HEAD unchanged at `c7fc087` (staged, not committed)

## Diff stat

```
 scalpr/engine/execution_engine.py          |  63 ++++++++++++++---
 tests/unit/engine/test_execution_engine.py | 104 +++++++++++++++++++++++++++++
 2 files changed, 158 insertions(+), 9 deletions(-)
```

## What this task fixes

R4 and R6 — the most architecturally significant change in the plan. The engine currently makes the local book lie in two ways:
1. `_on_cancel` marks the order CANCELLED the moment a strategy asks, before the broker has confirmed. A local book that says "flat" while the broker still holds a live order is a real-money divergence.
2. `_on_modify` applies an arbitrary caller dict straight onto the frozen domain object via `dataclasses.replace(order, **cmd.updates)` — before the broker has agreed, and without any field whitelist. A malicious or buggy caller could rewrite `state`, `quantity`, or any other field.

After this task:
- Cancel and modify become **intent-only**: the engine routes the command to the broker but leaves the local order state untouched until the broker confirms.
- Three new confirmation handlers (`_on_cancel_rejected`, `_on_modified`, `_on_modify_rejected`) subscribe to the broker's events.
- `MODIFIABLE_FIELDS` whitelists the only fields a broker modify may legitimately change (`price`, `quantity`, `trigger_price`). Anything else is logged and dropped.

## What to verify

1. Does the implementation match the brief's verbatim code?
2. Is `MODIFIABLE_FIELDS` at module level after the payload dataclasses?
3. Are the three new handlers subscribed in `start()`?
4. Does `_on_cancel` route the intent only, with no state transition?
5. Does `_on_modify` route the intent only, with no mutation?
6. Does `_on_modified` use `dataclasses.replace(order, **applied)` with the filtered `applied` dict (not the raw `payload.updates`)?
7. Are the 7 new tests real behaviour tests, not self-mocking?
8. Did any pre-existing test get modified? (The implementer reports none — verify.)
9. Does `pytest tests/unit/ tests/contract/` still pass? Run it yourself.
10. Does `lint-imports --no-cache` still pass? Run it yourself.
11. Did the implementer touch any file outside the two the brief listed?

## Full diff

```diff
diff --git a/scalpr/engine/execution_engine.py b/scalpr/engine/execution_engine.py
--- a/scalpr/engine/execution_engine.py
+++ b/scalpr/engine/execution_engine.py
@@ -1,6 +1,9 @@
 from __future__ import annotations

 import dataclasses
+import logging
 from datetime import datetime, timezone
 from typing import Any

+logger = logging.getLogger(__name__)
+
@@ -108,6 +111,13 @@ class OrderFilled:


+# Fields a broker modify may legitimately change. Anything else arriving in a
+# ModifyOrder.updates dict is a bug or an attack — never let it reach the
+# frozen domain object.
+MODIFIABLE_FIELDS: frozenset[str] = frozenset({"price", "quantity", "trigger_price"})
+
+
 class ExecutionEngine:
     def __init__(self, bus: MessageBus, clock: Clock) -> None:
@@ -134,6 +144,9 @@ class ExecutionEngine:
         self._bus.subscribe("exec.event.rejected.dhan", self._on_rejected)
         self._bus.subscribe("exec.event.cancelled.dhan", self._on_cancelled)
+        self._bus.subscribe("exec.event.cancel_rejected.dhan", self._on_cancel_rejected)
+        self._bus.subscribe("exec.event.modified.dhan", self._on_modified)
+        self._bus.subscribe("exec.event.modify_rejected.dhan", self._on_modify_rejected)
         self._running = True

@@ -168,23 +181,20 @@ class ExecutionEngine:
     def _on_cancel(self, cmd: CancelOrder) -> None:
         self._event_store.append(cmd)
         order = self._cache.order(cmd.order_id)
         if order is None:
             return
         if order.state.is_terminal:
             return
-        try:
-            cancelled = order.transition_to(OrderState.CANCELLED)
-            self._cache.update(cancelled)
-            self._event_store.append(cmd)
-            self._route("exec.command.cancel", cmd.broker, cmd)
-        except ValueError:
-            pass
+        # Route the intent only. The order stays in its current state until the
+        # broker confirms on exec.event.cancelled.<broker> — a local book that
+        # claims CANCELLED while the broker holds a live order is a real-money
+        # divergence.
+        self._route("exec.command.cancel", cmd.broker, cmd)

     def _on_modify(self, cmd: ModifyOrder) -> None:
         self._event_store.append(cmd)
         order = self._cache.order(cmd.order_id)
         if order is None or order.state.is_terminal:
             return
-        new_order = dataclasses.replace(order, **cmd.updates)
-        self._cache.update(new_order)
-        self._route("exec.command.modify", cmd.broker, cmd)
+        # Route the intent only; apply on exec.event.modified.<broker>.
+        self._route("exec.command.modify", cmd.broker, cmd)

@@ -268,3 +278,52 @@ class ExecutionEngine:
         self._event_store.append(payload)

+    def _on_cancel_rejected(self, payload: OrderCancelRejected) -> None:
+        # The order remains in whatever state it was; record the refusal so the
+        # risk layer and any operator can see the cancel did not land.
+        self._event_store.append(payload)
+        logger.warning(
+            "cancel_rejected: order_id=%s reason=%s", payload.order_id, payload.reason
+        )
+
+    def _on_modified(self, payload: OrderModified) -> None:
+        order = self._cache.order(payload.order_id)
+        if order is None:
+            return
+        applied = {
+            key: value
+            for key, value in payload.updates.items()
+            if key in MODIFIABLE_FIELDS
+        }
+        rejected_keys = set(payload.updates) - MODIFIABLE_FIELDS
+        if rejected_keys:
+            logger.warning(
+                "modify_fields_refused: order_id=%s fields=%s",
+                payload.order_id,
+                sorted(rejected_keys),
+            )
+        if not applied:
+            self._event_store.append(payload)
+            return
+        self._cache.update(dataclasses.replace(order, **applied))
+        self._event_store.append(payload)
+
+    def _on_modify_rejected(self, payload: OrderModifyRejected) -> None:
+        self._event_store.append(payload)
+        logger.warning(
+            "modify_rejected: order_id=%s reason=%s", payload.order_id, payload.reason
+        )
diff --git a/tests/unit/engine/test_execution_engine.py b/tests/unit/engine/test_execution_engine.py
--- a/tests/unit/engine/test_execution_engine.py
+++ b/tests/unit/engine/test_execution_engine.py
@@ -10,6 +10,9 @@ from scalpr.engine.execution_engine import (
     OrderAccepted,
     OrderCancelled,
+    OrderCancelRejected,
     OrderFilled,
+    OrderModified,
+    OrderModifyRejected,
     OrderRejected,
     SubmitOrder,
 )
@@ -628,3 +631,114 @@ class TestExecutionEngineEdgeCases:

         bus.publish("exec.event.accepted.dhan", OrderAccepted(order_id="nonexistent", timestamp=clock.utc_now()))
+
+
+class TestConfirmationDrivenLifecycle:
+    def _open_order(self, bus, clock, engine, order_id="o1"):
+        order = Order(
+            order_id=order_id, symbol="RELIANCE", exchange=Exchange.NSE,
+            side=OrderSide.BUY, order_type=OrderType.LIMIT,
+            quantity=10, price=Decimal("2500.00"),
+        )
+        bus.publish("exec.command.submit", SubmitOrder(order=order))
+        bus.publish(
+            "exec.event.accepted.dhan",
+            OrderAccepted(order_id=order_id, timestamp=clock.utc_now(), broker_order_id="ORD1"),
+        )
+        assert engine.cache.order(order_id).state == OrderState.OPEN
+        return order
+
+    def _engine(self):
+        bus = MessageBus()
+        clock = StaticClock()
+        engine = ExecutionEngine(bus, clock)
+        engine.start()
+        return bus, clock, engine
+
+    def test_cancel_command_does_not_transition_before_confirmation(self):
+        """Marking CANCELLED on intent means the local book says flat while the
+        broker still holds a live order."""
+        bus, clock, engine = self._engine()
+        self._open_order(bus, clock, engine)
+
+        bus.publish("exec.command.cancel", CancelOrder(order_id="o1"))
+
+        assert engine.cache.order("o1").state == OrderState.OPEN
+
+    def test_cancel_transitions_only_on_broker_confirmation(self):
+        bus, clock, engine = self._engine()
+        self._open_order(bus, clock, engine)
+        bus.publish("exec.command.cancel", CancelOrder(order_id="o1"))
+
+        bus.publish("exec.event.cancelled.dhan",
+                    OrderCancelled(order_id="o1", timestamp=clock.utc_now()))
+
+        assert engine.cache.order("o1").state == OrderState.CANCELLED
+
+    def test_cancel_rejected_leaves_order_open(self):
+        bus, clock, engine = self._engine()
+        self._open_order(bus, clock, engine)
+        bus.publish("exec.command.cancel", CancelOrder(order_id="o1"))
+
+        bus.publish("exec.event.cancel_rejected.dhan",
+                    OrderCancelRejected(order_id="o1", reason="DH-906",
+                                        timestamp=clock.utc_now()))
+
+        assert engine.cache.order("o1").state == OrderState.OPEN
+
+    def test_modify_command_does_not_mutate_before_confirmation(self):
+        bus, clock, engine = self._engine()
+        self._open_order(bus, clock, engine)
+
+        bus.publish("exec.command.modify",
+                    ModifyOrder(order_id="o1", updates={"price": Decimal("2600.00")}))
+
+        assert engine.cache.order("o1").price == Decimal("2500.00")
+
+    def test_modify_applies_on_confirmation(self):
+        bus, clock, engine = self._engine()
+        self._open_order(bus, clock, engine)
+        bus.publish("exec.command.modify",
+                    ModifyOrder(order_id="o1", updates={"price": Decimal("2600.00")}))
+
+        bus.publish("exec.event.modified.dhan",
+                    OrderModified(order_id="o1", updates={"price": Decimal("2600.00")},
+                                  timestamp=clock.utc_now()))
+
+        assert engine.cache.order("o1").price == Decimal("2600.00")
+
+    def test_modify_rejected_leaves_order_untouched(self):
+        bus, clock, engine = self._engine()
+        self._open_order(bus, clock, engine)
+        bus.publish("exec.command.modify",
+                    ModifyOrder(order_id="o1", updates={"price": Decimal("2600.00")}))
+
+        bus.publish("exec.event.modify_rejected.dhan",
+                    OrderModifyRejected(order_id="o1", reason="DH-905",
+                                        timestamp=clock.utc_now()))
+
+        assert engine.cache.order("o1").price == Decimal("2500.00")
+
+    def test_non_whitelisted_modify_field_is_refused(self):
+        """An arbitrary caller dict must not be able to rewrite the book of
+        record — only price, quantity and trigger_price are modifiable."""
+        bus, clock, engine = self._engine()
+        self._open_order(bus, clock, engine)
+
+        bus.publish("exec.command.modify",
+                    ModifyOrder(order_id="o1", updates={"state": OrderState.FILLED}))
+        bus.publish("exec.event.modified.dhan",
+                    OrderModified(order_id="o1", updates={"state": OrderState.FILLED},
+                                  timestamp=clock.utc_now()))
+
+        assert engine.cache.order("o1").state == OrderState.OPEN
```

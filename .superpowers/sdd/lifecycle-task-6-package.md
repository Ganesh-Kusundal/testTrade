# Review Package — Task 6: Modify addresses the broker's id and always terminates

- Plan: `docs/superpowers/plans/2026-07-31-broker-lifecycle-truth.md` (Task 6 at line 813)
- Brief given to implementer: `.superpowers/sdd/lifecycle-task-6-brief.md`
- Index tree range: `6ea5a500346b0550a272d27a8512fa09b170169f` .. `d32ca561757602015fbf8c5f81755410957588a7`
- Implementer status: DONE
- Verified by controller: full suite `1696 passed, 3 warnings in 25.08s`; `lint-imports --no-cache` = `7 kept, 0 broken`; HEAD unchanged at `c7fc087` (staged, not committed)

## Diff stat

```
 scalpr/adapters/dhan/client.py          | 33 ++++++++++++++++++++++++++++-
 scalpr/engine/execution_engine.py       | 14 +++++++++++++
 tests/unit/adapters/dhan/test_client.py | 37 ++++++++++++++++++++++++++++++++-
 3 files changed, 82 insertions(+), 2 deletions(-)
```

## What this task fixes

The other half of R2/R4. Previously `_on_modify` sent the *local* UUID to the broker and published **nothing at all** — not on success, not on failure. The engine had no way to know a modify landed, so the local book and the broker's book could silently diverge.

After this task:
- The modify addresses the broker's id (looked up via `OrderRegistry`).
- Unmapped modifies publish `OrderModifyRejected` instead of silently firing.
- Broker-side failures publish `OrderModifyRejected` instead of being swallowed.
- Only broker-confirmed modifications publish `OrderModified`.

## What to verify

1. Does the implementation match the brief's verbatim code?
2. Does `OrderModified` carry the **local** `order_id` (not the broker id)? The engine's cache is keyed locally.
3. Does the implementation use `updates=dict(msg.updates)` (defensive copy) as the brief specifies?
4. Are the three new tests real behaviour tests, not self-mocking?
5. Does `test_sends_put_request` now assert the broker id (`/orders/ORD123456`)?
6. Does `pytest tests/unit/ tests/contract/` still pass? Run it yourself.
7. Does `lint-imports --no-cache` still pass? Run it yourself.
8. Did the implementer touch any file outside the three the brief listed?

## Full diff

```diff
diff --git a/scalpr/adapters/dhan/client.py b/scalpr/adapters/dhan/client.py
--- a/scalpr/adapters/dhan/client.py
+++ b/scalpr/adapters/dhan/client.py
@@ -42,6 +42,8 @@ from scalpr.engine.execution_engine import (
     OrderAccepted,
     OrderCancelled,
     OrderCancelRejected,
+    OrderModified,
+    OrderModifyRejected,
     OrderRejected,
     SubmitOrder,
 )
@@ -256,24 +258,53 @@ class DhanClient:
             return
         self._bus.publish(
             "exec.event.cancelled.dhan",
             OrderCancelled(
                 order_id=msg.order_id,
                 timestamp=self._clock.timestamp(),
             ),
         )

     def _on_modify(self, msg: ModifyOrder) -> None:
+        broker_order_id = self._registry.broker_id(msg.order_id)
+        if broker_order_id is None:
+            logger.error("modify_unmapped: order_id=%s", msg.order_id)
+            self._bus.publish(
+                "exec.event.modify_rejected.dhan",
+                OrderModifyRejected(
+                    order_id=msg.order_id,
+                    reason=f"unknown broker order id for {msg.order_id}",
+                    timestamp=self._clock.timestamp(),
+                ),
+            )
+            return
         try:
-            self._http_client.put(f"/orders/{msg.order_id}", data=msg.updates)
+            self._http_client.put(f"/orders/{broker_order_id}", data=msg.updates)
         except Exception as exc:
             logger.error("modify_failed: order_id=%s error=%s", msg.order_id, exc)
+            self._bus.publish(
+                "exec.event.modify_rejected.dhan",
+                OrderModifyRejected(
+                    order_id=msg.order_id,
+                    reason=str(exc),
+                    timestamp=self._clock.timestamp(),
+                ),
+            )
+            return
+        self._bus.publish(
+            "exec.event.modified.dhan",
+            OrderModified(
+                order_id=msg.order_id,
+                updates=dict(msg.updates),
+                timestamp=self._clock.timestamp(),
+            ),
+        )
diff --git a/scalpr/engine/execution_engine.py b/scalpr/engine/execution_engine.py
--- a/scalpr/engine/execution_engine.py
+++ b/scalpr/engine/execution_engine.py
@@ -87,6 +87,20 @@ class OrderCancelRejected:


+@dataclasses.dataclass(frozen=True)
+class OrderModified:
+    order_id: str
+    updates: dict
+    timestamp: datetime
+
+
+@dataclasses.dataclass(frozen=True)
+class OrderModifyRejected:
+    order_id: str
+    reason: str
+    timestamp: datetime
+
+
 @dataclasses.dataclass(frozen=True)
 class OrderFilled:
diff --git a/tests/unit/adapters/dhan/test_client.py b/tests/unit/adapters/dhan/test_client.py
--- a/tests/unit/adapters/dhan/test_client.py
+++ b/tests/unit/adapters/dhan/test_client.py
@@ -420,35 +420,70 @@ class TestDhanClientOnModify(unittest.TestCase):
         self.mock_resolver = self.mocks[4].return_value

         self.client = DhanClient(self.bus, self.clock, self.config)
+        self.client.registry.register("ord-1", "ORD123456")
         self.msg = ModifyOrder(order_id="ord-1", updates={"quantity": 15})

     def test_acquires_rate_limit_bucket_orders(self):
         self.client._on_modify(self.msg)

     def test_sends_put_request(self):
         self.client._on_modify(self.msg)
         self.mock_http_client.put.assert_called_once_with(
-            "/orders/ord-1", data={"quantity": 15},
+            "/orders/ORD123456", data={"quantity": 15},
         )

     def test_handles_error_gracefully(self):
         self.mock_http_client.put.side_effect = RuntimeError("conn lost")
         self.client._on_modify(self.msg)  # should not raise

+    def test_modify_uses_broker_order_id_and_confirms(self):
+        self.client._on_modify(self.msg)
+
+        self.mock_http_client.put.assert_called_once_with(
+            "/orders/ORD123456", data={"quantity": 15},
+        )
+        events = self.bus.filter("exec.event.modified.dhan")
+        self.assertEqual(len(events), 1)
+        self.assertEqual(events[0].payload.order_id, "ord-1")
+        self.assertEqual(events[0].payload.updates, {"quantity": 15})
+
+    def test_modify_of_unmapped_order_publishes_modify_rejected(self):
+        """Without a mapping the broker cannot be addressed. Announce it rather
+        of letting the engine to assume the modify landed."""
+        self.client.registry.forget("ord-1")
+
+        self.client._on_modify(self.msg)
+
+        self.mock_http_client.put.assert_not_called()
+        events = self.bus.filter("exec.event.modify_rejected.dhan")
+        self.assertEqual(len(events), 1)
+        self.assertEqual(events[0].payload.order_id, "ord-1")
+        self.assertIn("unknown", events[0].payload.reason.lower())
+
+    def test_modify_http_failure_publishes_modify_rejected(self):
+        self.mock_http_client.put.side_effect = RuntimeError("DH-905 invalid price")
+
+        self.client._on_modify(self.msg)
+
+        self.assertEqual(len(self.bus.filter("exec.event.modified.dhan")), 0)
+        events = self.bus.filter("exec.event.modify_rejected.dhan")
+        self.assertEqual(len(events), 1)
+        self.assertIn("DH-905", events[0].payload.reason)
+
```

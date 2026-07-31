# Review Package — Task 5: Cancel addresses the broker's id and announces failure

- Plan: `docs/superpowers/plans/2026-07-31-broker-lifecycle-truth.md` (Task 5 at line 672)
- Brief given to implementer: `.superpowers/sdd/lifecycle-task-5-brief.md`
- Index tree range: `bf1c0553d6c5a3cb0c279dd2ee8aea4fd5126981` .. `6ea5a500346b0550a272d27a8512fa09b170169f`
- Implementer status: DONE
- Verified by controller: full suite `1693 passed, 3 warnings in 25.32s`; `lint-imports --no-cache` = `7 kept, 0 broken`; HEAD unchanged at `c7fc087` (staged, not committed)

## Diff stat

```
 scalpr/adapters/dhan/client.py          | 30 ++++++++++++++++++++++++++----
 scalpr/engine/execution_engine.py       |  7 +++++++
 tests/unit/adapters/dhan/test_client.py | 29 ++++++++++++++++++++++++++++-
 3 files changed, 61 insertions(+), 5 deletions(-)
```

## What this task fixes

R2 and half of R4. Previously `DELETE /orders/{msg.order_id}` sent the *local* UUID to the broker, so cancels silently no-op'd. And when the broker-side cancel failed, the engine had already optimistically marked the order CANCELLED — the local book silently diverged from the broker's truth.

After this task:
- The cancel addresses the broker's id (looked up via `OrderRegistry`).
- Unmapped cancels publish `OrderCancelRejected` instead of silently firing.
- Broker-side failures publish `OrderCancelRejected` instead of being swallowed.
- Only broker-confirmed cancellations publish `OrderCancelled`.

## What to verify

1. Does the implementation match the brief's verbatim code?
2. Does `OrderCancelled` still carry the **local** `order_id` (not the broker id)? The engine's cache is keyed locally.
3. Are the two new tests real behaviour tests, not self-mocking?
4. Does `test_sends_delete_request` now assert the broker id (`/orders/ORD123456`)?
5. Does `pytest tests/unit/ tests/contract/` still pass? Run it yourself.
6. Does `lint-imports --no-cache` still pass? Run it yourself.
7. Did the implementer touch any file outside the three the brief listed?

## Full diff

```diff
diff --git a/scalpr/adapters/dhan/client.py b/scalpr/adapters/dhan/client.py
--- a/scalpr/adapters/dhan/client.py
+++ b/scalpr/adapters/dhan/client.py
@@ -41,6 +41,7 @@ from scalpr.engine.execution_engine import (
     CancelOrder,
     ModifyOrder,
     OrderAccepted,
     OrderCancelled,
+    OrderCancelRejected,
     OrderRejected,
     SubmitOrder,
 )
@@ -222,31 +223,52 @@ class DhanClient:
             )

     def _on_cancel(self, msg: CancelOrder) -> None:
-        try:
-            self._http_client.delete(f"/orders/{msg.order_id}")
-        except Exception as exc:
-            logger.error("cancel_failed: order_id=%s error=%s", msg.order_id, exc)
+        broker_order_id = self._registry.broker_id(msg.order_id)
+        if broker_order_id is None:
+            logger.error("cancel_unmapped: order_id=%s", msg.order_id)
+            self._bus.publish(
+                "exec.event.cancel_rejected.dhan",
+                OrderCancelRejected(
+                    order_id=msg.order_id,
+                    reason=f"unknown broker order id for {msg.order_id}",
+                    timestamp=self._clock.timestamp(),
+                ),
+            )
+            return
+        try:
+            self._http_client.delete(f"/orders/{broker_order_id}")
+        except Exception as exc:
+            logger.error("cancel_failed: order_id=%s error=%s", msg.order_id, exc)
+            self._bus.publish(
+                "exec.event.cancel_rejected.dhan",
+                OrderCancelRejected(
+                    order_id=msg.order_id,
+                    reason=str(exc),
+                    timestamp=self._clock.timestamp(),
+                ),
+            )
+            return
         self._bus.publish(
             "exec.event.cancelled.dhan",
             OrderCancelled(
                 order_id=msg.order_id,
                 timestamp=self._clock.timestamp(),
             ),
         )
diff --git a/scalpr/engine/execution_engine.py b/scalpr/engine/execution_engine.py
--- a/scalpr/engine/execution_engine.py
+++ b/scalpr/engine/execution_engine.py
@@ -80,6 +80,13 @@ class OrderRejected:


 @dataclasses.dataclass(frozen=True)
 class OrderCancelled:
     order_id: str
     timestamp: datetime


+@dataclasses.dataclass(frozen=True)
+class OrderCancelRejected:
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
@@ -16,6 +16,7 @@ from scalpr.engine.execution_engine import (
     CancelOrder,
     ModifyOrder,
     OrderAccepted,
     OrderCancelled,
+    OrderCancelRejected,
     OrderRejected,
     SubmitOrder,
 )
@@ -348,41 +349,67 @@ class TestDhanClientOnCancel(unittest.TestCase):
         self.mock_resolver = self.mocks[4].return_value

         self.client = DhanClient(self.bus, self.clock, self.config)
+        self.client.registry.register("ord-1", "ORD123456")
         self.msg = CancelOrder(order_id="ord-1")

     def test_acquires_rate_limit_bucket_orders(self):
         self.client._on_cancel(self.msg)

     def test_sends_delete_request(self):
         self.client._on_cancel(self.msg)
-        self.mock_http_client.delete.assert_called_once_with("/orders/ord-1")
+        self.mock_http_client.delete.assert_called_once_with("/orders/ORD123456")

     def test_publishes_cancelled_event_on_success(self):
         self.client._on_cancel(self.msg)
         events = self.bus.filter("exec.event.cancelled.dhan")
         self.assertEqual(len(events), 1)
         ev = events[0].payload
         self.assertIsInstance(ev, OrderCancelled)
         self.assertEqual(ev.order_id, "ord-1")

     def test_handles_error_gracefully(self):
         self.mock_http_client.delete.side_effect = RuntimeError("conn lost")
         self.client._on_cancel(self.msg)  # should not raise

+    def test_cancel_of_unmapped_order_publishes_cancel_rejected(self):
+        """No mapping means we cannot address the broker. Say so loudly instead
+        of letting the engine believe the order is cancelled."""
+        self.client.registry.forget("ord-1")
+
+        self.client._on_cancel(self.msg)
+
+        self.mock_http_client.delete.assert_not_called()
+        events = self.bus.filter("exec.event.cancel_rejected.dhan")
+        self.assertEqual(len(events), 1)
+        self.assertEqual(events[0].payload.order_id, "ord-1")
+        self.assertIn("unknown", events[0].payload.reason.lower())
+
+    def test_cancel_http_failure_publishes_cancel_rejected(self):
+        """A broker-side cancel failure must reach the engine — the local book
+        must not silently diverge from a still-live broker order."""
+        self.mock_http_client.delete.side_effect = RuntimeError("DH-906 order not found")
+
+        self.client._on_cancel(self.msg)
+
+        self.assertEqual(len(self.bus.filter("exec.event.cancelled.dhan")), 0)
+        events = self.bus.filter("exec.event.cancel_rejected.dhan")
+        self.assertEqual(len(events), 1)
+        self.assertIn("DH-906", events[0].payload.reason)
+
```

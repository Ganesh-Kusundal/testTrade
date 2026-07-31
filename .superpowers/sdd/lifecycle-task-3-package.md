# Review Package — Task 3: OrderRegistry

- Plan: `docs/superpowers/plans/2026-07-31-broker-lifecycle-truth.md` (Task 3 at line 352)
- Brief given to implementer: `.superpowers/sdd/lifecycle-task-3-brief.md`
- Index tree range: `5dd196d260d21a8bb5fa202c06ab4b8120c0dab5` .. `3e5160492523256c118e2239c86d9d0612a125a7`
- Implementer status: DONE_WITH_CONCERNS
- Verified by controller: full suite `1688 passed, 3 warnings in 25.01s`; HEAD unchanged at `c7fc087` (staged, not committed)

## Diff stat

```
 scalpr/adapters/dhan/_order_registry.py         | 56 +++++++++++++++++++++++++
 tests/unit/adapters/dhan/test_order_registry.py | 49 ++++++++++++++++++++++
 2 files changed, 105 insertions(+)
```

## Controller-resolved concerns

The implementer raised two concerns. Both are resolved; they are recorded here
so the reviewer does not re-litigate them without the evidence.

1. **Tests converted from bare-pytest to `unittest.TestCase` style.** Done at
   the controller's instruction, to match the surrounding suite
   (`tests/unit/adapters/dhan/test_client.py` is `unittest.TestCase`).

2. **`threading.Lock` retained despite the controller's dispatch note saying
   "no thread locks".** The controller's note was wrong and the brief was
   right. Evidence that this class sits on a real thread boundary:
   - `scalpr/adapters/dhan/_ws.py:175` — `threading.Thread(target=self._run, daemon=True, name="dhan-ws")`
   - `scalpr/engine/message_bus.py:22` — the bus itself holds a `threading.Lock`
   - `scalpr/adapters/dhan/_http.py:54`, `_auth.py:147`, `_resolver.py:565` — every
     adapter-internal shared map is locked
   `register()` is called from the submit path; `local_id()` will be read from
   the WS/watcher thread (Task 8). The lock is load-bearing.

`all_broker_ids()` is **brief-mandated**, not scope creep — plan lines 362, 406
and 490 all specify it; Task 8's `OrderWatcher` polls with it.

## Full diff

```diff
diff --git a/scalpr/adapters/dhan/_order_registry.py b/scalpr/adapters/dhan/_order_registry.py
new file mode 100644
--- /dev/null
+++ b/scalpr/adapters/dhan/_order_registry.py
@@ -0,0 +1,56 @@
+"""Local order id <-> Dhan orderId identity map.
+
+The strategy layer knows an order by its local `Order.order_id`. Dhan knows
+it by the `orderId` it returns from POST /orders. Every subsequent broker
+call — cancel, modify, status — must address the broker's id, and every
+inbound broker event must be translated back. Without this map the adapter
+sends local UUIDs to the broker and cancels silently no-op.
+
+In-memory only. On restart the map is rebuilt by OrderWatcher from the order
+book, matching on `correlationId` (the local order id is sent as
+correlationId — see _mapper_orders.order_to_dhan_request_v2).
+"""
+
+from __future__ import annotations
+
+import threading
+
+
+class OrderRegistry:
+    """Thread-safe bidirectional map between local order ids and broker ids."""
+
+    def __init__(self) -> None:
+        self._to_broker: dict[str, str] = {}
+        self._to_local: dict[str, str] = {}
+        self._lock = threading.Lock()
+
+    def register(self, local_id: str, broker_id: str) -> None:
+        """Map a local order id to a broker order id, replacing any prior pair."""
+        if not broker_id:
+            raise ValueError("broker_id must be non-empty")
+        if not local_id:
+            raise ValueError("local_id must be non-empty")
+        with self._lock:
+            previous = self._to_broker.get(local_id)
+            if previous is not None:
+                self._to_local.pop(previous, None)
+            self._to_broker[local_id] = broker_id
+            self._to_local[broker_id] = local_id
+
+    def broker_id(self, local_id: str) -> str | None:
+        with self._lock:
+            return self._to_broker.get(local_id)
+
+    def local_id(self, broker_id: str) -> str | None:
+        with self._lock:
+            return self._to_local.get(broker_id)
+
+    def forget(self, local_id: str) -> None:
+        with self._lock:
+            broker_id = self._to_broker.pop(local_id, None)
+            if broker_id is not None:
+                self._to_local.pop(broker_id, None)
+
+    def all_broker_ids(self) -> list[str]:
+        with self._lock:
+            return list(self._to_local.keys())
diff --git a/tests/unit/adapters/dhan/test_order_registry.py b/tests/unit/adapters/dhan/test_order_registry.py
new file mode 100644
--- /dev/null
+++ b/tests/unit/adapters/dhan/test_order_registry.py
@@ -0,0 +1,49 @@
+"""OrderRegistry — bidirectional local_id <-> broker orderId map."""
+from __future__ import annotations
+
+import unittest
+
+from scalpr.adapters.dhan._order_registry import OrderRegistry
+
+
+class TestOrderRegistry(unittest.TestCase):
+    def setUp(self):
+        self.reg = OrderRegistry()
+
+    def test_register_maps_both_directions(self):
+        self.reg.register("local-1", "ORD123456")
+        self.assertEqual(self.reg.broker_id("local-1"), "ORD123456")
+        self.assertEqual(self.reg.local_id("ORD123456"), "local-1")
+
+    def test_unknown_ids_return_none(self):
+        self.assertIsNone(self.reg.broker_id("nope"))
+        self.assertIsNone(self.reg.local_id("nope"))
+
+    def test_re_register_replaces_stale_reverse_entry(self):
+        """A re-submitted local id must not leave the old broker id resolvable."""
+        self.reg.register("local-1", "ORD_OLD")
+        self.reg.register("local-1", "ORD_NEW")
+        self.assertEqual(self.reg.broker_id("local-1"), "ORD_NEW")
+        self.assertEqual(self.reg.local_id("ORD_NEW"), "local-1")
+        self.assertIsNone(self.reg.local_id("ORD_OLD"))
+
+    def test_forget_removes_both_directions(self):
+        self.reg.register("local-1", "ORD123456")
+        self.reg.forget("local-1")
+        self.assertIsNone(self.reg.broker_id("local-1"))
+        self.assertIsNone(self.reg.local_id("ORD123456"))
+
+    def test_forget_unknown_local_id_is_a_no_op(self):
+        self.reg.forget("never-registered")
+
+    def test_all_broker_ids_lists_every_registered_broker_id(self):
+        self.reg.register("local-1", "ORD1")
+        self.reg.register("local-2", "ORD2")
+        self.assertEqual(sorted(self.reg.all_broker_ids()), ["ORD1", "ORD2"])
+
+    def test_empty_broker_id_is_rejected(self):
+        """A blank orderId means the broker response was malformed; refuse it
+        rather than poisoning the map with an unusable key."""
+        with self.assertRaises(ValueError):
+            self.reg.register("local-1", "")
+        self.assertIsNone(self.reg.broker_id("local-1"))
```

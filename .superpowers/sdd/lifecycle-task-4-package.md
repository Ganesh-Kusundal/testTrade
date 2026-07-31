# Review Package — Task 4: `_on_submit` captures the broker order id

- Plan: `docs/superpowers/plans/2026-07-31-broker-lifecycle-truth.md` (Task 4 at line 510)
- Brief given to implementer: `.superpowers/sdd/lifecycle-task-4-brief.md`
- Index tree range: `3e5160492523256c118e2239c86d9d0612a125a7` .. `bf1c0553d6c5a3cb0c279dd2ee8aea4fd5126981`
- Implementer status: DONE
- Verified by controller: full suite `1691 passed, 3 warnings in 24.70s`; `lint-imports --no-cache` = `7 kept, 0 broken`; HEAD unchanged at `c7fc087` (staged, not committed)

## Diff stat

```
 docs/superpowers/plans/2026-07-31-broker-lifecycle-truth.md | 33 ++++++++++++++++++----
 scalpr/adapters/dhan/client.py                              | 14 ++++++++-
 scalpr/engine/execution_engine.py                           |  1 +
 tests/unit/adapters/dhan/test_client.py                     | 29 ++++++++++++++++++-
 4 files changed, 69 insertions(+), 8 deletions(-)
```

The plan doc diff is the controller's own count-correction edit (1684 → 1691 at line 668) — not an implementer change. The implementer touched exactly the three files the brief listed.

## What this task fixes

R1's cure at the call site. `client.py:199` previously discarded the `POST /orders` response, so the broker's `orderId` was lost. This is why cancel and modify later sent the *local* UUID to the broker and silently no-op'd — the adapter literally had no way to address the broker's order.

After this task:
- The response's `orderId` is extracted, validated non-empty, and stored in `OrderRegistry` keyed by the local `Order.order_id`.
- `OrderAccepted` gains a `broker_order_id` field (default `""` so `FakeExchange` construction sites still work).
- A missing `orderId` in the response is now treated as a rejection — the order cannot be cancelled, so it must not be considered live.

## What to verify

1. Does the implementation match the brief's verbatim code?
2. Does the `OrderAccepted` field default to `""` so `FakeExchange` still works?
3. Does the existing `test_publishes_order_accepted_on_success` still pass (it asserts the local id, not the broker id)?
4. Are the three new tests real behaviour tests, not self-mocking?
5. Does `pytest tests/unit/ tests/contract/` still pass? Run it yourself.
6. Does `lint-imports --no-cache` still pass? Run it yourself.
7. Did the implementer touch any file outside the three the brief listed?

## Full diff

```diff
diff --git a/scalpr/adapters/dhan/client.py b/scalpr/adapters/dhan/client.py
--- a/scalpr/adapters/dhan/client.py
+++ b/scalpr/adapters/dhan/client.py
@@ -12,6 +12,7 @@ from scalpr.adapters.dhan._auth import TokenManager
 from scalpr.adapters.dhan._historical import DhanHistoricalData
 from scalpr.adapters.dhan._http import DhanHttpClient
 from scalpr.adapters.dhan._loader import InstrumentLoader
+from scalpr.adapters.dhan._order_registry import OrderRegistry
 from scalpr.adapters.dhan._mapper_orders import order_to_dhan_request_v2
 from scalpr.adapters.dhan._resolver import SymbolResolver
 from scalpr.domain.events import (
@@ -80,6 +81,7 @@ class DhanClient:
         self._loader = InstrumentLoader(self._http_client, self._client_id)
         self._resolver = SymbolResolver(self._loader)
         self._historical = DhanHistoricalData(self._http_client, self._loader)
+        self._registry = OrderRegistry()
         self._bus = bus
         self._clock = clock
         self._config = config
@@ -120,6 +122,11 @@ class DhanClient:
         """The historical data adapter for this client."""
         return self._historical

+    @property
+    def registry(self) -> OrderRegistry:
+        """Local order id <-> Dhan orderId map for this client."""
+        return self._registry
+
     def start(self) -> None:
         try:
             csv_path = self._loader.ensure_loaded()
@@ -190,29 +197,34 @@ class DhanClient:
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
+            broker_order_id = str(resp.get("orderId") or "")
+            if not broker_order_id:
+                raise ValueError(f"broker response missing 'orderId': {resp!r}")
+            self._registry.register(order.order_id, broker_order_id)
             self._bus.publish(
                 "exec.event.accepted.dhan",
                 OrderAccepted(
                     order_id=order.order_id,
                     timestamp=self._clock.timestamp(),
+                    broker_order_id=broker_order_id,
                 ),
             )
         except Exception as exc:
-            logger.error("submit_failed: %s", exc)
+            logger.error("submit_failed: order_id=%s error=%s", order.order_id, exc)
             self._bus.publish(
                 "exec.event.rejected.dhan",
                 OrderRejected(
                     order_id=order.order_id,
                     reason=str(exc),
                     timestamp=self._clock.timestamp(),
                 ),
             )
diff --git a/scalpr/engine/execution_engine.py b/scalpr/engine/execution_engine.py
--- a/scalpr/engine/execution_engine.py
+++ b/scalpr/engine/execution_engine.py
@@ -64,6 +64,7 @@ class ModifyOrder:
 @dataclasses.dataclass(frozen=True)
 class OrderAccepted:
     order_id: str
     timestamp: datetime
+    broker_order_id: str = ""


 @dataclasses.dataclass(frozen=True)
 class OrderRejected:
diff --git a/tests/unit/adapters/dhan/test_client.py b/tests/unit/adapters/dhan/test_client.py
--- a/tests/unit/adapters/dhan/test_client.py
+++ b/tests/unit/adapters/dhan/test_client.py
@@ -238,7 +238,7 @@ class TestDhanClientOnSubmit(unittest.TestCase):
             "securityId": "12345",
             "quantity": 10,
             "disclosedQuantity": 0,
             "price": "2500",
             "triggerPrice": "0",
             "afterMarketOrder": False,
         }
-        self.mock_http_client.post.return_value = {"orderId": "ord-1", "filledQuantity": 10}
+        self.mock_http_client.post.return_value = {"orderId": "ORD123456", "orderStatus": "TRANSIT"}

@@ -292,6 +292,33 @@ class TestDhanClientOnSubmit(unittest.TestCase):
     def test_publishes_order_rejected_on_error(self):
         self.mock_http_client.post.side_effect = RuntimeError("API down")
         self.client._on_submit(self.msg)
         events = self.bus.filter("exec.event.rejected.dhan")
         self.assertEqual(len(events), 1)
         ev = events[0].payload
         self.assertIsInstance(ev, OrderRejected)
         self.assertEqual(ev.order_id, "ord-1")
         self.assertIn("API down", ev.reason)

+    def test_submit_registers_broker_order_id(self):
+        """POST /orders returns the broker's orderId; it must be captured, not
+        discarded, otherwise cancel/modify can never address the real order."""
+        self.client._on_submit(self.msg)
+        self.assertEqual(self.client.registry.broker_id("ord-1"), "ORD123456")
+
+    def test_accepted_event_carries_broker_order_id(self):
+        self.client._on_submit(self.msg)
+        events = self.bus.filter("exec.event.accepted.dhan")
+        self.assertEqual(len(events), 1)
+        ev = events[0].payload
+        self.assertEqual(ev.order_id, "ord-1")
+        self.assertEqual(ev.broker_order_id, "ORD123456")
+
+    def test_missing_order_id_in_response_is_a_rejection(self):
+        """No orderId means we could never cancel it — treat as rejected rather
+        than pretending the order is live."""
+        self.mock_http_client.post.return_value = {"orderStatus": "TRANSIT"}
+
+        self.client._on_submit(self.msg)
+
+        self.assertIsNone(self.client.registry.broker_id("ord-1"))
+        self.assertEqual(len(self.bus.filter("exec.event.accepted.dhan")), 0)
+        events = self.bus.filter("exec.event.rejected.dhan")
+        self.assertEqual(len(events), 1)
+        self.assertIn("orderId", events[0].payload.reason)
+
     def test_does_not_publish_filled_on_error(self):
         self.mock_http_client.post.side_effect = RuntimeError("API down")
         self.client._on_submit(self.msg)
         self.assertEqual(len(self.bus.filter("exec.event.filled.dhan")), 0)
```

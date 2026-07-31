## Global Constraints

- Money is `Decimal`. Never `float` in a domain object. `Fill.price` and `Order.price` raise `TypeError` on non-`Decimal`.
- `Order`, `Fill`, and all `exec.*` payloads are `@dataclass(frozen=True)`. Mutation means `dataclasses.replace`.
- Time comes from the injected `Clock` (`clock.timestamp()` / `clock.utc_now()`). Never call `datetime.now()` in adapter or engine code paths added by this plan.
- Topic convention is `{domain}.{verb}.{broker}` for broker-directed and broker-emitted messages: commands `exec.command.<verb>.dhan`, events `exec.event.<verb>.dhan`. Engine-internal domain events stay unsuffixed (`domain.order.placed`, `domain.fill.received`).
- Never import a private module across a package boundary. `scalpr.adapters.dhan._http` is internal to the Dhan adapter.
- Production modules outside `scalpr/adapters/dhan/` must not import `DhanClient` concretely — depend on a Protocol from `scalpr.domain.contracts`.
- Staging discipline from `AGENTS.md`: `git add` only. **Never `git commit`** unless the user explicitly asks. Every staged state must pass `pytest tests/unit/ tests/contract/` with 0 failures.
- After any code change, re-run `python3 .qoder/skills/kanban.cli/scripts/kanban.py scan`.


## Task 3: `OrderRegistry` — the local↔broker identity map

R1's cure. A pure, in-memory, bidirectional map with no I/O. Everything in Phase A depends on it, so it gets its own task and its own tests.

**Files:**
- Create: `scalpr/adapters/dhan/_order_registry.py`
- Create: `tests/unit/adapters/dhan/test_order_registry.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `scalpr.adapters.dhan._order_registry.OrderRegistry` with methods `register(local_id: str, broker_id: str) -> None`, `broker_id(local_id: str) -> str | None`, `local_id(broker_id: str) -> str | None`, `forget(local_id: str) -> None`, `all_broker_ids() -> list[str]`. Consumed by `client.py` (Tasks 4-5) and `_order_watcher.py` (Task 8).

- [ ] **Step 1: Write the failing test**

Create `tests/unit/adapters/dhan/test_order_registry.py`:

```python
"""OrderRegistry — bidirectional local_id <-> broker orderId map."""

from scalpr.adapters.dhan._order_registry import OrderRegistry


class TestOrderRegistry:
    def test_register_maps_both_directions(self):
        reg = OrderRegistry()
        reg.register("local-1", "ORD123456")
        assert reg.broker_id("local-1") == "ORD123456"
        assert reg.local_id("ORD123456") == "local-1"

    def test_unknown_ids_return_none(self):
        reg = OrderRegistry()
        assert reg.broker_id("nope") is None
        assert reg.local_id("nope") is None

    def test_re_register_replaces_stale_reverse_entry(self):
        """A re-submitted local id must not leave the old broker id resolvable."""
        reg = OrderRegistry()
        reg.register("local-1", "ORD_OLD")
        reg.register("local-1", "ORD_NEW")
        assert reg.broker_id("local-1") == "ORD_NEW"
        assert reg.local_id("ORD_NEW") == "local-1"
        assert reg.local_id("ORD_OLD") is None

    def test_forget_removes_both_directions(self):
        reg = OrderRegistry()
        reg.register("local-1", "ORD123456")
        reg.forget("local-1")
        assert reg.broker_id("local-1") is None
        assert reg.local_id("ORD123456") is None

    def test_forget_unknown_local_id_is_a_no_op(self):
        reg = OrderRegistry()
        reg.forget("never-registered")

    def test_all_broker_ids_lists_every_registered_broker_id(self):
        reg = OrderRegistry()
        reg.register("local-1", "ORD1")
        reg.register("local-2", "ORD2")
        assert sorted(reg.all_broker_ids()) == ["ORD1", "ORD2"]

    def test_empty_broker_id_is_rejected(self):
        """A blank orderId means the broker response was malformed; refuse it
        rather than poisoning the map with an unusable key."""
        reg = OrderRegistry()
        try:
            reg.register("local-1", "")
        except ValueError:
            pass
        else:
            raise AssertionError("expected ValueError for empty broker_id")
        assert reg.broker_id("local-1") is None
```

- [ ] **Step 2: Run it to verify it fails**

```bash
.venv/bin/python -m pytest tests/unit/adapters/dhan/test_order_registry.py -q
```
Expected: FAIL — `ModuleNotFoundError: No module named 'scalpr.adapters.dhan._order_registry'`.

- [ ] **Step 3: Write the implementation**

Create `scalpr/adapters/dhan/_order_registry.py`:

```python
"""Local order id <-> Dhan orderId identity map.

The strategy layer knows an order by its local `Order.order_id`. Dhan knows
it by the `orderId` it returns from POST /orders. Every subsequent broker
call — cancel, modify, status — must address the broker's id, and every
inbound broker event must be translated back. Without this map the adapter
sends local UUIDs to the broker and cancels silently no-op.

In-memory only. On restart the map is rebuilt by OrderWatcher from the order
book, matching on `correlationId` (the local order id is sent as
correlationId — see _mapper_orders.order_to_dhan_request_v2).
"""

from __future__ import annotations

import threading


class OrderRegistry:
    """Thread-safe bidirectional map between local order ids and broker ids."""

    def __init__(self) -> None:
        self._to_broker: dict[str, str] = {}
        self._to_local: dict[str, str] = {}
        self._lock = threading.Lock()

    def register(self, local_id: str, broker_id: str) -> None:
        """Map a local order id to a broker order id, replacing any prior pair."""
        if not broker_id:
            raise ValueError("broker_id must be non-empty")
        if not local_id:
            raise ValueError("local_id must be non-empty")
        with self._lock:
            previous = self._to_broker.get(local_id)
            if previous is not None:
                self._to_local.pop(previous, None)
            self._to_broker[local_id] = broker_id
            self._to_local[broker_id] = local_id

    def broker_id(self, local_id: str) -> str | None:
        with self._lock:
            return self._to_broker.get(local_id)

    def local_id(self, broker_id: str) -> str | None:
        with self._lock:
            return self._to_local.get(broker_id)

    def forget(self, local_id: str) -> None:
        with self._lock:
            broker_id = self._to_broker.pop(local_id, None)
            if broker_id is not None:
                self._to_local.pop(broker_id, None)

    def all_broker_ids(self) -> list[str]:
        with self._lock:
            return list(self._to_local.keys())
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
.venv/bin/python -m pytest tests/unit/adapters/dhan/test_order_registry.py -q
```
Expected: `7 passed`.

- [ ] **Step 5: Stage**

```bash
git add scalpr/adapters/dhan/_order_registry.py tests/unit/adapters/dhan/test_order_registry.py
```

---

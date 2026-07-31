# Broker Order-Lifecycle Truth — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Dhan adapter's order lifecycle tell the truth — every order gets a broker identity, cancels and modifies actually reach the broker, failures announce themselves, and fills enter the system from the broker instead of never arriving at all.

**Architecture:** The message-bus mediator stays. Three things change. (1) The adapter gains an identity map so local `order_id` and Dhan `orderId` are both known, and every broker call addresses the broker's id. (2) Every command path gains a terminating event — success *and* failure — so the engine never guesses. (3) A new `OrderWatcher` polls the already-proven `GET /orders` order book and publishes real fills, replacing the current situation where nothing in production ever publishes a fill.

**Tech Stack:** Python 3.13, pytest, `dataclasses` (frozen, slots), `Decimal` for money, in-process `MessageBus`, `import-linter` + `grimp` for boundary contracts, ruff.

## Global Constraints

- Money is `Decimal`. Never `float` in a domain object. `Fill.price` and `Order.price` raise `TypeError` on non-`Decimal`.
- `Order`, `Fill`, and all `exec.*` payloads are `@dataclass(frozen=True)`. Mutation means `dataclasses.replace`.
- Time comes from the injected `Clock` (`clock.timestamp()` / `clock.utc_now()`). Never call `datetime.now()` in adapter or engine code paths added by this plan.
- Topic convention is `{domain}.{verb}.{broker}` for broker-directed and broker-emitted messages: commands `exec.command.<verb>.dhan`, events `exec.event.<verb>.dhan`. Engine-internal domain events stay unsuffixed (`domain.order.placed`, `domain.fill.received`).
- Never import a private module across a package boundary. `scalpr.adapters.dhan._http` is internal to the Dhan adapter.
- Production modules outside `scalpr/adapters/dhan/` must not import `DhanClient` concretely — depend on a Protocol from `scalpr.domain.contracts`.
- Staging discipline from `AGENTS.md`: `git add` only. **Never `git commit`** unless the user explicitly asks. Every staged state must pass `pytest tests/unit/ tests/contract/` with 0 failures.
- After any code change, re-run `python3 .qoder/skills/kanban.cli/scripts/kanban.py scan`.

---

## Verified Baseline (measured 2026-07-31 at HEAD `c7fc087`)

Run these first; the plan assumes these exact starting numbers.

```bash
.venv/bin/python -m pytest tests/unit/ tests/contract/ -q   # 1679 passed, 0 failed
.venv/bin/lint-imports --config pyproject.toml              # aborts: Module 'scalpr.adapters.dhan' does not exist
.venv/bin/ruff check scalpr/adapters/dhan/client.py         # 12 errors
```

**Correction to the earlier review (2026-07-30):** the topic-divergence and phantom-fill defects it reported are **already fixed** at this HEAD. `ExecutionEngine.start` now subscribes to `exec.event.{accepted,filled,rejected,cancelled}.dhan` (`execution_engine.py:117-120`), `_on_fill` correctly unwraps `payload.fill` (`execution_engine.py:182-183`), and `_on_submit` publishes `OrderAccepted` rather than a fabricated fill (`client.py:200-206`). `response_to_fill` is no longer called from `client.py`. The four failing tests are gone. Do not re-fix those.

### Root causes this plan addresses

| # | Root cause | Evidence | Money impact |
|---|---|---|---|
| R1 | **The broker's order id is thrown away.** `resp` is assigned and never read. No local→broker identity map exists anywhere in the adapter. | `scalpr/adapters/dhan/client.py:199` | Keystone defect. Enables R2 and R3. |
| R2 | **Cancel and modify address the broker with the local UUID.** `DELETE /orders/{msg.order_id}` and `PUT /orders/{msg.order_id}` where `msg.order_id` is the strategy's local id. | `client.py:220`, `client.py:233` | Cancels and modifies can never succeed against a real Dhan order. A stop-loss cancel silently no-ops. |
| R3 | **Nothing in production publishes a fill.** `exec.event.filled.dhan` has exactly two publishers, both test doubles. `_ws.py` is market-data only — there is no order-update feed. | `tests/conftest.py:174`, `scalpr/adapters/test_helpers/fake_exchange.py:86`; no match in `scalpr/` | Orders reach `OPEN` and stay there forever. `filled_quantity`, `avg_price`, positions and PnL never advance from real execution. |
| R4 | **Local book goes to CANCELLED before the broker confirms, and failure is silent.** Engine transitions optimistically; adapter swallows the exception and publishes nothing. `_on_modify` publishes nothing even on success. | `execution_engine.py:153-159`, `client.py:228-229`, `client.py:231-235` | Local book says CANCELLED while the broker still holds a live order. Position divergence with real money at risk. |
| R5 | **The boundary guard reports green while violations exist.** `.import_linter_cache/` serves a stale graph. With `--no-cache` two contracts break. Separately, `scalpr/adapters/__init__.py` is absent so the guard aborts outright, and `scalpr/engine/` has no `__init__.py` so it is invisible to the graph (129 of 132 files analysed). | `lint-imports --config /tmp/probe.toml` KEPT vs `--no-cache` BROKEN; `.github/workflows/ci.yml:31` | A dark guard is worse than no guard — it certifies violations as clean. |
| R6 | **Engine applies untrusted modify payloads to a domain object.** `dataclasses.replace(order, **cmd.updates)` with an arbitrary caller-supplied dict, before the broker confirms. | `execution_engine.py:166` | A stray key corrupts the book of record; an unconfirmed modify is treated as applied. |

### Phase map

- **Phase 0 — Turn the guards on.** Tasks 1-2. No behaviour change. Makes the boundary contracts real and fixes the two violations they expose. Everything else is safer once this lands.
- **Phase A — Order-lifecycle truth.** Tasks 3-8. R1 → R2 → R4/R6 → R3, in dependency order. This is the money path.
- **Phase B — Structural (separate plan, after A lands).** Deliberately not expanded here; the scope is recorded so it is not lost: move `RateLimiter`/`TokenBucket`/`PAPER_BUCKETS` out of `_http.py` into `scalpr/infrastructure/rate_limiter.py` (fixes `scalpr/simulation/simulated_gateway.py:22-24` reaching a private module); break the `market_data ↔ adapters/dhan` cycle; route `scalpr/api/routers/orders.py:83` through `ExecutionEngine` instead of publishing `exec.command.submit.dhan` directly; remove `api/bootstrap.py`'s reach-ins into `client._bus`, `client._clock`, `gateway._historical`; replace the shadow `DhanClient` at `tests/conftest.py:100` with the real adapter in the contract suite.
- **Phase C — Hygiene (separate plan).** 12 ruff errors in `client.py`; split the 605-line / 65-public-method `DhanClient` facade and the 1040-line `_resolver.py`.

---

## File Structure

| File | Responsibility | Phase |
|---|---|---|
| `scalpr/adapters/__init__.py` | **Create.** Empty. Makes `scalpr.adapters.dhan` addressable by `grimp`, so the 7 contracts stop aborting. | 0 |
| `scalpr/engine/__init__.py` | **Create.** Empty. Makes `scalpr/engine/`'s 3 modules visible to the import graph (currently 129 of 132 files analysed). | 0 |
| `.github/workflows/ci.yml` | **Modify.** Add `--no-cache` to the `lint-imports` step. | 0 |
| `.gitignore` | **Modify.** Ignore `.import_linter_cache/`. | 0 |
| `scalpr/domain/contracts.py` | **Modify.** Add `ExecutionGatewayProtocol` and `HistoricalSourceProtocol` — the outward ports that let `risk` and `market_data` stop importing `DhanClient`. | 0 |
| `scalpr/risk/session_guard.py` | **Modify** line 7 + line 18. Depend on `ExecutionGatewayProtocol`. | 0 |
| `scalpr/market_data/historical.py` | **Modify** line 5 + line 12. Depend on `HistoricalSourceProtocol`. | 0 |
| `scalpr/adapters/dhan/_order_registry.py` | **Create.** `OrderRegistry` — the local↔broker identity map. One responsibility, no I/O, trivially testable. | A |
| `scalpr/adapters/dhan/client.py` | **Modify** `_on_submit`, `_on_cancel`, `_on_modify`. Own an `OrderRegistry`; address the broker by broker id; publish a terminating event on every path. | A |
| `scalpr/engine/execution_engine.py` | **Modify.** Add `OrderModified`/`OrderCancelRejected`/`OrderModifyRejected` payloads. Stop transitioning on cancel intent. Whitelist modify fields and apply on confirmation. | A |
| `scalpr/adapters/dhan/_mapper_orders.py` | **Modify.** Add `"TRANSIT"` to `_DHAN_STATUS_TO_STATE`; add `order_book_entry_to_fill`. | A |
| `scalpr/adapters/dhan/_order_watcher.py` | **Create.** `OrderWatcher` — polls `GET /orders`, diffs against last-seen, publishes real fill/reject/cancel events. This is the fill ingress that does not currently exist. | A |
| `tests/unit/adapters/dhan/test_order_registry.py` | **Create.** | A |
| `tests/unit/adapters/dhan/test_order_watcher.py` | **Create.** | A |
| `tests/unit/adapters/dhan/test_client.py` | **Modify.** Lifecycle assertions for the new events. | A |
| `tests/unit/engine/test_execution_engine.py` | **Modify.** Confirmation-driven cancel/modify assertions. | A |
| `tests/unit/test_import_contracts.py` | **Create.** Guard that `lint-imports --no-cache` stays green, so the cache can never lie again. | 0 |

---

## Task 1: Make the boundary guards real

The guard currently aborts on the missing `scalpr/adapters/__init__.py`, and when that is fixed it reports green off a stale cache. Both have to go, and the cache must never be able to lie again.

**Files:**
- Create: `scalpr/adapters/__init__.py`
- Create: `scalpr/engine/__init__.py`
- Create: `tests/unit/test_import_contracts.py`
- Modify: `.github/workflows/ci.yml:31`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: nothing.
- Produces: a live `lint-imports --no-cache` run. Task 2 fixes the two violations it exposes.

- [ ] **Step 1: Prove the guard is currently dead**

```bash
.venv/bin/lint-imports --config pyproject.toml
```
Expected: `Module 'scalpr.adapters.dhan' does not exist.` — it never evaluates a single contract.

- [ ] **Step 2: Create the two missing package markers**

Both files are empty. `scalpr/adapters/` and `scalpr/engine/` are currently implicit namespace packages, which `grimp` cannot address.

```bash
touch scalpr/adapters/__init__.py scalpr/engine/__init__.py
```

- [ ] **Step 3: Show that the cache lies**

```bash
.venv/bin/lint-imports --config pyproject.toml
.venv/bin/lint-imports --config pyproject.toml --no-cache
```
Expected: the cached run reports `7 kept, 0 broken` off a stale graph. The `--no-cache` run reports **`5 kept, 2 broken`**, naming:

```
scalpr.risk.session_guard -> scalpr.adapters.dhan.client (l.7)
scalpr.market_data.historical -> scalpr.adapters.dhan.client (l.5)
```

Same code, same config, opposite verdict. That is the finding.

The absolute file and dependency counts shift as soon as both `__init__.py` files exist (measured after Step 2: 133 files, 309 dependencies under `--no-cache`). Do not treat the counts as an assertion — the *verdict* and the two named violations are the thing to confirm.

- [ ] **Step 4: Write the failing guard test**

Create `tests/unit/test_import_contracts.py`:

```python
"""Architectural guard: the import-linter contracts must actually pass.

`lint-imports` caches its import graph in `.import_linter_cache/`. A stale
cache makes it report KEPT for contracts that are in fact broken, which is
worse than having no guard at all. This test always runs with --no-cache.
"""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# The console script, not `python -m importlinter.cli` — that module has no
# __main__ hook, exits 0 and prints nothing, which would make this guard pass
# vacuously forever. Resolving it next to sys.executable keeps it venv-correct.
LINT_IMPORTS = Path(sys.executable).parent / "lint-imports"


def test_lint_imports_executable_is_present():
    """If the console script moves, the guard below must fail loudly, not skip."""
    assert LINT_IMPORTS.exists(), f"lint-imports not found at {LINT_IMPORTS}"


def test_import_linter_contracts_pass_without_cache():
    result = subprocess.run(
        [str(LINT_IMPORTS), "--config", "pyproject.toml", "--no-cache"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    output = result.stdout + result.stderr
    # A silent success is not a success — it means nothing was evaluated.
    assert "Contracts:" in output, (
        "lint-imports produced no contract report; the guard would be vacuous:\n"
        + output
    )
    assert result.returncode == 0, (
        "import-linter contracts are broken (run with --no-cache to reproduce):\n"
        + output
    )
```

The `Contracts:` assertion is the point. Without it, any invocation that exits 0 without evaluating anything would satisfy this test — which is the same class of defect the test exists to catch.

- [ ] **Step 5: Run it to confirm it fails**

```bash
.venv/bin/python -m pytest tests/unit/test_import_contracts.py -q
```
Expected: FAIL, with the two violating imports from Step 3 in the assertion message. Leave it failing — Task 2 is what makes it pass.

Verified 2026-07-31: `python -m importlinter.cli lint-imports` prints nothing and exits 0 — the package has no `__main__` hook, so that invocation evaluates zero contracts. Use the console script as written above.

- [ ] **Step 6: Stop CI from trusting the cache**

In `.github/workflows/ci.yml`, change line 31 from:

```yaml
        run: lint-imports --config pyproject.toml
```

to:

```yaml
        run: lint-imports --config pyproject.toml --no-cache
```

Append to `.gitignore`:

```
.import_linter_cache/
```

Remove the stale cache from the working tree:

```bash
git rm -r --cached .import_linter_cache 2>/dev/null || true
rm -rf .import_linter_cache
```

- [ ] **Step 7: Confirm the rest of the suite is unaffected**

```bash
.venv/bin/python -m pytest tests/unit/ tests/contract/ -q --deselect tests/unit/test_import_contracts.py
```
Expected: `1679 passed`. Adding `__init__.py` files must not change any behaviour.

- [ ] **Step 8: Stage**

```bash
git add scalpr/adapters/__init__.py scalpr/engine/__init__.py \
        tests/unit/test_import_contracts.py .github/workflows/ci.yml .gitignore
```

Do not commit. `AGENTS.md` requires every staged state to pass the suite, and Task 1 deliberately leaves one test red — so Task 1 and Task 2 stage together and are only committable as a pair. If the user asks for a commit, do Task 2 first.

---

## Task 2: Give `risk` and `market_data` a port instead of `DhanClient`

The two violations Task 1 exposed are both a production module importing the concrete adapter. `session_guard` needs exactly two methods; `historical` does not use the client at all (`load_history` returns `[]`). A narrow Protocol fixes both and makes the broker a replaceable detail for these callers.

**Files:**
- Modify: `scalpr/domain/contracts.py`
- Modify: `scalpr/risk/session_guard.py:7`, `:18`
- Modify: `scalpr/market_data/historical.py:5`, `:12`

**Interfaces:**
- Consumes: Task 1's live guard.
- Produces: `scalpr.domain.contracts.ExecutionGatewayProtocol` (methods `get_positions()`, `place_order(order)`) and `scalpr.domain.contracts.HistoricalSourceProtocol` (method `get_historical(symbol, exchange, timeframe, lookback_days)`). `DhanClient` already satisfies both structurally — no adapter change is needed.

- [ ] **Step 1: Add the two ports**

`scalpr/domain/contracts.py` already hosts `HttpClientProtocol` and `ResolverProtocol` and already imports `Protocol` and `runtime_checkable`. Append after the existing protocol block:

```python
@runtime_checkable
class ExecutionGatewayProtocol(Protocol):
    """Outward port for order placement and position enquiry.

    Consumers in risk/, oms/ and strategy/ depend on this, never on a
    concrete broker adapter — the broker is a replaceable detail.
    """

    def get_positions(self) -> list[Any]:
        """Return current broker positions."""
        ...

    def place_order(self, order: Any) -> str:
        """Submit an order; return the broker's order id."""
        ...


@runtime_checkable
class HistoricalSourceProtocol(Protocol):
    """Outward port for historical candle retrieval."""

    def get_historical(
        self,
        symbol: str,
        exchange: str,
        timeframe: str,
        lookback_days: int,
    ) -> list[dict[str, Any]]:
        """Return raw historical candles for the given instrument."""
        ...
```

`Any` for `Position`/`Order` is deliberate: `scalpr.domain.contracts` must not grow an import edge to `scalpr.domain.position`, and the `Domain independence` contract is the thing keeping `domain/` clean. The concrete types are asserted at the call sites.

- [ ] **Step 2: Point `session_guard` at the port**

In `scalpr/risk/session_guard.py`, replace line 7:

```python
from scalpr.adapters.dhan.client import DhanClient
```

with:

```python
from scalpr.domain.contracts import ExecutionGatewayProtocol
```

and change the constructor signature at line 18:

```python
    def __init__(self, gateway: ExecutionGatewayProtocol, max_losses: int = 3) -> None:
```

The body is unchanged — it already only calls `self._client.get_positions()` (line 77) and `self._client.place_order(...)` (line 82).

- [ ] **Step 3: Point `historical` at the port**

In `scalpr/market_data/historical.py`, replace line 5:

```python
from scalpr.adapters.dhan.client import DhanClient
```

with:

```python
from scalpr.domain.contracts import HistoricalSourceProtocol
```

and change line 12:

```python
    def __init__(self, client: HistoricalSourceProtocol):
```

- [ ] **Step 4: Run the guard test**

```bash
.venv/bin/python -m pytest tests/unit/test_import_contracts.py -q
```
Expected: PASS. Confirm directly too:

```bash
.venv/bin/lint-imports --config pyproject.toml --no-cache
```
Expected: `Contracts: 7 kept, 0 broken.`

- [ ] **Step 5: Run the full suite**

```bash
.venv/bin/python -m pytest tests/unit/ tests/contract/ -q
```
Expected: `1681 passed` (1679 + the two new guard tests).

- [ ] **Step 6: Stage**

```bash
git add scalpr/domain/contracts.py scalpr/risk/session_guard.py scalpr/market_data/historical.py
```

---

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

## Task 4: `_on_submit` captures the broker order id

R1's cure at the call site. The POST response is currently discarded on line 199.

**Files:**
- Modify: `scalpr/engine/execution_engine.py` (add `broker_order_id` to `OrderAccepted`)
- Modify: `scalpr/adapters/dhan/client.py` (`__init__`, `_on_submit`)
- Modify: `tests/unit/adapters/dhan/test_client.py`

**Interfaces:**
- Consumes: `OrderRegistry` from Task 3.
- Produces: `OrderAccepted` gains a field — `OrderAccepted(order_id: str, timestamp: datetime, broker_order_id: str = "")`. `DhanClient` gains a public read-only property `registry -> OrderRegistry`, consumed by `OrderWatcher` in Task 8.

- [ ] **Step 1: Stop the fixture from masking the bug**

`tests/unit/adapters/dhan/test_client.py` is `unittest.TestCase`-based: `TestDhanClientOnSubmit.setUp` (line 182) patches the adapter's collaborators, builds `self.client = DhanClient(self.bus, self.clock, self.config)`, and calls handlers directly as `self.client._on_submit(self.msg)`. Tests use `self.assertEqual` style.

Line 248 currently reads:

```python
        self.mock_http_client.post.return_value = {"orderId": "ord-1", "filledQuantity": 10}
```

The broker id `"ord-1"` is identical to the local `Order.order_id` (line 209), which hides the entire defect — sending the local id to the broker looks correct. Change it to a distinct value:

```python
        self.mock_http_client.post.return_value = {"orderId": "ORD123456", "orderStatus": "TRANSIT"}
```

- [ ] **Step 2: Write the failing tests**

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

- [ ] **Step 3: Run to verify they fail**

```bash
.venv/bin/python -m pytest tests/unit/adapters/dhan/test_client.py -q -k "TestDhanClientOnSubmit"
```
Expected: the three new tests FAIL with `AttributeError: 'DhanClient' object has no attribute 'registry'`. The pre-existing `test_publishes_order_accepted_on_success` must still pass — it asserts the *local* id, which does not change.

- [ ] **Step 4: Add the field to `OrderAccepted`**

In `scalpr/engine/execution_engine.py`, replace the `OrderAccepted` definition at lines 70-73:

```python
@dataclasses.dataclass(frozen=True)
class OrderAccepted:
    order_id: str
    timestamp: datetime
    broker_order_id: str = ""
```

The default keeps every existing construction site valid, including `FakeExchange`.

- [ ] **Step 5: Give the client a registry**

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

- [ ] **Step 6: Capture the id in `_on_submit`**

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

- [ ] **Step 7: Run to verify they pass**

```bash
.venv/bin/python -m pytest tests/unit/adapters/dhan/test_client.py tests/unit/engine/ -q
```
Expected: all pass.

- [ ] **Step 8: Full suite and stage**

```bash
.venv/bin/python -m pytest tests/unit/ tests/contract/ -q
git add scalpr/engine/execution_engine.py scalpr/adapters/dhan/client.py tests/unit/adapters/dhan/test_client.py
```
Expected: `1691 passed` (1688 after Task 3, plus 3).

---

## Task 5: Cancel addresses the broker's id and announces failure

R2 and half of R4. `DELETE /orders/{msg.order_id}` currently sends the local UUID, and a failure is swallowed with no event — so the engine, which has already marked the order CANCELLED, never learns the truth.

**Files:**
- Modify: `scalpr/engine/execution_engine.py` (add `OrderCancelRejected`)
- Modify: `scalpr/adapters/dhan/client.py` (`_on_cancel`)
- Modify: `tests/unit/adapters/dhan/test_client.py`

**Interfaces:**
- Consumes: `OrderRegistry` (Task 3), the registry populated by `_on_submit` (Task 4).
- Produces: `scalpr.engine.execution_engine.OrderCancelRejected(order_id: str, reason: str, timestamp: datetime)`, published on `exec.event.cancel_rejected.dhan`. Consumed by the engine in Task 7.

- [ ] **Step 1: Fix the two existing tests that encode the bug**

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

- [ ] **Step 2: Write the failing tests**

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

- [ ] **Step 3: Run to verify they fail**

```bash
.venv/bin/python -m pytest tests/unit/adapters/dhan/test_client.py -q -k TestDhanClientOnCancel
```
Expected: `test_sends_delete_request` FAILS (still sends the local id), and the two new tests FAIL on `ImportError: cannot import name 'OrderCancelRejected'`.

- [ ] **Step 4: Add the payload**

In `scalpr/engine/execution_engine.py`, add after `OrderCancelled`:

```python
@dataclasses.dataclass(frozen=True)
class OrderCancelRejected:
    order_id: str
    reason: str
    timestamp: datetime
```

- [ ] **Step 5: Rewrite `_on_cancel`**

In `scalpr/adapters/dhan/client.py`, add `OrderCancelRejected` to the existing `from scalpr.engine.execution_engine import (...)` block, then replace `_on_cancel` (currently `client.py:218-229`) with:

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

- [ ] **Step 6: Run to verify they pass**

```bash
.venv/bin/python -m pytest tests/unit/adapters/dhan/test_client.py -q
```
Expected: all pass.

- [ ] **Step 7: Stage**

```bash
git add scalpr/engine/execution_engine.py scalpr/adapters/dhan/client.py tests/unit/adapters/dhan/test_client.py
```

---

## Task 6: Modify addresses the broker's id and always terminates

The other half of R2/R4. `_on_modify` currently sends the local UUID and publishes **nothing at all** — not on success, not on failure. The engine has no way to know a modify landed.

**Files:**
- Modify: `scalpr/engine/execution_engine.py` (add `OrderModified`, `OrderModifyRejected`)
- Modify: `scalpr/adapters/dhan/client.py` (`_on_modify`)
- Modify: `tests/unit/adapters/dhan/test_client.py`

**Interfaces:**
- Consumes: `OrderRegistry` (Task 3), registry populated by `_on_submit` (Task 4).
- Produces: `OrderModified(order_id: str, updates: dict, timestamp: datetime)` on `exec.event.modified.dhan`, and `OrderModifyRejected(order_id: str, reason: str, timestamp: datetime)` on `exec.event.modify_rejected.dhan`. Both consumed by the engine in Task 7.

- [ ] **Step 1: Fix the existing test that encodes the bug**

`TestDhanClientOnModify.setUp` (line 354) never registers a broker id, and `test_sends_put_request` (line 381) asserts `put("/orders/ord-1", data={"quantity": 15})` — the *local* id. Seed the mapping in `setUp`, immediately after line 375 (`self.client = DhanClient(...)`):

```python
        self.client.registry.register("ord-1", "ORD123456")
```

and update the assertion at lines 383-385 to the broker's id:

```python
        self.mock_http_client.put.assert_called_once_with(
            "/orders/ORD123456", data={"quantity": 15},
        )
```

- [ ] **Step 2: Write the failing tests**

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

The existing `test_handles_error_gracefully` (line 387) still holds — `_on_modify` must not raise — but it now also gets a terminating event, which the new test asserts.

- [ ] **Step 3: Run to verify they fail**

```bash
.venv/bin/python -m pytest tests/unit/adapters/dhan/test_client.py -q -k modify
```
Expected: FAIL — `ImportError: cannot import name 'OrderModified'`.

- [ ] **Step 4: Add the payloads**

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

- [ ] **Step 5: Rewrite `_on_modify`**

Add `OrderModified` and `OrderModifyRejected` to the `from scalpr.engine.execution_engine import (...)` block in `client.py`, then replace `_on_modify` (currently `client.py:231-235`) with:

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

- [ ] **Step 6: Run and stage**

```bash
.venv/bin/python -m pytest tests/unit/adapters/dhan/test_client.py -q
git add scalpr/engine/execution_engine.py scalpr/adapters/dhan/client.py tests/unit/adapters/dhan/test_client.py
```
Expected: all pass, including the amended `test_sends_put_request`.

---

## Task 7: The engine waits for confirmation

R4 and R6. The engine currently marks an order CANCELLED the moment a strategy asks (`execution_engine.py:154`), and applies an arbitrary caller dict straight onto the frozen domain object (`execution_engine.py:166`) before the broker has agreed. Both make the local book lie.

**Files:**
- Modify: `scalpr/engine/execution_engine.py` (`start`, `_on_cancel`, `_on_modify`, add `_on_cancel_rejected`, `_on_modified`, `_on_modify_rejected`)
- Modify: `tests/unit/engine/test_execution_engine.py`

**Interfaces:**
- Consumes: `OrderCancelRejected` (Task 5), `OrderModified` / `OrderModifyRejected` (Task 6).
- Produces: `ExecutionEngine` subscribes to `exec.event.cancel_rejected.dhan`, `exec.event.modified.dhan`, `exec.event.modify_rejected.dhan`. `MODIFIABLE_FIELDS: frozenset[str]` is the module-level whitelist.

- [ ] **Step 1: Write the failing tests**

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

- [ ] **Step 2: Run to verify they fail**

```bash
.venv/bin/python -m pytest tests/unit/engine/test_execution_engine.py -q -k TestConfirmationDrivenLifecycle
```
Expected: FAIL — the first on `state == OrderState.CANCELLED` (the optimistic transition), the modify ones on the blind `dataclasses.replace`.

- [ ] **Step 3: Add the whitelist and the three subscriptions**

In `scalpr/engine/execution_engine.py`, add at module level after the payload dataclasses:

```python
# Fields a broker modify may legitimately change. Anything else arriving in a
# ModifyOrder.updates dict is a bug or an attack — never let it reach the
# frozen domain object.
MODIFIABLE_FIELDS: frozenset[str] = frozenset({"price", "quantity", "trigger_price"})
```

In `start`, add after line 120:

```python
        self._bus.subscribe("exec.event.cancel_rejected.dhan", self._on_cancel_rejected)
        self._bus.subscribe("exec.event.modified.dhan", self._on_modified)
        self._bus.subscribe("exec.event.modify_rejected.dhan", self._on_modify_rejected)
```

- [ ] **Step 4: Make cancel and modify intent-only**

Replace `_on_cancel` (lines 146-159) with:

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

Replace `_on_modify` (lines 161-168) with:

```python
    def _on_modify(self, cmd: ModifyOrder) -> None:
        self._event_store.append(cmd)
        order = self._cache.order(cmd.order_id)
        if order is None or order.state.is_terminal:
            return
        # Route the intent only; apply on exec.event.modified.<broker>.
        self._route("exec.command.modify", cmd.broker, cmd)
```

- [ ] **Step 5: Add the three confirmation handlers**

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

- [ ] **Step 6: Run the engine tests**

```bash
.venv/bin/python -m pytest tests/unit/engine/test_execution_engine.py -q
```
Expected: all pass. If a pre-existing test asserted the optimistic-cancel behaviour, it encoded the bug — update it to publish `exec.event.cancelled.dhan` before asserting CANCELLED, and note the change in the commit message.

- [ ] **Step 7: Full suite and stage**

```bash
.venv/bin/python -m pytest tests/unit/ tests/contract/ -q
git add scalpr/engine/execution_engine.py tests/unit/engine/test_execution_engine.py
```

---

## Task 8: `OrderWatcher` — the fill ingress that does not exist yet

R3, and the reason this plan exists. Nothing in production publishes `exec.event.filled.dhan`; the only two publishers are `tests/conftest.py:174` and `scalpr/adapters/test_helpers/fake_exchange.py:86`. `_ws.py` carries market data only. Until this lands, every live order reaches `OPEN` and stops — `filled_quantity`, `avg_price`, positions and PnL never move.

This polls `GET /orders`, the order book endpoint already used at `_order_client.py:114`. No new wire format is guessed. A push-based order-update WebSocket is a later optimisation, not a prerequisite.

**Files:**
- Modify: `scalpr/adapters/dhan/_mapper_orders.py` (add `"TRANSIT"`, add `order_book_entry_to_fill`)
- Create: `scalpr/adapters/dhan/_order_watcher.py`
- Create: `tests/unit/adapters/dhan/test_order_watcher.py`

**Interfaces:**
- Consumes: `OrderRegistry` (Task 3), `DhanClient.registry` (Task 4), `MessageBus`, `Clock`, and the Dhan HTTP client — typed `Any` and duck-called as `http.get("/orders", bucket="orders")`, exactly as `_order_client.py:114` already does against `DhanHttpClient.get(path, bucket="portfolio", **kwargs)` (`_http.py:138`).
- Produces: `scalpr.adapters.dhan._order_watcher.OrderWatcher(http, bus, clock, registry)` with method `poll_once() -> None`. Publishes `exec.event.filled.dhan` (`OrderFilled`), `exec.event.rejected.dhan` (`OrderRejected`), `exec.event.cancelled.dhan` (`OrderCancelled`). Also produces `scalpr.adapters.dhan._mapper_orders.order_book_entry_to_fill(entry: dict, local_order_id: str, delta_quantity: int) -> Fill`.

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/adapters/dhan/test_order_watcher.py`:

```python
"""OrderWatcher — turns the Dhan order book into lifecycle events.

Without this, nothing in production ever publishes exec.event.filled.dhan.
"""

from decimal import Decimal
from unittest.mock import MagicMock

from scalpr.adapters.dhan._order_registry import OrderRegistry
from scalpr.adapters.dhan._order_watcher import OrderWatcher
from scalpr.engine.clock import StaticClock
from scalpr.engine.message_bus import RecordingBus


def _watcher(book):
    http = MagicMock()
    http.get.return_value = book
    bus = RecordingBus()
    registry = OrderRegistry()
    registry.register("local-1", "ORD1")
    return OrderWatcher(http, bus, StaticClock(), registry), bus, http


def _entry(status, filled_qty, traded_price, order_id="ORD1"):
    return {
        "orderId": order_id,
        "orderStatus": status,
        "filledQuantity": filled_qty,
        "tradedPrice": traded_price,
        "quantity": 10,
    }


class TestOrderWatcherFills:
    def test_partial_fill_publishes_the_new_quantity_only(self):
        """A book showing 4 filled after 0 is a 4-lot fill, not a 4-lot total."""
        watcher, bus, _ = _watcher([_entry("PARTIALLY FILLED", 4, 2500.50)])

        watcher.poll_once()

        fills = bus.filter("exec.event.filled.dhan")
        assert len(fills) == 1
        fill = fills[0].payload.fill
        assert fill.order_id == "local-1"
        assert fill.quantity == 4
        assert fill.price == Decimal("2500.50")
        assert isinstance(fill.price, Decimal)

    def test_second_poll_publishes_only_the_delta(self):
        """Polling is idempotent on unchanged rows and emits deltas on changed
        rows — re-emitting the cumulative total would double-count the position."""
        watcher, bus, http = _watcher([_entry("PARTIALLY FILLED", 4, 2500.50)])
        watcher.poll_once()
        http.get.return_value = [_entry("TRADED", 10, 2501.00)]

        watcher.poll_once()

        fills = bus.filter("exec.event.filled.dhan")
        assert len(fills) == 2
        assert fills[1].payload.fill.quantity == 6

    def test_unchanged_book_publishes_nothing_further(self):
        watcher, bus, _ = _watcher([_entry("PARTIALLY FILLED", 4, 2500.50)])
        watcher.poll_once()

        watcher.poll_once()

        assert len(bus.filter("exec.event.filled.dhan")) == 1

    def test_zero_filled_quantity_publishes_no_fill(self):
        """An accepted-but-unfilled order is not a fill. Publishing a
        zero-quantity fill would corrupt avg_price to zero."""
        watcher, bus, _ = _watcher([_entry("TRANSIT", 0, None)])

        watcher.poll_once()

        assert len(bus.filter("exec.event.filled.dhan")) == 0


class TestOrderWatcherTerminalStates:
    def test_broker_rejection_publishes_rejected(self):
        watcher, bus, _ = _watcher([_entry("REJECTED", 0, None)])

        watcher.poll_once()

        rejected = bus.filter("exec.event.rejected.dhan")
        assert len(rejected) == 1
        assert rejected[0].payload.order_id == "local-1"

    def test_broker_cancellation_publishes_cancelled(self):
        watcher, bus, _ = _watcher([_entry("CANCELLED", 0, None)])

        watcher.poll_once()

        cancelled = bus.filter("exec.event.cancelled.dhan")
        assert len(cancelled) == 1
        assert cancelled[0].payload.order_id == "local-1"

    def test_terminal_state_is_published_once(self):
        watcher, bus, _ = _watcher([_entry("CANCELLED", 0, None)])
        watcher.poll_once()

        watcher.poll_once()

        assert len(bus.filter("exec.event.cancelled.dhan")) == 1


class TestOrderWatcherRobustness:
    def test_unmapped_broker_order_is_ignored(self):
        """Orders placed outside this process (manual, or a previous run) must
        not be invented into the local book."""
        watcher, bus, _ = _watcher([_entry("TRADED", 10, 2500.00, order_id="FOREIGN")])

        watcher.poll_once()

        assert len(bus.filter("exec.event.filled.dhan")) == 0

    def test_http_failure_does_not_raise(self):
        """The watcher runs on a heartbeat; one failed poll must not kill it."""
        watcher, bus, http = _watcher([])
        http.get.side_effect = RuntimeError("rate limited")

        watcher.poll_once()

        assert bus.recorded_events == []

    def test_unknown_status_is_skipped_not_fatal(self):
        watcher, bus, _ = _watcher([_entry("SOMETHING_NEW", 0, None)])

        watcher.poll_once()

        assert bus.recorded_events == []
```

- [ ] **Step 2: Run to verify they fail**

```bash
.venv/bin/python -m pytest tests/unit/adapters/dhan/test_order_watcher.py -q
```
Expected: FAIL — `ModuleNotFoundError: No module named 'scalpr.adapters.dhan._order_watcher'`.

- [ ] **Step 3: Teach the mapper about `TRANSIT` and add the fill mapper**

In `scalpr/adapters/dhan/_mapper_orders.py`, add to `_DHAN_STATUS_TO_STATE` (currently lines 42-52) — Dhan returns `TRANSIT` for a freshly accepted order and `order_status_from_dhan` currently raises `InvalidValueError` on it:

```python
    "TRANSIT": OrderState.PENDING,
```

Add this function after `response_to_fill`:

```python
def order_book_entry_to_fill(
    entry: dict,
    local_order_id: str,
    delta_quantity: int,
) -> Fill:
    """Build a Fill for the newly-executed quantity of an order-book row.

    `delta_quantity` is the increase since the last poll, not the cumulative
    filledQuantity — publishing the cumulative figure would double-count the
    position on every poll.
    """
    price_raw = entry.get("tradedPrice") or entry.get("averageTradedPrice")
    if price_raw is None:
        raise MissingFieldError("order book entry missing traded price")
    broker_order_id = entry.get("orderId")
    if not broker_order_id:
        raise MissingFieldError("order book entry missing 'orderId'")
    return Fill(
        fill_id=f"f_{broker_order_id}_{entry.get('filledQuantity')}",
        order_id=local_order_id,
        symbol=str(entry.get("tradingSymbol", "")),
        side=transaction_type_to_side(str(entry.get("transactionType", "BUY"))),
        quantity=delta_quantity,
        price=Decimal(str(price_raw)),
        timestamp=datetime.now(timezone.utc),
        exchange=str(entry.get("exchangeSegment", "")),
    )
```

If `transaction_type_to_side` does not already exist in this module (the inverse `transaction_type_from_side` is at line 94), add it:

```python
def transaction_type_to_side(transaction_type: str) -> OrderSide:
    value = transaction_type.strip().upper()
    if value == "BUY":
        return OrderSide.BUY
    if value == "SELL":
        return OrderSide.SELL
    raise InvalidValueError(f"Unknown Dhan transactionType: {transaction_type!r}")
```

- [ ] **Step 4: Write the watcher**

Create `scalpr/adapters/dhan/_order_watcher.py`:

```python
"""Order-book polling watcher — the adapter's fill ingress.

Dhan's POST /orders response only tells us the order was accepted. Execution
arrives later. This watcher polls GET /orders on a heartbeat, diffs each row
against what it last saw, and publishes the delta as domain events.

Deltas, not totals: filledQuantity is cumulative, so publishing it raw on
every poll would count the same lots repeatedly and inflate the position.
"""

from __future__ import annotations

import logging
from typing import Any

from scalpr.adapters.dhan._mapper_orders import (
    order_book_entry_to_fill,
    order_status_from_dhan,
)
from scalpr.adapters.dhan._order_registry import OrderRegistry
from scalpr.domain.order import OrderState
from scalpr.engine.clock import Clock
from scalpr.engine.execution_engine import (
    OrderCancelled,
    OrderFilled,
    OrderRejected,
)
from scalpr.engine.message_bus import MessageBus

logger = logging.getLogger(__name__)


class OrderWatcher:
    """Polls the Dhan order book and publishes lifecycle events for deltas."""

    def __init__(
        self,
        http: Any,
        bus: MessageBus,
        clock: Clock,
        registry: OrderRegistry,
    ) -> None:
        self._http = http
        self._bus = bus
        self._clock = clock
        self._registry = registry
        self._seen_filled: dict[str, int] = {}
        self._terminal: set[str] = set()

    def poll_once(self) -> None:
        """Fetch the order book and publish whatever changed. Never raises."""
        try:
            book = self._http.get("/orders", bucket="orders")
        except Exception as exc:
            logger.warning("order_book_poll_failed: %s", exc)
            return
        if not isinstance(book, list):
            logger.warning("order_book_unexpected_shape: %r", type(book))
            return
        for entry in book:
            try:
                self._process(entry)
            except Exception as exc:
                logger.warning(
                    "order_book_entry_skipped: orderId=%s error=%s",
                    entry.get("orderId") if isinstance(entry, dict) else "?",
                    exc,
                )

    def _process(self, entry: dict) -> None:
        broker_order_id = str(entry.get("orderId") or "")
        if not broker_order_id:
            return
        local_order_id = self._registry.local_id(broker_order_id)
        if local_order_id is None:
            # Placed outside this process — not ours to report on.
            return
        if broker_order_id in self._terminal:
            return

        try:
            state = order_status_from_dhan(str(entry.get("orderStatus", "")))
        except Exception as exc:
            logger.warning("order_status_unmapped: %s", exc)
            return

        self._emit_fill_delta(entry, broker_order_id, local_order_id)
        self._emit_terminal(state, broker_order_id, local_order_id)

    def _emit_fill_delta(
        self, entry: dict, broker_order_id: str, local_order_id: str
    ) -> None:
        raw_filled = entry.get("filledQuantity") or 0
        try:
            filled = int(raw_filled)
        except (TypeError, ValueError):
            return
        previous = self._seen_filled.get(broker_order_id, 0)
        delta = filled - previous
        if delta <= 0:
            return
        fill = order_book_entry_to_fill(entry, local_order_id, delta)
        self._seen_filled[broker_order_id] = filled
        self._bus.publish(
            "exec.event.filled.dhan",
            OrderFilled(
                order_id=local_order_id,
                fill=fill,
                timestamp=self._clock.timestamp(),
            ),
        )

    def _emit_terminal(
        self, state: OrderState, broker_order_id: str, local_order_id: str
    ) -> None:
        if state == OrderState.REJECTED:
            self._terminal.add(broker_order_id)
            self._bus.publish(
                "exec.event.rejected.dhan",
                OrderRejected(
                    order_id=local_order_id,
                    reason="rejected by broker",
                    timestamp=self._clock.timestamp(),
                ),
            )
        elif state in (OrderState.CANCELLED, OrderState.EXPIRED):
            self._terminal.add(broker_order_id)
            self._bus.publish(
                "exec.event.cancelled.dhan",
                OrderCancelled(
                    order_id=local_order_id,
                    timestamp=self._clock.timestamp(),
                ),
            )
        elif state == OrderState.FILLED:
            self._terminal.add(broker_order_id)
```

- [ ] **Step 5: Run to verify they pass**

```bash
.venv/bin/python -m pytest tests/unit/adapters/dhan/test_order_watcher.py -q
```
Expected: `10 passed`. If `test_http_failure_does_not_raise` fails on the `bucket="orders"` keyword, the `MagicMock` accepts it — the assertion is on `bus.recorded_events`, so a mismatch means the watcher raised; check the `try/except` in `poll_once`.

- [ ] **Step 6: Full suite and stage**

```bash
.venv/bin/python -m pytest tests/unit/ tests/contract/ -q
.venv/bin/lint-imports --config pyproject.toml --no-cache
git add scalpr/adapters/dhan/_order_watcher.py scalpr/adapters/dhan/_mapper_orders.py \
        tests/unit/adapters/dhan/test_order_watcher.py
```
Expected: suite green; `Contracts: 7 kept, 0 broken.`

---

## Validation

Run after every task, and all of it after Task 8.

```bash
# 1. Unit + contract suite — the AGENTS.md staging gate
.venv/bin/python -m pytest tests/unit/ tests/contract/ -q

# 2. Boundary contracts, with the cache bypassed
.venv/bin/lint-imports --config pyproject.toml --no-cache

# 3. Broker vocabulary guard (pre-existing)
.venv/bin/python -m pytest tests/unit/test_broker_boundary.py -q

# 4. Lint only what this plan touched — do not mass-fix the 12 pre-existing
#    client.py errors here; that is Phase C
.venv/bin/ruff check scalpr/adapters/dhan/_order_registry.py \
                     scalpr/adapters/dhan/_order_watcher.py \
                     scalpr/engine/execution_engine.py

# 5. Confirm the fill ingress now exists in production, not only in fakes
grep -rn "exec.event.filled" scalpr/ --include='*.py' | grep -v test_helpers
# Expected: a publisher in scalpr/adapters/dhan/_order_watcher.py
#           and the subscriber in scalpr/engine/execution_engine.py

# 6. Refresh the board
python3 .qoder/skills/kanban.cli/scripts/kanban.py scan
```

**Acceptance:** `1679 + N passed, 0 failed`; 7 contracts kept without cache; a production publisher of `exec.event.filled.dhan` exists; every `exec.command.*.dhan` handler in `client.py` has a terminating event on both the success and the failure branch.

---

## Risk Mitigation

| Risk | Why it matters | Mitigation |
|---|---|---|
| **`OrderRegistry` is in-memory; a restart orphans live orders.** Cancels for pre-restart orders will publish `cancel_rejected`. | An un-cancellable live position is the worst failure mode in this plan. | The local order id is already sent as `correlationId` (`_mapper_orders.py:216`). Follow-up task in the Phase B plan: `OrderWatcher` rebuilds the registry on first poll by mapping `entry["correlationId"] → entry["orderId"]`. Until then, the `cancel_rejected` event makes the condition loud rather than silent — which is the point. |
| **Polling latency.** A fill is visible only at the next poll. | Unsuitable for tight scalping. | Ship polling first because it uses a proven endpoint; add the Dhan order-update WebSocket as a push path in a later plan, keeping `OrderWatcher` as the reconciliation backstop. Do not guess the WS wire format — record a live payload into `tests/fixtures/dhan_responses/` first. |
| **`GET /orders` consumes the `orders` rate bucket.** | A tight poll interval could starve order placement. | `_http.get` defaults to `bucket="portfolio"`; the watcher passes `bucket="orders"` explicitly because that is the true cost. Default the heartbeat to no faster than 1s and make it configurable. Verify against `DHAN_BUCKETS` in `_http.py` before choosing the interval. |
| **`Task 7` may break tests that encoded the optimistic-cancel behaviour.** | A green suite that asserts a bug is worse than a red one. | Step 6 of Task 7 says explicitly: update such a test to publish the broker confirmation, and call it out. Do not weaken the new assertions to keep an old test passing. |
| **Task 1 leaves the suite red until Task 2.** | Violates the `AGENTS.md` staging gate if committed alone. | Tasks 1 and 2 stage together and are only committable as a pair. Stated in Task 1 Step 8. |
| **`OrderAccepted` gains a field.** | `FakeExchange` and existing tests construct it positionally or by keyword. | `broker_order_id: str = ""` is defaulted and last, so every existing construction remains valid. Verified by running the full suite at Task 4 Step 7. |
| **Removing `.import_linter_cache/` from the index changes CI timing.** | `--no-cache` re-analyses 132 files each run. | Measured cost is a full graph build on 132 files — seconds. Correctness beats the cache here; a guard that can report green on broken code has negative value. |

---

## Out of Scope (deliberately)

Recorded so nothing is lost, and so no implementer expands the blast radius mid-plan:

- The 12 ruff errors in `client.py`, the 605-line facade with 65 public methods, and the 1040-line `_resolver.py`. → Phase C plan.
- `tests/conftest.py:100`'s shadow `DhanClient` and making the contract suite exercise the real adapter. → Phase B plan. It becomes tractable once Task 8 gives the real adapter a fill path.
- `scalpr/api/routers/orders.py:83` publishing `exec.command.submit.dhan` directly, bypassing the engine's cache, event store and state machine. → Phase B plan.
- `scalpr/simulation/simulated_gateway.py:22-24` importing private `_http.PAPER_BUCKETS` / `RateLimiter`. → Phase B plan.
- `scalpr/api/bootstrap.py` reaching into `client._bus`, `client._clock`, `gateway._historical`. → Phase B plan.
- The Dhan order-update WebSocket. → later plan, after a live payload is recorded as a fixture.

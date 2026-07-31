# Task 8 brief — `OrderWatcher`: the fill ingress that does not exist yet

## Global Constraints (verbatim from the plan)

- Money is `Decimal`. Never `float` in a domain object. `Fill.price` and `Order.price` raise `TypeError` on non-`Decimal`.
- `Order`, `Fill`, and all `exec.*` payloads are `@dataclass(frozen=True)`. Mutation means `dataclasses.replace`.
- Time comes from the injected `Clock` (`clock.timestamp()` / `clock.utc_now()`). Never call `datetime.now()` in adapter or engine code paths added by this plan.
- Topic convention is `{domain}.{verb}.{broker}` for broker-directed and broker-emitted messages: commands `exec.command.<verb>.dhan`, events `exec.event.<verb>.dhan`. Engine-internal domain events stay unsuffixed (`domain.order.placed`, `domain.fill.received`).
- Never import a private module across a package boundary. `scalpr.adapters.dhan._http` is internal to the Dhan adapter.
- Production modules outside `scalpr/adapters/dhan/` must not import `DhanClient` concretely — depend on a Protocol from `scalpr.domain.contracts`.
- Staging discipline from `AGENTS.md`: `git add` only. **Never `git commit`** unless the user explicitly asks. Every staged state must pass `pytest tests/unit/ tests/contract/` with 0 failures.
- After any code change, re-run `python3 .qoder/skills/kanban.cli/scripts/kanban.py scan`.

## Task 8 (verbatim from the plan, lines 1204-1575)

R3, and the reason this plan exists. Nothing in production publishes `exec.event.filled.dhan`; the only two publishers are `tests/conftest.py:174` and `scalpr/adapters/test_helpers/fake_exchange.py:86`. `_ws.py` carries market data only. Until this lands, every live order reaches `OPEN` and stops — `filled_quantity`, `avg_price`, positions and PnL never move.

This polls `GET /orders`, the order book endpoint already used at `_order_client.py:114`. No new wire format is guessed. A push-based order-update WebSocket is a later optimisation, not a prerequisite.

**Files:**
- Modify: `scalpr/adapters/dhan/_mapper_orders.py` (add `"TRANSIT"`, add `order_book_entry_to_fill`)
- Create: `scalpr/adapters/dhan/_order_watcher.py`
- Create: `tests/unit/adapters/dhan/test_order_watcher.py`

**Interfaces:**
- Consumes: `OrderRegistry` (Task 3), `DhanClient.registry` (Task 4), `MessageBus`, `Clock`, and the Dhan HTTP client — typed `Any` and duck-called as `http.get("/orders", bucket="orders")`, exactly as `_order_client.py:114` already does against `DhanHttpClient.get(path, bucket="portfolio", **kwargs)` (`_http.py:138`).
- Produces: `scalpr.adapters.dhan._order_watcher.OrderWatcher(http, bus, clock, registry)` with method `poll_once() -> None`. Publishes `exec.event.filled.dhan` (`OrderFilled`), `exec.event.rejected.dhan` (`OrderRejected`), `exec.event.cancelled.dhan` (`OrderCancelled`). Also produces `scalpr.adapters.dhan._mapper_orders.order_book_entry_to_fill(entry: dict, local_order_id: str, delta_quantity: int) -> Fill`.

### Step 1: Write the failing tests

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

### Step 2: Run to verify they fail

```bash
.venv/bin/python -m pytest tests/unit/adapters/dhan/test_order_watcher.py -q
```

Expected: FAIL — `ModuleNotFoundError: No module named 'scalpr.adapters.dhan._order_watcher'`.

### Step 3: Teach the mapper about `TRANSIT` and add the fill mapper

In `scalpr/adapters/dhan/_mapper_orders.py`, add to `_DHAN_STATUS_TO_STATE` (currently lines 42-52) — Dhan returns `TRANSIT` for a freshly accepted order and `order_status_from_dhan` currently raises `InvalidValueError` on it:

```python
    "TRANSIT": OrderState.PENDING,
```

Add this function after `response_to_fill` (currently ends at line 83):

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

### Step 4: Write the watcher

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

### Step 5: Run to verify they pass

```bash
.venv/bin/python -m pytest tests/unit/adapters/dhan/test_order_watcher.py -q
```

Expected: `10 passed`.

### Step 6: Full suite and stage

```bash
.venv/bin/python -m pytest tests/unit/ tests/contract/ -q
.venv/bin/lint-imports --config pyproject.toml --no-cache
git add scalpr/adapters/dhan/_order_watcher.py scalpr/adapters/dhan/_mapper_orders.py \
        tests/unit/adapters/dhan/test_order_watcher.py
```

Expected: suite green (expect `1713 passed` — 1703 + 10 new); `Contracts: 7 kept, 0 broken.`

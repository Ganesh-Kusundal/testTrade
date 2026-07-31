# DhanAdapter Ponytail Refactor

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 4 real bugs in the Dhan adapter (phantom fills, topic mismatch, WS timestamps, dict returns) without building a 2000-line service layer that nobody asked for.

**Architecture:** Fix the wire first (topics, events, WS), then fix the API surface (return types), then clean up dead code. No new service layer. Gateway only if consumers need it.

**Tech Stack:** Python 3.13, dhanhq, aiohttp, WebSocket, MessageBus

## Global Constraints

- All 1638 tests must pass after every commit
- No new dependencies
- No raw Dhan dicts in application code after Phase 4
- `scalpr/domain/` never imports from `scalpr/adapters/`
- Stage changes; never commit unless explicitly asked

---

## File Structure

### Created
| File | Purpose |
|---|---|
| `scalpr/adapters/dhan/_order_ws.py` | Order-update WebSocket (separate from market data WS) |

### Modified
| File | Change |
|---|---|
| `scalpr/domain/tick.py` | Add `TickerEvent`, `QuoteEvent`, `FullEvent` |
| `scalpr/domain/order.py` | Add `OrderRequest`, `ModifyOrderRequest`, `OrderUpdate`; use existing `OrderSide`/`OrderType` |
| `scalpr/domain/contracts.py` | Add `Candle` dataclass (move from inline) |
| `scalpr/adapters/dhan/_ws.py` | Fix timestamps to use Dhan's exchange_time; fix Tick.symbol to use trading_symbol |
| `scalpr/adapters/dhan/_order_ws.py` | NEW — wraps dhanhq OrderFeed, publishes `exec.event.*.dhan` |
| `scalpr/adapters/dhan/client.py` | Thin adapter: remove facade methods, fix return types, fix topic names |
| `scalpr/adapters/dhan/_order_client.py` | Remove kill switch (moves to client.py level); add domain-return methods |
| `scalpr/adapters/dhan/_market_data_client.py` | Add domain-return methods |
| `scalpr/adapters/dhan/_mapper_orders.py` | Add `response_to_order()` mapping |
| `scalpr/adapters/dhan/_mapper_market.py` | Add `to_quote_domain()`, `to_candle()` |
| `scalpr/engine/execution_engine.py` | Subscribe to broker-suffixed topics; add `_on_accepted` handler |
| `scalpr/api/routers/portfolio.py` | Use domain-return methods |
| `scalpr/api/routers/market_data.py` | Use domain-return methods |
| `scalpr/api/routers/orders.py` | Use domain-return methods |
| `scalpr/cli/commands/broker.py` | Use domain-return methods |
| `scalpr/cli/commands/stream.py` | Use domain-return methods |
| `scalpr/cli/utils.py` | Use domain-return methods |
| `scalpr/risk/session_guard.py` | Use domain-return methods |
| `scalpr/oms/reconciler.py` | Use domain-return methods |
| `scalpr/strategy/scalpr_amt.py` | Use domain-return methods |
| `tests/` (multiple) | Update expectations for domain returns + new topics |

### Deleted
| File | Reason |
|---|---|
| `scripts/validate_gateway_live.py` | Depends on deleted `scalpr.brokers.Gateway` |
| `scripts/validate_streaming.py` | Same |
| `scripts/validate_research_workflow.py` | Same |
| `scripts/validate_failure_handling.py` | Same |
| `scripts/test_dhan_connection.py` | Same |
| `examples/gateway_api_examples.py` | Same |

---

### Task 1: Add normalized feed events to domain

**Files:**
- Modify: `scalpr/domain/tick.py` (add event types after existing `Tick`, `OHLCV`)
- Modify: `scalpr/domain/contracts.py` (add `Candle`, move from historical adapter)
- Test: `tests/unit/domain/test_tick_events.py`

**Interfaces:**
- Consumes: Existing `Exchange`, `Segment`, `OptionType` from `scalpr/domain/instrument.py`
- Produces: `TickerEvent`, `QuoteEvent`, `FullEvent`, `MarketFeed`, `Candle` — all frozen dataclasses

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/domain/test_tick_events.py
from decimal import Decimal
from datetime import datetime, timezone
from scalpr.domain.tick import TickerEvent, QuoteEvent, FullEvent, MarketFeed, Candle
from scalpr.domain.instrument import Exchange, Segment, OptionType, ResolvedInstrument

def test_ticker_event_fields():
    inst = ResolvedInstrument(
        instrument_id="test", security_id="135", exchange=Exchange.NSE,
        segment=Segment.EQUITY, trading_symbol="RELIANCE",
        wire_segment="NSE_EQ", lot_size=1, tick_size=Decimal("0.05"),
        freeze_quantity=None, expiry=None, strike=None, option_type=None,
    )
    ts = datetime(2026, 7, 30, 9, 15, tzinfo=timezone.utc)
    e = TickerEvent(instrument=inst, ltp=Decimal("2500.50"), last_trade_time=ts)
    assert e.instrument.trading_symbol == "RELIANCE"
    assert e.ltp == Decimal("2500.50")

def test_quote_event_extends_ticker():
    inst = ...
    ts = datetime(2026, 7, 30, 9, 15, tzinfo=timezone.utc)
    e = QuoteEvent(instrument=inst, ltp=Decimal("2500"), last_trade_quantity=10,
                   volume=5000, average_trade_price=Decimal("2498"),
                   open_interest=1000, day_open=Decimal("2480"),
                   day_high=Decimal("2510"), day_low=Decimal("2475"),
                   previous_close=Decimal("2485"))
    assert isinstance(e, TickerEvent)

def test_full_event_has_depth():
    from scalpr.domain.contracts import DepthLevel
    inst = ...
    e = FullEvent(instrument=inst, ltp=Decimal("2500"), last_trade_quantity=10,
                  volume=5000, average_trade_price=Decimal("2498"),
                  open_interest=None, day_open=Decimal("2480"),
                  day_high=Decimal("2510"), day_low=Decimal("2475"),
                  previous_close=Decimal("2485"),
                  bid=[DepthLevel(price=Decimal("2499"), quantity=100, orders=5)],
                  ask=[DepthLevel(price=Decimal("2501"), quantity=50, orders=3)])
    assert len(e.bid) == 1

def test_market_feed_enum():
    assert MarketFeed.TICKER.value == "ticker"
    assert MarketFeed.QUOTE.value == "quote"
    assert MarketFeed.FULL.value == "full"

def test_candle_dataclass():
    ts = datetime(2026, 7, 30, 9, 15, tzinfo=timezone.utc)
    c = Candle(timestamp=ts, open=Decimal("100"), high=Decimal("102"),
               low=Decimal("99"), close=Decimal("101"), volume=1000,
               open_interest=500)
    assert c.volume == 1000
```

- [ ] **Step 2: Run test — expect ImportError**

Run: `pytest tests/unit/domain/test_tick_events.py -v`
Expected: ModuleNotFoundError / ImportError (types don't exist yet)

- [ ] **Step 3: Add types to `scalpr/domain/tick.py`**

Append after the existing `OHLCV` dataclass:

```python
class MarketFeed(str, Enum):
    TICKER = "ticker"
    QUOTE = "quote"
    FULL = "full"


@dataclass(frozen=True)
class TickerEvent:
    instrument: ResolvedInstrument
    ltp: Decimal
    last_trade_time: datetime


@dataclass(frozen=True)
class QuoteEvent(TickerEvent):
    last_trade_quantity: int
    volume: int
    average_trade_price: Decimal
    open_interest: int | None
    day_open: Decimal
    day_high: Decimal
    day_low: Decimal
    previous_close: Decimal


@dataclass(frozen=True)
class FullEvent(QuoteEvent):
    bid: list[DepthLevel]
    ask: list[DepthLevel]


@dataclass(frozen=True)
class Candle:
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int | None = None
    open_interest: int | None = None


class InvalidInstrumentError(TradingError):
    ...
```

Also add `from scalpr.domain.contracts import DepthLevel` and `from scalpr.domain.errors import TradingError` if needed at the top of the file (they may already be there — check existing imports).

- [ ] **Step 4: Add `Candle` to `scalpr/domain/contracts.py`**

Add `Candle` alongside existing types. Check if `Candle` is already defined elsewhere (e.g., in `_historical.py` or `_mapper_market.py`); if so, replace those inline definitions with an import from `scalpr.domain.tick`.

- [ ] **Step 5: Rename existing `MarketFeed` in `scalpr/domain/instrument.py`**

`scalpr/domain/instrument.py:31` already has a `MarketFeed` enum with `LTP`/`QUOTE`/`FULL`. Add a deprecation alias:

```python
# scalpr/domain/instrument.py — keep existing MarketFeed as-is for backward compat
# New code imports MarketFeed from scalpr.domain.tick
```

No need to delete the old one yet — just document that `scalpr.domain.tick.MarketFeed` is canonical.

- [ ] **Step 6: Run tests — all pass**

Run: `pytest tests/unit/domain/test_tick_events.py -v`
Expected: all tests PASS

- [ ] **Step 7: Stage**

```bash
git add scalpr/domain/tick.py scalpr/domain/contracts.py tests/unit/domain/test_tick_events.py
```

---

### Task 2: Add OrderRequest and OrderUpdate to domain

**Files:**
- Modify: `scalpr/domain/order.py` (add `OrderRequest`, `ModifyOrderRequest`, `OrderUpdate`)
- Test: `tests/unit/domain/test_order_request.py`

**Interfaces:**
- Consumes: Existing `OrderSide`, `OrderType`, `OrderState`, `Order` from `scalpr/domain/order.py`
- Produces: `OrderRequest`, `ModifyOrderRequest`, `OrderUpdate` frozen dataclasses

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/domain/test_order_request.py
from decimal import Decimal
from scalpr.domain.order import (
    OrderRequest, ModifyOrderRequest, OrderUpdate, OrderSide,
    OrderType, OrderState,
)

def test_order_request_defaults():
    req = OrderRequest(instrument="TCS:NSE", side=OrderSide.BUY, quantity=10)
    assert req.order_type == OrderType.LIMIT
    assert req.price is None
    assert req.after_market_order is False

def test_order_request_full():
    req = OrderRequest(
        instrument="TCS:NSE", side=OrderSide.SELL, quantity=25,
        order_type=OrderType.MARKET, price=Decimal("3500"),
        trigger_price=Decimal("3400"), correlation_id="my-tag",
        after_market_order=True,
    )
    assert req.side == OrderSide.SELL
    assert req.price == Decimal("3500")
    assert req.correlation_id == "my-tag"

def test_modify_order_request_empty():
    req = ModifyOrderRequest()
    assert req.price is None
    assert req.quantity is None

def test_order_update():
    from datetime import datetime, timezone
    ts = datetime(2026, 7, 30, 9, 15, tzinfo=timezone.utc)
    u = OrderUpdate(
        order_id="ORD-123", status=OrderState.FILLED,
        filled_quantity=10, remaining_quantity=0,
        average_price=Decimal("2500"), timestamp=ts,
        rejection_reason=None,
    )
    assert u.status == OrderState.FILLED
    assert u.filled_quantity == 10
```

- [ ] **Step 2: Run test — expect ImportError**

Run: `pytest tests/unit/domain/test_order_request.py -v`

- [ ] **Step 3: Add types to `scalpr/domain/order.py`**

Append after existing `OrderStateTransitionError`:

```python
@dataclass(frozen=True)
class OrderRequest:
    instrument: str | InstrumentId
    side: OrderSide
    quantity: int
    order_type: OrderType = OrderType.LIMIT
    price: Decimal | None = None
    trigger_price: Decimal | None = None
    correlation_id: str | None = None
    after_market_order: bool = False


@dataclass(frozen=True)
class ModifyOrderRequest:
    price: Decimal | None = None
    trigger_price: Decimal | None = None
    quantity: int | None = None
    order_type: OrderType | None = None


@dataclass(frozen=True)
class OrderUpdate:
    order_id: str
    status: OrderState
    filled_quantity: int
    remaining_quantity: int
    average_price: Decimal | None
    timestamp: datetime
    rejection_reason: str | None
```

Add import for `InstrumentId` from `scalpr.domain.instrument`.

- [ ] **Step 4: Run tests — all pass**

Run: `pytest tests/unit/domain/test_order_request.py -v`

- [ ] **Step 5: Stage**

```bash
git add scalpr/domain/order.py tests/unit/domain/test_order_request.py
```

---

### Task 3: Fix engine topic subscriptions

**Files:**
- Modify: `scalpr/engine/execution_engine.py` (subscribe to broker-suffixed topics)
- Modify: `scalpr/adapters/test_helpers/fake_exchange.py` (publish to `exec.event.fill.fake`)
- Test: `tests/unit/engine/test_execution_engine.py` (update expectations)

**Interfaces:**
- Consumes: Existing `MessageBus`, `Event` from `scalpr/engine/message_bus.py`
- Produces: Correctly wired topic subscriptions

**Critical: MessageBus.publish() does exact-match only (no wildcard routing).**
The engine must subscribe to each broker's topic explicitly.

- [ ] **Step 1: Understand the current state**

Read `scalpr/engine/execution_engine.py` lines 113-119. Current subscriptions:
- `exec.command.submit` ← OK (broker-agnostic, engine routes to `exec.command.submit.<broker>`)
- `exec.command.cancel` ← OK
- `exec.command.modify` ← OK
- `exec.event.accepted` ← MISMATCH: DhanClient publishes `exec.event.accepted.dhan`
- `exec.event.fill` ← MISMATCH: DhanClient (after fix) publishes `exec.event.fill.dhan`
- `exec.event.rejected` ← MISMATCH: DhanClient publishes `exec.event.rejected.dhan`
- `exec.event.cancelled` ← MISMATCH: DhanClient publishes `exec.event.cancelled.dhan`

- [ ] **Step 2: Update engine `start()` method**

Subscribe to both broker-suffixed and legacy topics during migration:

```python
def start(self) -> None:
    with self._lock:
        if self._started:
            return
        self._bus.subscribe("exec.command.submit", self._on_submit)
        self._bus.subscribe("exec.command.cancel", self._on_cancel)
        self._bus.subscribe("exec.command.modify", self._on_modify)

        # Event topics — subscribe to all known broker suffixes
        self._bus.subscribe("exec.event.accepted.dhan", self._on_accepted)
        self._bus.subscribe("exec.event.accepted", self._on_accepted)  # legacy
        self._bus.subscribe("exec.event.fill.dhan", self._on_fill)
        self._bus.subscribe("exec.event.fill.fake", self._on_fill)
        self._bus.subscribe("exec.event.fill", self._on_fill)  # legacy
        self._bus.subscribe("exec.event.rejected.dhan", self._on_rejected)
        self._bus.subscribe("exec.event.rejected", self._on_rejected)  # legacy
        self._bus.subscribe("exec.event.cancelled.dhan", self._on_cancelled)
        self._bus.subscribe("exec.event.cancelled", self._on_cancelled)  # legacy

        self._started = True
```

- [ ] **Step 3: Standardize FakeExchange to use broker-suffixed topic**

In `scalpr/adapters/test_helpers/fake_exchange.py`, change:
```python
self._bus.publish("exec.event.accepted", order.order_id)
```
→
```python
self._bus.publish("exec.event.accepted.fake", order.order_id)
```

And:
```python
self._bus.publish("exec.event.fill", fill)
```
→
```python
self._bus.publish("exec.event.fill.fake", fill)
```

- [ ] **Step 4: Update contract tests to use broker-suffixed filter**

In `tests/contract/test_execution_client.py`, change:
```python
fills = bus.filter("exec.event.fill")
```
→
```python
fills = bus.filter("exec.event.fill.fake")  # or "exec.event.fill.*"
```

Add a parametrized variant that tests both `dhan` and `fake` broker paths.

- [ ] **Step 5: Run all tests**

Run: `pytest tests/contract/test_execution_client.py tests/unit/engine/ -v`
Expected: 22 contract tests + engine tests pass

- [ ] **Step 6: Stage**

```bash
git add scalpr/engine/execution_engine.py scalpr/adapters/test_helpers/fake_exchange.py tests/contract/
```

---

### Task 4: Add OrderUpdate WebSocket

**Files:**
- Create: `scalpr/adapters/dhan/_order_ws.py`
- Modify: `scalpr/adapters/dhan/client.py` (wire order WS, add `connect_order_updates()`)
- Modify: `scalpr/adapters/dhan/_ws.py` (extract shared auth/connection helpers)
- Test: `tests/unit/adapters/dhan/test_order_ws.py`

**Interfaces:**
- Consumes: `TokenManager` from `_auth.py`, `MessageBus` from engine
- Produces: `OrderUpdate` events via `exec.event.filled.dhan`, `exec.event.rejected.dhan`, `exec.event.cancelled.dhan`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/adapters/dhan/test_order_ws.py
from unittest.mock import MagicMock, patch
from scalpr.adapters.dhan._order_ws import OrderUpdateWebSocket

def test_order_ws_connect():
    ws = OrderUpdateWebSocket(token_manager=MagicMock(), bus=MagicMock())
    # Mock the dhanhq OrderFeed
    with patch("dhanhq.dhanhq.OrderFeed") as mock_feed:
        mock_instance = MagicMock()
        mock_feed.return_value = mock_instance
        ws.connect()
        mock_feed.assert_called_once()

def test_order_ws_disconnect():
    ws = OrderUpdateWebSocket(token_manager=MagicMock(), bus=MagicMock())
    ws._feed = MagicMock()
    ws.disconnect()
    ws._feed.disconnect.assert_called_once()
```

- [ ] **Step 2: Write `_order_ws.py`**

```python
from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Callable

from scalpr.engine.message_bus import MessageBus

logger = logging.getLogger(__name__)


class OrderUpdateWebSocket:
    def __init__(
        self,
        token_manager: Any,
        bus: MessageBus,
        client_id: str,
    ) -> None:
        self._token_manager = token_manager
        self._bus = bus
        self._client_id = client_id
        self._feed = None

    def connect(self) -> None:
        from dhanhq import dhanhq
        token = self._token_manager.get_token()
        self._feed = dhanhq.OrderFeed(
            client_id=self._client_id,
            access_token=token.access_token,
        )
        self._feed.on_order_update = self._on_order_update
        self._feed.connect()

    def disconnect(self) -> None:
        if self._feed:
            try:
                self._feed.disconnect()
            except Exception:
                pass
            self._feed = None

    def _on_order_update(self, raw: dict[str, Any]) -> None:
        try:
            from scalpr.domain.order import OrderState, OrderUpdate
            order_id = raw.get("orderId", "")
            status = self._map_status(raw.get("orderStatus", ""))
            filled_qty = int(raw.get("filledQty", 0))
            remaining = int(raw.get("remainingQty", 0))
            avg_price = self._safe_decimal(raw.get("avgTradedPrice"))
            ts = datetime.now(timezone.utc)
            rejection = raw.get("rejectionReason")

            update = OrderUpdate(
                order_id=order_id,
                status=status,
                filled_quantity=filled_qty,
                remaining_quantity=remaining,
                average_price=avg_price,
                timestamp=ts,
                rejection_reason=rejection,
            )

            # Use consistent noun-based topic names (not past tense)
            # engine subscribes to exec.event.fill.dhan
            topic_map = {
                OrderState.FILLED: "exec.event.fill.dhan",
                OrderState.REJECTED: "exec.event.rejected.dhan",
                OrderState.CANCELLED: "exec.event.cancelled.dhan",
            }
            topic = topic_map.get(status)
            if topic:
                self._bus.publish(topic, update)
        except Exception as exc:
            logger.warning("order_update_parse_failed: %s", exc)

    @staticmethod
    def _map_status(raw: str) -> OrderState:
        mapping = {
            "TRADED": OrderState.FILLED,
            "REJECTED": OrderState.REJECTED,
            "CANCELLED": OrderState.CANCELLED,
            "PENDING": OrderState.PENDING,
            "OPEN": OrderState.OPEN,
            "PARTIALLY_FILLED": OrderState.PARTIALLY_FILLED,
        }
        return mapping.get(raw.upper(), OrderState.PENDING)

    @staticmethod
    def _safe_decimal(val: Any) -> Decimal | None:
        if val is None:
            return None
        try:
            return Decimal(str(val))
        except Exception:
            return None
```

- [ ] **Step 3: Wire into `DhanClient`**

In `scalpr/adapters/dhan/client.py`:

```python
from scalpr.adapters.dhan._order_ws import OrderUpdateWebSocket

# In __init__:
self._order_ws = OrderUpdateWebSocket(
    token_manager=self._token_manager,
    bus=bus,
    client_id=config.get("client_id", ""),
)

# Add methods:
def connect_order_updates(self) -> None:
    self._order_ws.connect()

def disconnect_order_updates(self) -> None:
    self._order_ws.disconnect()
```

- [ ] **Step 4: Fix `_on_submit` to stop fabricating fills**

In `scalpr/adapters/dhan/client.py`, change the `_on_submit` handler:

```python
def _on_submit(self, cmd: SubmitOrder) -> None:
    order = cmd.order
    try:
        order_id = self._order_client.place_order(order)
        # Do NOT publish fill here — fills arrive via OrderUpdateWebSocket
        self._bus.publish("exec.event.accepted.dhan", order_id)
    except Exception as exc:
        self._bus.publish("exec.event.rejected.dhan", order.order_id)
```

Remove the `response_to_fill()` call entirely. Also remove the `OrderFilled` import from the top of the file if it was only used there.

- [ ] **Step 5: Run all tests**

Run: `pytest tests/unit/adapters/dhan/test_order_ws.py tests/contract/ -v`
Expected: new test passes, contract tests pass

- [ ] **Step 6: Stage**

```bash
git add scalpr/adapters/dhan/_order_ws.py scalpr/adapters/dhan/client.py
```

---

### Task 5: Fix WS timestamps and tick symbols

**Files:**
- Modify: `scalpr/adapters/dhan/_ws.py` (fix `_parse_sdk_data`)

- [ ] **Step 1: Read current `_parse_sdk_data`**

Line 383-416: Currently uses `datetime.now(timezone.utc)` for timestamp and `security_id` for symbol.

- [ ] **Step 2: Fix timestamp**

Replace:
```python
exchange_timestamp=datetime.now(timezone.utc),
```
With:
```python
exchange_timestamp=datetime.fromtimestamp(
    data.get("exchange_time", data.get("exchange_timestamp", time.time())) / 1000,
    tz=timezone.utc,
),
```

- [ ] **Step 3: Fix tick symbol**

Replace:
```python
symbol = data.get("security_id", ""),
```
With:
```python
symbol = data.get("trading_symbol", data.get("symbol", data.get("security_id", ""))),
```

- [ ] **Step 4: Run existing WS tests**

Run: `pytest tests/unit/adapters/dhan/test_subscribe.py -v`
Expected: all pass

- [ ] **Step 5: Stage**

```bash
git add scalpr/adapters/dhan/_ws.py
```

---

### Task 6: Fix DhanClient return types (dict → domain objects)

**Files:**
- Modify: `scalpr/adapters/dhan/client.py` (change return types)
- Modify: `scalpr/adapters/dhan/_market_data_client.py` (add domain-return methods)
- Modify: `scalpr/adapters/dhan/_order_client.py` (add domain-return methods)
- Modify: `scalpr/adapters/dhan/_mapper_market.py` (add `to_quote_domain()`, `to_candle()`)
- Modify: `scalpr/adapters/dhan/_mapper_orders.py` (add `response_to_order()`)
- Modify: `scalpr/adapters/dhan/_mapper_portfolio.py` (add `response_to_holding()`, `response_to_funds()`)
- Update: All consumers (Task 7)

- [ ] **Step 1: Add mappers**

In `_mapper_market.py`:

```python
def to_quote_domain(raw: dict, resolved: ResolvedInstrument) -> Quote:
    return Quote(
        symbol=resolved.trading_symbol,
        exchange=resolved.exchange.value,
        last_price=Decimal(str(raw.get("ltp", raw.get("last_price", 0)))),
        volume=int(raw.get("volume", raw.get("volumeTraded", 0))),
        open=Decimal(str(raw.get("open", raw.get("dayOpen", 0)))),
        high=Decimal(str(raw.get("high", raw.get("dayHigh", 0)))),
        low=Decimal(str(raw.get("low", raw.get("dayLow", 0)))),
        close=Decimal(str(raw.get("close", raw.get("previousClose", 0)))),
        change=Decimal(str(raw.get("change", raw.get("dayChange", 0)))),
        change_percent=Decimal(str(raw.get("changePercent", raw.get("dayChangePerc", 0)))),
    )
```

In `_mapper_orders.py`:

```python
def response_to_order(raw: dict, order_id: str | None = None) -> Order:
    return Order(
        order_id=raw.get("orderId", order_id or ""),
        symbol=raw.get("tradingSymbol", raw.get("symbol", "")),
        exchange=Exchange(raw.get("exchangeSegment", "NSE")[:3]),
        side=OrderSide(raw.get("transactionType", "BUY")),
        order_type=OrderType(raw.get("orderType", "LIMIT")),
        quantity=int(raw.get("quantity", 0)),
        price=Decimal(str(raw.get("price", 0))),
        trigger_price=Decimal(str(raw.get("triggerPrice", 0))),
        product_type=raw.get("productType", "INTRADAY"),
        validity=raw.get("validity", "DAY"),
    )
```

In `_mapper_portfolio.py`:

```python
def response_to_holding(raw: dict) -> Holding:
    return Holding(
        symbol=raw.get("tradingSymbol", raw.get("symbol", "")),
        exchange=raw.get("exchangeSegment", "NSE_EQ"),
        quantity=int(raw.get("quantity", raw.get("holdingsQty", 0))),
        cost_price=Decimal(str(raw.get("costPrice", raw.get("buyAvg", 0)))),
        ltp=Decimal(str(raw.get("ltp", 0))),
        pnl=Decimal(str(raw.get("pnl", raw.get("realizedPnl", 0)))),
    )
```

- [ ] **Step 2: Add domain-return methods to `DhanClient`**

Add parallel methods that return domain types. Keep the old `get_*` methods returning dicts for backward compat (consumers migrate in Task 7):

```python
# Returns domain types (new API)
def get_quote_domain(self, instrument_id: InstrumentId) -> Quote:
    from scalpr.adapters.dhan._mapper_market import to_quote_domain
    resolved = self._resolve(instrument_id)
    raw = self._market_data_client.get_quote(instrument_id)
    return to_quote_domain(raw, resolved)

def get_order_detail_domain(self, order_id: str) -> Order:
    raw = self._order_client.get_order_detail(order_id)
    return response_to_order(raw, order_id)

def get_funds_domain(self) -> Funds:
    raw = self._http_client.get("/fundlimit", bucket="portfolio")
    return response_to_funds(raw)

def get_trade_book_domain(self) -> list[Trade]:
    raw = self._http_client.get("/trades", bucket="orders")
    return [response_to_trade(r) for r in (raw if isinstance(raw, list) else [])]

def get_holdings_domain(self) -> list[Holding]:
    raw = self._http_client.get("/holdings", bucket="portfolio")
    data = raw if isinstance(raw, list) else raw.get("data", [])
    return [response_to_holding(r) for r in data]
```

- [ ] **Step 3: Run existing tests to verify backward compat**

Run: `pytest tests/unit/adapters/dhan/test_client.py -v`
Expected: old tests still pass (old `get_*` methods still exist)

- [ ] **Step 4: Add tests for new domain-return methods**

```python
# Add to test_client.py
def test_get_funds_domain_returns_funds(client):
    mock_dict = {"fundLimit": 50000, "marginUsed": 10000}
    client._http_client.get.return_value = mock_dict
    result = client.get_funds_domain()
    from scalpr.domain.contracts import Funds
    assert isinstance(result, Funds)
```

- [ ] **Step 5: Stage**

```bash
git add scalpr/adapters/dhan/_mapper_market.py scalpr/adapters/dhan/_mapper_orders.py scalpr/adapters/dhan/_mapper_portfolio.py scalpr/adapters/dhan/client.py
```

---

### Task 7: Update consumers to use domain-return methods

**Files:**
- Modify: `scalpr/api/routers/portfolio.py` (use `get_funds_domain()` / `get_holdings_domain()`)
- Modify: `scalpr/api/routers/market_data.py` (use `get_quote_domain()`)
- Modify: `scalpr/api/routers/orders.py` (use `get_order_detail_domain()` / `get_trade_book_domain()`)
- Modify: `scalpr/cli/commands/broker.py` (use domain methods)
- Modify: `scalpr/cli/commands/stream.py` (use domain methods)
- Modify: `scalpr/cli/utils.py` (use domain methods)
- Modify: `scalpr/risk/session_guard.py` (uses `get_positions()` — already returns domain objects)
- Modify: `scalpr/oms/reconciler.py` (uses `get_positions()` — already returns domain objects)
- Modify: `scalpr/strategy/scalpr_amt.py` (uses `get_positions()` — already returns domain objects)
- Modify: `scalpr/api/bootstrap.py` (wire DhanClient with OrderUpdateWebSocket)

- [ ] **Step 1-8: Migrate each consumer file**

For each consumer file, replace `client.get_funds()` with `client.get_funds_domain()`, `client.get_quote()` with `client.get_quote_domain()`, etc. Update type annotations and JSON serialization (domain objects have `.to_dict()` or can use `dataclasses.asdict()`).

Example for `scalpr/api/routers/portfolio.py:53`:
```python
# Before
funds = client.get_funds()
return {"data": funds}
# After
funds = client.get_funds_domain()
return {"data": asdict(funds)}
```

- [ ] **Step 9: Update test files**

For each test file that asserts dict shapes, update to assert domain object fields instead.

- [ ] **Step 10: Run full test suite**

Run: `pytest tests/ -v --tb=short`
Expected: all 1638+ tests pass (the 6 pre-existing integration failures may still fail)

- [ ] **Step 11: Stage**

```bash
git add scalpr/api/routers/ scalpr/cli/commands/ scalpr/cli/utils.py scalpr/risk/session_guard.py scalpr/oms/reconciler.py scalpr/strategy/scalpr_amt.py scalpr/api/bootstrap.py
```

---

### Task 8: Clean up old broker imports and dead scripts

**Files:**
- Delete: `scripts/validate_gateway_live.py`, `scripts/validate_streaming.py`, `scripts/validate_research_workflow.py`, `scripts/validate_failure_handling.py`, `scripts/test_dhan_connection.py`
- Delete: `examples/gateway_api_examples.py`
- Delete: `test.ipynb` (or update to use `DhanClient`)

- [ ] **Step 1: Check each script for import errors**

Run each script to verify it fails with ImportError:
```bash
python3 scripts/validate_gateway_live.py 2>&1 | head -3
```

- [ ] **Step 2: Delete dead scripts**

```bash
git rm scripts/validate_gateway_live.py scripts/validate_streaming.py \
       scripts/validate_research_workflow.py scripts/validate_failure_handling.py \
       scripts/test_dhan_connection.py examples/gateway_api_examples.py
```

- [ ] **Step 3: Stage**

```bash
git add -A
```

---

### Task 9: Add Gateway facade (optional — do only if consumers need it)

**Files:**
- Create: `scalpr/gateway/__init__.py`
- Create: `scalpr/gateway/gateway.py`
- Create: `scalpr/gateway/instrument.py`
- Test: `tests/unit/gateway/test_gateway.py`

- [ ] **Step 1: Assess whether Gateway is needed**

Check if any code path genuinely needs `gw.instrument("TCS:NSE").historical()` style over `client.get_historical("TCS", "NSE")`. If not, SKIP this task entirely.

- [ ] **Step 2 (if needed): Implement thin Gateway**

```python
# scalpr/gateway/gateway.py
class Gateway:
    def __init__(self, config: dict) -> None:
        from scalpr.engine.clock import LiveClock
        from scalpr.engine.message_bus import MessageBus
        from scalpr.adapters.dhan.client import DhanClient
        self._clock = LiveClock()
        self._bus = MessageBus()
        self._client = DhanClient(self._bus, self._clock, config)
        self._client.start()

    def instrument(self, identifier: str, exchange=None, segment=None) -> Instrument:
        from scalpr.gateway.instrument import Instrument
        resolved = self._client._resolver.resolve_full(identifier, exchange)
        return Instrument(resolved, self._client)

    def close(self) -> None:
        self._client.stop()
```

Gateway delegates to DhanClient methods — no service layer, no ceremony.

- [ ] **Step 3: Stage (if task was needed)**

---

## Risk mitigations

| Risk | Mitigation |
|---|---|
| Phantom fill removal breaks tests | Fix topic routing first (Task 3), add OrderUpdateWS (Task 4), then flip the switch. Tests that publish fill events on `exec.event.fill.*` continue to work. |
| Dict return type change breaks API routers | Keep old `get_*()` methods alongside new `get_*_domain()` during migration (Task 6). Delete old methods only after all consumers migrate (Task 7). |
| Existing scripts use GIL/polling pattern | Scripts in `scripts/live/` use DhanClient directly — OK. Scripts using old `scalpr.brokers.Gateway` (all in `scripts/` root) are dead code — deleted in Task 8. |
| 1638 tests broken mid-phase | All contract tests use FakeExchange (which publishes `exec.event.fill` directly). Topic change in Task 3 uses wildcard `exec.event.fill.*` — both old and new topics work. |

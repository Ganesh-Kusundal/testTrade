# Gateway + Domain Services Refactor

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the `DhanClient` god-object with a proper `Gateway` facade that delegates to domain services, fix critical event-routing bugs (topic mismatch, phantom fills), and normalize all return types to domain objects — matching the v0/v1 infrastructure specification.

**Architecture:** Gateway facade delegates to domain services (OrderService, PortfolioService, AccountService, MarketDataService, OptionChainService, RiskService, TraderControlService, OrderUpdateService). DhanClient becomes a thin adapter that returns domain objects. ExecutionEngine subscribes to broker-specific topics that DhanClient actually publishes on.

**Tech Stack:** Python 3.13, pytest, dhanhq SDK, pandas, mibian, requests, pyotp, concurrent.futures

## Global Constraints

- All tests must pass: `pytest tests/unit/ tests/contract/` with 0 failures
- No raw Dhan dicts in application-facing return types — all methods return domain objects
- Wire-segment mapping in exactly one module (`scalpr/adapters/dhan/_resolver.py`)
- No guessing of derivative contracts — resolver must raise `InstrumentNotFound`
- Zero-parity: backtest, replay, and live must share identical logic
- DhanClient must remain the sole adapter — no new broker adapters
- TDD: every new function/method has a failing test first
- Frequent commits per task

---

## Task 1: Fix Event Topic Routing (Critical Bug)

**Files:**
- Modify: `scalpr/engine/execution_engine.py:110-120` (subscribe to broker-specific topics)
- Modify: `scalpr/adapters/dhan/client.py:180-198` (publish on `exec.event.accepted.dhan` not `exec.event.filled.dhan`)
- Test: `tests/unit/engine/test_execution_engine.py` (add test for accepted/filled/cancelled/rejected routing)

**Interfaces:**
- Consumes: `SubmitOrder`, `OrderAccepted`, `OrderFilled`, `OrderRejected`, `OrderCancelled` from `scalpr.engine.execution_engine`
- Produces: Fixed topic routing so engine receives all broker events

**Steps:**

- [ ] **Step 1: Write failing test for topic routing**

```python
def test_engine_receives_broker_specific_events():
    """Engine must subscribe to exec.event.accepted.dhan, filled.dhan, rejected.dhan, cancelled.dhan."""
    bus = RecordingBus()
    clock = StaticClock()
    engine = ExecutionEngine(bus, clock)
    engine.start()

    # Verify engine subscribed to broker-specific topics
    assert "exec.event.accepted.dhan" in bus._subscribers
    assert "exec.event.filled.dhan" in bus._subscribers
    assert "exec.event.rejected.dhan" in bus._subscribers
    assert "exec.event.cancelled.dhan" in bus._subscribers
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/unit/engine/test_execution_engine.py::test_engine_receives_broker_specific_events -v`
Expected: FAIL

- [ ] **Step 3: Fix ExecutionEngine subscriptions**

In `execution_engine.py`, change `start()` to subscribe to broker-specific topics:

```python
def start(self) -> None:
    self._bus.subscribe("exec.command.submit", self._on_submit)
    self._bus.subscribe("exec.command.cancel", self._on_cancel)
    self._bus.subscribe("exec.command.modify", self._on_modify)
    # Broker-specific event topics
    self._bus.subscribe("exec.event.accepted.dhan", self._on_accepted)
    self._bus.subscribe("exec.event.filled.dhan", self._on_fill)
    self._bus.subscribe("exec.event.rejected.dhan", self._on_rejected)
    self._bus.subscribe("exec.event.cancelled.dhan", self._on_cancelled)
    self._running = True
```

- [ ] **Step 4: Fix DhanClient._on_submit to publish accepted, not filled**

In `client.py`, change `_on_submit` to publish `OrderAccepted` instead of fabricating a `Fill`:

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
        order_id = resp.get("orderId", "")
        self._bus.publish(
            "exec.event.accepted.dhan",
            OrderAccepted(
                order_id=order.order_id,
                timestamp=self._clock.timestamp(),
            ),
        )
    except Exception as exc:
        logger.error("submit_failed: %s", exc)
        self._bus.publish(
            "exec.event.rejected.dhan",
            OrderRejected(
                order_id=order.order_id,
                reason=str(exc),
                timestamp=self._clock.timestamp(),
            ),
        )
```

Add `OrderAccepted` import to `client.py`.

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/unit/engine/test_execution_engine.py tests/unit/adapters/dhan/test_client.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add scalpr/engine/execution_engine.py scalpr/adapters/dhan/client.py tests/unit/engine/test_execution_engine.py
git commit -m "fix: route broker-specific event topics correctly, publish OrderAccepted on submit"
```

---

## Task 2: Add OrderAccepted to ExecutionEngine

**Files:**
- Modify: `scalpr/engine/execution_engine.py` (add `OrderAccepted` dataclass and `_on_accepted` handler)
- Test: `tests/unit/engine/test_execution_engine.py`

**Interfaces:**
- Consumes: `OrderAccepted` (new), `OrderFilled`, `OrderRejected`, `OrderCancelled` from execution_engine
- Produces: Order state transitions PENDING → OPEN

**Steps:**

- [ ] **Step 1: Write failing test for OrderAccepted**

```python
def test_order_accepted_transitions_to_open():
    """OrderAccepted event transitions order from PENDING to OPEN."""
    bus = RecordingBus()
    clock = StaticClock()
    engine = ExecutionEngine(bus, clock)
    engine.start()

    order = Order(
        order_id="test-1", symbol="RELIANCE", exchange=Exchange.NSE,
        side=OrderSide.BUY, order_type=OrderType.LIMIT,
        quantity=10, price=Decimal("2500.00"),
    )
    bus.publish("exec.command.submit", SubmitOrder(order=order, broker="dhan"))

    # Order should be OPEN after accepted
    accepted = bus.filter("exec.event.accepted.*")
    assert len(accepted) == 1

    cached = engine.cache.order("test-1")
    assert cached is not None
    assert cached.state == OrderState.OPEN
```

- [ ] **Step 2: Run test to verify it fails**

- [ ] **Step 3: Add OrderAccepted dataclass and handler**

```python
@dataclasses.dataclass(frozen=True)
class OrderAccepted:
    order_id: str
    timestamp: datetime
```

Add `_on_accepted` handler to `ExecutionEngine`:

```python
def _on_accepted(self, payload: Any) -> None:
    order_id = payload.order_id if hasattr(payload, "order_id") else str(payload)
    order = self._cache.order(order_id)
    if order is None:
        return
    try:
        accepted = order.transition_to(OrderState.OPEN)
        self._cache.update(accepted)
        self._event_store.append(
            OrderAccepted(order_id=order_id, timestamp=self._clock.utc_now())
        )
    except ValueError:
        pass
```

- [ ] **Step 4: Run tests to verify they pass**

- [ ] **Step 5: Commit**

---

## Task 3: Add Domain Types for Gateway API

**Files:**
- Modify: `scalpr/domain/order.py` (add `Side`, `ProductType`, `Validity`, `OrderRequest`, `ModifyOrderRequest`)
- Modify: `scalpr/domain/tick.py` (add `TickerEvent`, `QuoteEvent`, `FullEvent`, `DepthLevel`, fix `MarketFeed`)
- Modify: `scalpr/domain/contracts.py` (move `DepthLevel` to tick.py, add `OHLC`)
- Test: `tests/unit/domain/test_order.py`, `tests/unit/domain/test_tick.py`

**Interfaces:**
- Consumes: `Exchange`, `Segment`, `OptionType`, `ResolvedInstrument` from domain
- Produces: `Side`, `ProductType`, `Validity`, `OrderRequest`, `ModifyOrderRequest`, `MarketFeed`, `TickerEvent`, `QuoteEvent`, `FullEvent`, `DepthLevel`, `OHLC`

**Steps:**

- [ ] **Step 1: Write failing tests for new domain types**

```python
# tests/unit/domain/test_order.py
def test_order_request_defaults():
    req = OrderRequest(
        instrument=Instrument(symbol="TCS", exchange=Exchange.NSE, segment=Segment.EQUITY,
                              security_id="112833", lot_size=1, tick_size=Decimal("0.05")),
        side=Side.BUY,
        quantity=10,
    )
    assert req.order_type == OrderType.LIMIT
    assert req.product == ProductType.INTRADAY
    assert req.validity == Validity.DAY
    assert req.price is None
    assert req.trigger_price is None

def test_modify_order_request_defaults():
    mod = ModifyOrderRequest()
    assert mod.price is None
    assert mod.quantity is None
    assert mod.order_type is None
```

```python
# tests/unit/domain/test_tick.py
def test_market_feed_enum():
    assert MarketFeed.TICKER.value == "ticker"
    assert MarketFeed.QUOTE.value == "quote"
    assert MarketFeed.FULL.value == "full"

def test_ticker_event():
    inst = ResolvedInstrument(
        instrument_id=SimpleInstrumentId("TCS", Exchange.NSE),
        security_id="112833", exchange=Exchange.NSE, segment=Segment.EQUITY,
        trading_symbol="TCS", wire_segment="NSE_EQ",
        lot_size=1, tick_size=Decimal("0.05"), freeze_quantity=None,
        expiry=None, strike=None, option_type=None,
    )
    event = TickerEvent(instrument=inst, ltp=Decimal("100.00"),
                        last_trade_time=datetime(2024, 1, 1, tzinfo=timezone.utc))
    assert event.instrument.resolved.trading_symbol == "TCS"
    assert event.ltp == Decimal("100.00")
```

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Add types to domain/order.py**

```python
class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class ProductType(str, Enum):
    INTRADAY = "INTRADAY"
    CNC = "CNC"
    MARGIN = "MARGIN"
    MTF = "MTF"
    CO = "CO"
    BO = "BO"

class Validity(str, Enum):
    DAY = "DAY"
    IOC = "IOC"
    GTD = "GTD"
    GTC = "GTC"

@dataclass(frozen=True)
class OrderRequest:
    instrument: Instrument
    side: Side
    quantity: int
    order_type: OrderType = OrderType.LIMIT
    product: ProductType = ProductType.INTRADAY
    validity: Validity = Validity.DAY
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
    validity: Validity | None = None
```

- [ ] **Step 4: Add types to domain/tick.py**

```python
class MarketFeed(str, Enum):
    TICKER = "ticker"
    QUOTE = "quote"
    FULL = "full"

@dataclass(frozen=True)
class DepthLevel:
    price: Decimal
    quantity: int
    orders: int = 1

@dataclass(frozen=True)
class TickerEvent:
    instrument: ResolvedInstrument
    ltp: Decimal
    last_trade_time: datetime

@dataclass(frozen=True)
class QuoteEvent:
    instrument: ResolvedInstrument
    ltp: Decimal
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
class OHLC:
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    timestamp: datetime | None = None
```

- [ ] **Step 5: Run tests to verify they pass**

- [ ] **Step 6: Commit**

```bash
git add scalpr/domain/order.py scalpr/domain/tick.py tests/unit/domain/test_order.py tests/unit/domain/test_tick.py
git commit -m "feat(domain): add OrderRequest, Side, ProductType, Validity, MarketFeed, TickerEvent, QuoteEvent, FullEvent, DepthLevel, OHLC"
```

---

## Task 4: Create Subscription Handle

**Files:**
- Create: `scalpr/gateway/subscription.py`
- Test: `tests/unit/gateway/test_subscription.py`

**Interfaces:**
- Produces: `Subscription` class with `id`, `instruments`, `mode`, `is_active`

**Steps:**

- [ ] **Step 1: Write failing test**

```python
def test_subscription_creation():
    from scalpr.gateway.subscription import Subscription
    sub = Subscription(id="sub-1", instruments=["TCS:NSE"], mode=MarketFeed.QUOTE)
    assert sub.id == "sub-1"
    assert sub.mode == MarketFeed.QUOTE
    assert sub.is_active is True

def test_subscription_deactivate():
    sub = Subscription(id="sub-1", instruments=["TCS:NSE"], mode=MarketFeed.QUOTE)
    sub.deactivate()
    assert sub.is_active is False
```

- [ ] **Step 2: Run test to verify it fails**

- [ ] **Step 3: Implement Subscription**

```python
@dataclass
class Subscription:
    id: str
    instruments: list[str]
    mode: MarketFeed
    is_active: bool = True

    def deactivate(self) -> None:
        self.is_active = False
```

- [ ] **Step 4: Run tests to verify they pass**

- [ ] **Step 5: Commit**

```bash
git add scalpr/gateway/subscription.py tests/unit/gateway/test_subscription.py
git commit -m "feat(gateway): add Subscription handle"
```

---

## Task 5: Create Instrument Domain Object

**Files:**
- Create: `scalpr/gateway/instrument.py`
- Modify: `scalpr/domain/instrument.py` (add `wire_segment` to `ResolvedInstrument` if missing)
- Test: `tests/unit/gateway/test_instrument.py`

**Interfaces:**
- Consumes: `ResolvedInstrument`, `SimpleInstrumentId`, `DerivativeInstrumentId` from domain
- Produces: `Instrument` domain object with `historical()`, `quote()`, `ohlc()`, `depth()`, `subscribe()`, `option_chain()`, `expired_options()`

**Steps:**

- [ ] **Step 1: Write failing test**

```python
def test_instrument_historical():
    resolved = ResolvedInstrument(
        instrument_id=SimpleInstrumentId("TCS", Exchange.NSE),
        security_id="112833", exchange=Exchange.NSE, segment=Segment.EQUITY,
        trading_symbol="TCS", wire_segment="NSE_EQ",
        lot_size=1, tick_size=Decimal("0.05"), freeze_quantity=None,
        expiry=None, strike=None, option_type=None,
    )
    inst = Instrument(resolved=resolved, market_data=mock_market_data)
    candles = inst.historical(interval="1D", start=datetime(2024,1,1), end=datetime(2024,1,31))
    assert len(candles) > 0
    assert isinstance(candles[0], Candle)
```

- [ ] **Step 2: Run test to verify it fails**

- [ ] **Step 3: Implement Instrument**

```python
class Instrument:
    def __init__(self, resolved: ResolvedInstrument,
                 market_data: MarketDataService,
                 option_chain: OptionChainService | None = None) -> None:
        self.id = resolved.instrument_id
        self.resolved = resolved
        self._md = market_data
        self._oc = option_chain

    def historical(self, interval, start, end) -> list[Candle]:
        return self._md.historical(self, interval, start, end)

    def quote(self) -> Quote:
        return self._md.quote(self)

    def ohlc(self) -> OHLC:
        return self._md.ohlc(self)

    def depth(self, levels: int = 5) -> MarketDepth:
        return self._md.depth(self, levels)

    def subscribe(self, mode: MarketFeed, on_event) -> Subscription:
        return self._md.subscribe_feed(mode, [self], on_event)

    def option_chain(self, expiry: date | None = None) -> OptionChain:
        if self._oc is None:
            raise OptionChainNotSupported("Option chain service not available")
        return self._oc.chain(self, expiry)

    def expired_options(self, expiry: date, start: date, end: date) -> list[ExpiredOptionCandle]:
        if self._oc is None:
            raise OptionChainNotSupported("Option chain service not available")
        return self._oc.expired_options(self, expiry, start, end)
```

- [ ] **Step 4: Run tests to verify they pass**

- [ ] **Step 5: Commit**

```bash
git add scalpr/gateway/instrument.py tests/unit/gateway/test_instrument.py
git commit -m "feat(gateway): add Instrument domain object"
```

---

## Task 6: Create MarketDataService

**Files:**
- Create: `scalpr/gateway/market_data_service.py`
- Test: `tests/unit/gateway/test_market_data_service.py`

**Interfaces:**
- Consumes: `DhanClient` (adapter), `Instrument` (from gateway/instrument.py)
- Produces: `Quote`, `OHLC`, `MarketDepth`, `Candle`, `Subscription`, `TickerEvent`/`QuoteEvent`/`FullEvent`

**Steps:**

- [ ] **Step 1: Write failing tests**

```python
def test_quote_returns_domain_object():
    svc = MarketDataService(client=mock_client)
    resolved = create_resolved_instrument()
    inst = Instrument(resolved=resolved, market_data=svc)
    quote = svc.quote(inst)
    assert isinstance(quote, Quote)
    assert quote.ltp == Decimal("100.00")

def test_subscribe_feed_returns_subscription():
    svc = MarketDataService(client=mock_client)
    sub = svc.subscribe_feed(MarketFeed.FULL, ["TCS:NSE"], on_event=lambda e: None)
    assert isinstance(sub, Subscription)
    assert sub.mode == MarketFeed.FULL
```

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement MarketDataService**

Key implementation details:
- `quote()` calls `client.get_quote_raw(resolved)` and maps to `Quote` domain object
- `ohlc()` calls Dhan's OHLC endpoint and maps to `OHLC`
- `depth()` calls `client.get_market_depth(resolved)` and maps to `MarketDepth` with `DepthLevel`
- `historical()` calls `client.get_historical()` and maps to `list[Candle]` with `Decimal` prices
- `subscribe_feed()` resolves instruments, batches into groups of 100, delegates to `client.subscribe_quotes()` / `client.subscribe_market_depth()`, returns `Subscription`
- `unsubscribe()` takes `Subscription` handle

- [ ] **Step 4: Run tests to verify they pass**

- [ ] **Step 5: Commit**

```bash
git add scalpr/gateway/market_data_service.py tests/unit/gateway/test_market_data_service.py
git commit -m "feat(gateway): add MarketDataService with domain object returns"
```

---

## Task 7: Create OrderService

**Files:**
- Create: `scalpr/gateway/order_service.py`
- Test: `tests/unit/gateway/test_order_service.py`

**Interfaces:**
- Consumes: `DhanClient`, `RiskService`, `MessageBus`, `OrderRequest`, `ModifyOrderRequest`
- Produces: `Order`, `Trade`

**Steps:**

- [ ] **Step 1: Write failing tests**

```python
def test_place_order_validates_then_publishes():
    svc = OrderService(client=mock_client, bus=mock_bus, clock=mock_clock, risk=mock_risk)
    req = OrderRequest(instrument=inst, side=Side.BUY, quantity=10, price=Decimal("2500"))
    order = svc.place(req)
    assert isinstance(order, Order)
    assert order.state == OrderState.PENDING
    mock_bus.publish.assert_called_with("exec.command.submit", SubmitOrder(order=order, broker="dhan"))

def test_modify_order():
    svc = OrderService(client=mock_client, bus=mock_bus, clock=mock_clock, risk=mock_risk)
    mod = ModifyOrderRequest(price=Decimal("2510"), quantity=20)
    order = svc.modify("order-1", mod)
    assert isinstance(order, Order)

def test_cancel_order():
    svc = OrderService(client=mock_client, bus=mock_bus, clock=mock_clock, risk=mock_risk)
    order = svc.cancel("order-1")
    assert order.state == OrderState.CANCELLED
```

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement OrderService**

Key implementation details:
- `place()` validates via `RiskService`, constructs `Order` domain object, publishes `SubmitOrder` on bus
- `place_slice()` splits by freeze quantity, places each slice
- `modify()` validates, sends PUT to Dhan, returns updated `Order`
- `cancel()` sends DELETE to Dhan, returns `Order` with state=CANCELLED
- `get()` fetches order detail, maps to domain `Order`
- `list()` fetches order book, maps to `list[Order]`
- `trades()` fetches trade book, maps to `list[Trade]`
- `trades_for_order()` fetches trades for a specific order

- [ ] **Step 4: Run tests to verify they pass**

- [ ] **Step 5: Commit**

```bash
git add scalpr/gateway/order_service.py tests/unit/gateway/test_order_service.py
git commit -m "feat(gateway): add OrderService with validation, placement, modification, cancellation"
```

---

## Task 8: Create PortfolioService and AccountService

**Files:**
- Create: `scalpr/gateway/portfolio_service.py`
- Create: `scalpr/gateway/account_service.py`
- Test: `tests/unit/gateway/test_portfolio_service.py`, `tests/unit/gateway/test_account_service.py`

**Interfaces:**
- Consumes: `DhanClient`, `Position`, `Holding`, `Funds`
- Produces: `list[Position]`, `list[Holding]`, `Funds`, `AccountProfile`, `FundLimits`, `MarginResult`

**Steps:**

- [ ] **Step 1: Write failing tests**

```python
def test_positions_returns_domain_objects():
    svc = PortfolioService(client=mock_client)
    positions = svc.positions()
    assert all(isinstance(p, Position) for p in positions)

def test_holdings_returns_domain_objects():
    svc = PortfolioService(client=mock_client)
    holdings = svc.holdings()
    assert all(isinstance(h, Holding) for h in holdings)
```

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement services**

`PortfolioService`:
- `holdings()` — calls `client.get_holdings()`, maps raw dicts to `Holding` domain objects
- `positions()` — calls `client.get_positions()`, returns `list[Position]` (already domain objects)
- `ledger()` — fetches ledger entries
- `trade_history()` — fetches trade history

`AccountService`:
- `profile()` — calls `/profile`, maps to `AccountProfile`
- `fund_limits()` — calls `/fundlimit`, maps to `FundLimits`
- `margin()` — calls `/margincalculator`, maps to `MarginResult`
- `capabilities()` — checks token validity, exchange segments, data plan

- [ ] **Step 4: Run tests to verify they pass**

- [ ] **Step 5: Commit**

```bash
git add scalpr/gateway/portfolio_service.py scalpr/gateway/account_service.py tests/unit/gateway/test_portfolio_service.py tests/unit/gateway/test_account_service.py
git commit -m "feat(gateway): add PortfolioService and AccountService with domain object returns"
```

---

## Task 9: Create RiskService and TraderControlService

**Files:**
- Create: `scalpr/gateway/risk_service.py`
- Create: `scalpr/gateway/trader_control_service.py`
- Test: `tests/unit/gateway/test_risk_service.py`, `tests/unit/gateway/test_trader_control_service.py`

**Interfaces:**
- Consumes: `DhanClient`, `OrderRequest`, `ResolvedInstrument`
- Produces: Validation errors (`InvalidOrder`, `InsufficientMargin`), kill switch status

**Steps:**

- [ ] **Step 1: Write failing tests**

```python
def test_risk_rejects_non_lot_multiple():
    svc = RiskService(client=mock_client)
    req = OrderRequest(instrument=futures_inst, side=Side.BUY, quantity=7)  # lot_size=15
    with pytest.raises(InvalidOrder):
        svc.validate(req)

def test_kill_switch_activates():
    svc = TraderControlService(client=mock_client)
    status = svc.kill_switch(KillSwitchAction.ACTIVATE)
    assert status == KillSwitchStatus.ACTIVE
```

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement services**

`RiskService.validate()`:
- Check lot-size multiples for derivatives
- Check tick-size alignment for LIMIT orders
- Check freeze quantity limits
- Check margin (optional pre-check)
- Check static-IP requirement (if configured)

`TraderControlService`:
- `kill_switch(action)` — calls `client.kill_switch()`, returns `KillSwitchStatus`
- `kill_switch_status()` — returns current status
- `exit_all(scope)` — cancels all open orders and flattens positions

- [ ] **Step 4: Run tests to verify they pass**

- [ ] **Step 5: Commit**

```bash
git add scalpr/gateway/risk_service.py scalpr/gateway/trader_control_service.py tests/unit/gateway/test_risk_service.py tests/unit/gateway/test_trader_control_service.py
git commit -m "feat(gateway): add RiskService with order validation and TraderControlService"
```

---

## Task 10: Create OrderUpdateService

**Files:**
- Create: `scalpr/gateway/order_update_service.py`
- Modify: `scalpr/adapters/dhan/_ws.py` (add order update WebSocket)
- Test: `tests/unit/gateway/test_order_update_service.py`

**Interfaces:**
- Consumes: `DhanClient`, `MessageBus`
- Produces: `OrderUpdate` events, `Subscription`

**Steps:**

- [ ] **Step 1: Write failing test**

```python
def test_order_update_service_connects():
    svc = OrderUpdateService(client=mock_client, bus=mock_bus)
    svc.connect()
    mock_client.connect_order_updates.assert_called_once()

def test_order_update_service_subscribe():
    svc = OrderUpdateService(client=mock_client, bus=mock_bus)
    sub = svc.subscribe(on_update=lambda e: None)
    assert isinstance(sub, Subscription)
```

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Add order update WebSocket to DhanWebSocket**

Add `OrderUpdateWebSocket` class in `_ws.py` that:
- Connects to Dhan's order-update WebSocket
- Parses binary packets
- Normalizes to `OrderUpdate` domain events
- Publishes on `exec.event.filled.dhan` / `exec.event.rejected.dhan` / `exec.event.cancelled.dhan`

- [ ] **Step 4: Add `connect_order_updates()` / `disconnect_order_updates()` to DhanClient**

- [ ] **Step 5: Implement OrderUpdateService**

- [ ] **Step 6: Run tests to verify they pass**

- [ ] **Step 7: Commit**

```bash
git add scalpr/adapters/dhan/_ws.py scalpr/adapters/dhan/client.py scalpr/gateway/order_update_service.py tests/unit/gateway/test_order_update_service.py
git commit -m "feat: add OrderUpdateService with order-update WebSocket"
```

---

## Task 11: Create Gateway Facade

**Files:**
- Create: `scalpr/gateway/gateway.py`
- Create: `scalpr/gateway/__init__.py`
- Test: `tests/unit/gateway/test_gateway.py`

**Interfaces:**
- Consumes: `DhanClient`, all domain services
- Produces: `Gateway` with `.orders`, `.portfolio`, `.account`, `.market_data`, `.instrument()`, `.subscribe_feed()`, `.order_updates`, `.risk`, `.trader_control`, `.capabilities()`, `.close()`

**Steps:**

- [ ] **Step 1: Write failing test**

```python
def test_gateway_construction():
    gw = Gateway(config={"client_id": "test", "access_token": "test", "totp_secret": "test"})
    assert gw is not None
    assert gw.orders is not None
    assert gw.portfolio is not None
    assert gw.account is not None

def test_gateway_instrument():
    gw = Gateway(config=...)
    inst = gw.instrument("TCS:NSE")
    assert isinstance(inst, Instrument)
    assert inst.resolved.trading_symbol == "TCS"
```

- [ ] **Step 2: Run test to verify it fails**

- [ ] **Step 3: Implement Gateway**

```python
class Gateway:
    def __init__(self, config: dict[str, Any]) -> None:
        self._bus = MessageBus()
        self._clock = LiveClock()
        self._client = DhanClient(self._bus, self._clock, config)
        self._client.start()

        self._market_data = MarketDataService(self._client)
        self._order_chain = OptionChainService(self._client)
        self._orders = OrderService(self._client, self._bus, self._clock,
                                    RiskService(self._client))
        self._portfolio = PortfolioService(self._client)
        self._account = AccountService(self._client)
        self._risk = RiskService(self._client)
        self._trader_control = TraderControlService(self._client)
        self._order_updates = OrderUpdateService(self._client, self._bus)

    @property
    def orders(self) -> OrderService:
        return self._orders

    @property
    def portfolio(self) -> PortfolioService:
        return self._portfolio

    @property
    def account(self) -> AccountService:
        return self._account

    @property
    def market_data(self) -> MarketDataService:
        return self._market_data

    @property
    def order_updates(self) -> OrderUpdateService:
        return self._order_updates

    @property
    def risk(self) -> RiskService:
        return self._risk

    @property
    def trader_control(self) -> TraderControlService:
        return self._trader_control

    def instrument(self, identifier, exchange=None, segment=None) -> Instrument:
        resolved = self._client.resolve_instrument(identifier, exchange, segment)
        return Instrument(resolved, self._market_data, self._order_chain)

    def subscribe_feed(self, mode: MarketFeed, instruments, on_event) -> Subscription:
        return self._market_data.subscribe_feed(mode, instruments, on_event)

    def unsubscribe(self, subscription: Subscription) -> None:
        self._market_data.unsubscribe(subscription)

    def capabilities(self) -> Capabilities:
        return self._account.capabilities()

    def close(self) -> None:
        self._client.stop()
```

- [ ] **Step 4: Run tests to verify they pass**

- [ ] **Step 5: Commit**

```bash
git add scalpr/gateway/gateway.py scalpr/gateway/__init__.py tests/unit/gateway/test_gateway.py
git commit -m "feat(gateway): add Gateway facade with domain services"
```

---

## Task 12: Refactor DhanClient to Thin Adapter

**Files:**
- Modify: `scalpr/adapters/dhan/client.py` (remove facade methods, add adapter methods)
- Modify: `scalpr/adapters/dhan/_order_client.py` (remove kill_switch, super/forever/conditional methods)
- Modify: `scalpr/adapters/dhan/_market_data_client.py` (remove subscribe_batch, simplify)
- Test: `tests/unit/adapters/dhan/test_client.py`

**Interfaces:**
- Consumes: `DhanClient` internal sub-clients
- Produces: Domain objects (`Order`, `Position`, `Trade`, `Quote`, `MarketDepth`, `Candle`)

**Steps:**

- [ ] **Step 1: Write failing tests for thin adapter**

```python
def test_client_get_quote_returns_domain_quote():
    client = DhanClient(bus, clock, config)
    client.start()
    quote = client.get_quote(resolved_instrument)
    assert isinstance(quote, Quote)

def test_client_get_order_detail_returns_domain_order():
    client = DhanClient(bus, clock, config)
    client.start()
    order = client.get_order_detail("order-1")
    assert isinstance(order, Order)
```

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Refactor DhanClient**

Remove all facade methods (`place_order`, `get_quote`, `get_order_detail`, `get_trade_book`, `kill_switch`, `place_super_order`, `subscribe`, `subscribe_batch`, etc.). Add thin adapter methods:

- `resolve_instrument(identifier, exchange, segment) -> ResolvedInstrument`
- `get_quote(resolved: ResolvedInstrument) -> Quote`
- `get_order_detail(order_id: str) -> Order`
- `get_trade_book() -> list[Trade]`
- `get_holdings() -> list[Holding]`
- `get_funds() -> Funds`
- `get_positions() -> list[Position]`
- `place_order(order: Order) -> str` (returns order_id only)
- `connect_order_updates()` / `disconnect_order_updates()`
- `subscribe_quotes(resolved: ResolvedInstrument) -> None`
- `subscribe_market_depth(resolved: ResolvedInstrument, level: int) -> None`

Move advanced order methods to `TraderControlService` (which calls raw adapter methods).

- [ ] **Step 4: Run tests to verify they pass**

- [ ] **Step 5: Commit**

```bash
git add scalpr/adapters/dhan/client.py scalpr/adapters/dhan/_order_client.py scalpr/adapters/dhan/_market_data_client.py tests/unit/adapters/dhan/test_client.py
git commit -m "refactor(dhan): make DhanClient a thin adapter returning domain objects"
```

---

## Task 13: Update CLI and Fix Broken Scripts

**Files:**
- Modify: `scalpr/cli/commands/stream.py` (use Gateway)
- Modify: `scalpr/cli/commands/broker.py` (use Gateway)
- Modify: `scalpr/cli/utils.py` (use Gateway)
- Delete: `examples/gateway_api_examples.py` (already deprecated)
- Delete: `scripts/validate_gateway_live.py` (broken)
- Fix: `test.ipynb` (update to Gateway API)
- Test: Run CLI commands

**Steps:**

- [ ] **Step 1: Update `scalpr/cli/utils.py`**

Replace `_make_dhan_client()` with `_make_gateway()`:

```python
def _make_gateway() -> Gateway | None:
    client_id = os.environ.get("DHAN_CLIENT_ID", "")
    access_token = os.environ.get("DHAN_ACCESS_TOKEN", "")
    if not (client_id and access_token):
        return None
    config = {
        "client_id": client_id,
        "access_token": access_token,
        "totp_secret": os.environ.get("DHAN_TOTP_SECRET", ""),
        "pin": os.environ.get("DHAN_PIN", "1111"),
        "csv_path": os.environ.get("DHAN_INSTRUMENT_CSV", "instrument.csv"),
    }
    return Gateway(config)
```

- [ ] **Step 2: Update CLI commands to use Gateway**

- [ ] **Step 3: Delete broken scripts**

```bash
git rm examples/gateway_api_examples.py scripts/validate_gateway_live.py
```

- [ ] **Step 4: Update `test.ipynb`**

Replace `from scalpr.brokers.gateway import Gateway` with `from scalpr.gateway.gateway import Gateway`

- [ ] **Step 5: Run tests**

`.venv/bin/python -m pytest tests/unit/ tests/contract/ -x -q`

- [ ] **Step 6: Commit**

```bash
git add scalpr/cli/ examples/ test.ipynb
git commit -m "refactor(cli): use Gateway facade, remove broken scripts"
```

---

## Task 14: Update Runbook and Verify Full Test Suite

**Files:**
- Modify: Add runbook entry for new Gateway API
- Test: Full test suite

**Steps:**

- [ ] **Step 1: Add runbook entry**

```bash
python3 .qoder/skills/kanban.cli/scripts/kanban.py runbook add "Gateway facade and domain services API" \
 --api "Gateway(config) -> .instrument(), .orders, .portfolio, .account, .subscribe_feed(), .order_updates, .close()" \
 --steps "1. Construct Gateway with config dict; 2. Call gw.instrument('TCS:NSE') for Instrument; 3. Use gw.orders.place(OrderRequest) for orders; 4. Use gw.subscribe_feed(MarketFeed.FULL, [...], on_event) for market data; 5. Call gw.close() on shutdown" \
 --example "gw = Gateway(config); inst = gw.instrument('TCS:NSE'); inst.quote(); gw.close()" \
 --files "scalpr/gateway/gateway.py,scalpr/gateway/order_service.py,scalpr/gateway/market_data_service.py,scalpr/adapters/dhan/client.py" \
 --tags "gateway,architecture,api"
```

- [ ] **Step 2: Run full test suite**

`.venv/bin/python -m pytest tests/unit/ tests/contract/ -v`

- [ ] **Step 3: Update stale annotations**

`.venv/bin/python -m pytest tests/unit/ tests/contract/ -q` must show 0 failures.

- [ ] **Step 4: Commit**

```bash
git add .
git commit -m "docs: update runbook for Gateway facade API"
```

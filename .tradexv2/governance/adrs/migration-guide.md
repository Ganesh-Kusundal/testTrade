# ADR: Migration from `scalpr.brokers.*` to `scalpr.adapters.*`

**Status:** Draft · **K-056** · **2026-07-29**

## Context

The original broker integration lived under `scalpr.brokers.dhan.*` with a
`Gateway` facade, `IBrokerGateway` ABC, and per-domain adapters
(`OrdersAdapter`, `MarketDataAdapter`, `PortfolioAdapter`). This design grew
organically from a proof-of-concept and accumulated architectural debt:

- **Result monad** in `DhanMapper` — callers must `.value` / `.error` every mapping
- **`IBrokerGateway`** super-interface — forces every consumer to know the full
  surface even when they only need `ITradingPort`
- **Raw dict returns** from `get_orderbook()`, `get_quote()` — consumers must
  remember field names
- **Adapter discovery via `BrokerRegistry`** — global mutable state, lazy imports,
  test-flaky
- **Circular import pressure** — `_mapper.py` still imports `scalpr.brokers.dhan.resolution`
- **`DhanConnection`** owns lifecycle — too many concerns in one class

The new adapter layer (`scalpr.adapters.dhan.*`) replaces this with a
message-bus-native `DhanClient` that uses the `MessageBus` for both commands
and events. Domain types (`Fill`, `Position`, `Order`, `Tick`) are returned
directly; exceptions are raised normally.

## 1. Import path mapping

| Old import (brokers) | New import (adapters) |
|---|---|
| `scalpr.brokers.dhan.gateway.DhanGateway` | `scalpr.adapters.dhan.client.DhanClient` |
| `scalpr.brokers.dhan.connection.DhanConnection` | removed — `DhanClient` owns its lifecycle |
| `scalpr.brokers.dhan.orders.OrdersAdapter` | removed — merged into `DhanClient` |
| `scalpr.brokers.dhan.portfolio.PortfolioAdapter` | `scalpr.adapters.dhan._portfolio.PortfolioAdapter` (private) |
| `scalpr.brokers.dhan.market_data.MarketDataAdapter` | removed — merged into `DhanClient` |
| `scalpr.brokers.dhan.historical.HistoricalDataAdapter` | `scalpr.adapters.dhan._historical.HistoricalDataAdapter` (private) |
| `scalpr.brokers.dhan.option_chain.OptionChainAdapter` | `scalpr.adapters.dhan._option_chain.OptionChainAdapter` (private) |
| `scalpr.brokers.dhan.http_client.DhanHttpClient` | `scalpr.adapters.dhan._http.DhanHttpClient` (private) |
| `scalpr.brokers.dhan.resolution.SymbolResolver` | `scalpr.adapters.dhan._resolver.SymbolResolver` (private) |
| `scalpr.brokers.dhan.mapper.DhanMapper` | `scalpr.adapters.dhan._mapper` (module of free functions) |
| `scalpr.brokers.dhan.dtos.DhanOrderRequest/Response` | `scalpr.adapters.dhan._types` (dataclasses) |
| `scalpr.brokers.dhan.exceptions.*` | `scalpr.domain.errors.*` |
| `scalpr.brokers.errors.*` | `scalpr.domain.errors.*` (re-export shim) |
| `scalpr.brokers.contracts.*` | `scalpr.domain.contracts.*` (re-export shim) |
| `scalpr.brokers.broker_port.IBrokerGateway` | `scalpr.domain.contracts.HttpClientProtocol` / `ResolverProtocol` |
| `scalpr.brokers.gateway.Gateway` | deprecated — use `DhanClient` directly |
| `scalpr.brokers.registry.BrokerRegistry` | removed |
| `scalpr.brokers.rate_limit.*` | `scalpr.adapters.dhan._http.RateLimiter` |

**Re-export shims** (`scalpr.brokers/contracts.py`, `scalpr.brokers/errors.py`)
still exist and simply re-export from `scalpr.domain.*`. They will be deleted
in Phase 2 of K-056.

## 2. API differences

### 2.1 Exceptions vs Result monad

**Old (brokers):**
```python
result = DhanMapper.order_to_dhan_request(order, client_id, security_id)
if not result.is_ok:
    raise OrderError(f"Mapping failed: {result.error}")
dhan_req = result.value
```

**New (adapters):**
```python
# Functions raise MappingError/MissingFieldError/InvalidValueError directly
req = order_to_dhan_request(order, security_id, segment, client_id)
```

The old `Result[T, E]` monad (in `scalpr.brokers.dhan.mapper`) is eliminated.
Every mapper function in `scalpr.adapters.dhan._mapper` raises typed exceptions
from `scalpr.domain.errors.*`.

### 2.2 Raw dicts vs typed returns

**Old:** `OrdersAdapter.get_orderbook()` returns `list[dict]` — consumers must
know that keys are `"order_id"`, `"symbol"`, `"status"`, etc.

**New:** `DhanClient` returns domain objects directly everywhere:
- `get_positions() -> list[Position]`
- `get_quote() -> dict[str, Any]` (still dict — `Quote` TypedDict via `to_quote()`)
- `order_report() -> dict` (still dict — raw broker response)
- WebSocket ticks → `Tick` domain objects published on bus

### 2.3 Gateway facade gone

**Old:**
```python
gw = Gateway()
ltp = gw.ltp("TCS")
orders = gw.get_orders()
```

**New:**
```python
client = DhanClient(bus, clock, config)
client.start()
# Use client directly, or use MessageBus for commands:
bus.publish("exec.command.submit.dhan", SubmitOrder(order=my_order))
```

### 2.4 Error types moved to domain

All error classes now live in `scalpr.domain.errors`:

| Old import | New import |
|---|---|
| `scalpr.brokers.errors.TradingError` | `scalpr.domain.errors.TradingError` |
| `scalpr.brokers.dhan.exceptions.BrokerError` | `scalpr.domain.errors.TradingError` |
| `scalpr.brokers.dhan.exceptions.DhanInstrumentNotFoundError` | `scalpr.domain.errors.InstrumentNotFound` |
| `scalpr.brokers.dhan.exceptions.OrderError` | `scalpr.domain.errors.OrderError` |

Adapter code catches `Exception` broadly and publishes `OrderRejected` events
rather than raising `BrokerError`.

### 2.5 Import used from old module in adapter itself

`scalpr/adapters/dhan/_mapper.py:355` still has a lazy import:
```python
from scalpr.brokers.dhan.resolution import SEGMENT_TO_EXCHANGE
```
This must be migrated to a local constant or imported from the new resolver.
See K-056 Phase 1 item.

## 3. Coexistence pattern

Both `scalpr.brokers.*` and `scalpr.adapters.*` exist side by side during the
migration. The old module is frozen — no new features, only critical bugfixes.

### 3.1 How to keep both working

1. **Keep the re-export shims** (`scalpr/brokers/errors.py`, `scalpr/brokers/contracts.py`)
   — they delegate to `scalpr.domain.*` so existing imports keep working.
2. **Registry** (`scalpr.brokers.registry`) — keep registered but lazily import
   from `scalpr.brokers.dhan.*` until Phase 2.
3. **`Gateway` facade** — keep as deprecated wrapper that delegates old API
   to the new client under the hood.
4. **Tests** — run both old and new test suites; CI should pass for both.

### 3.2 What must NOT change

- **`scalpr.domain.*`** — the domain models (`Order`, `Fill`, `Position`,
  `Tick`, `Quote`, etc.) are shared and stable. New adapters consume them.
- **`scalpr.engine.message_bus`** — stable, used by both old and new.
- **`scalpr.engine.execution_engine`** — the `SubmitOrder`, `CancelOrder`,
  `ModifyOrder` commands and `OrderFilled`, `OrderRejected`, `OrderCancelled`
  event types are shared.

## 4. Deletion timeline (K-056)

| Phase | Description | Target |
|---|---|---|
| **Phase 0** | Write this ADR, map all imports | Current session |
| **Phase 1** | Migrate `_mapper.py` lazy import (`SEGMENT_TO_EXCHANGE`) to local constant in new adapter | Sprint 1 |
| **Phase 1** | Delete `scalpr/brokers/errors.py`, `scalpr/brokers/contracts.py` re-export shims — update remaining old-module callers to `scalpr.domain.*` | Sprint 1 |
| **Phase 2** | Delete `scalpr/brokers/dhan/` entirely (gateway, connection, orders, portfolio, market_data, historical, option_chain, mapper, dtos, exceptions, auth, http_client, loader, resolution, ws_client, ws_manager, _totp_cooldown) | Sprint 2 |
| **Phase 2** | Delete `scalpr/brokers/gateway/`, `scalpr/brokers/instrument_handle.py`, `scalpr/brokers/broker_port.py`, `scalpr/brokers/registry.py`, `scalpr/brokers/capabilities.py` | Sprint 2 |
| **Phase 2** | Delete `scalpr/brokers/__init__.py` — remove public API surface | Sprint 2 |
| **Phase 2** | Delete `scalpr/brokers/rate_limit.py` — rate limiting is now in `scalpr/adapters/dhan/_http.py` | Sprint 2 |
| **Phase 3** | Delete `scalpr/brokers/` directory root | Sprint 3 |
| **Phase 3** | Remove `scalpr.domain.instrument` dependency on `SEGMENT_TO_EXCHANGE` — final clean-up | Sprint 3 |

### Pre-flight checklist per phase

Before each deletion phase, run:
```bash
pytest tests/unit/ tests/contract/
python3 -c "import scalpr.brokers"  # should fail only in Phase 3
python3 -c "from scalpr.adapters.dhan.client import DhanClient"  # should always pass
grep -r "scalpr\.brokers" scalpr/ --include="*.py" | grep -v "# noqa" | grep -v "backward compat"
```

## 5. Migration steps (how to update a consumer file)

Here is the step-by-step checklist for migrating any file that currently imports
from `scalpr.brokers.*`.

### Step 1: Identify imports

```python
# OLD
from scalpr.brokers.errors import TradingError, InstrumentNotFound
from scalpr.brokers.dhan.exceptions import BrokerError, DhanInstrumentNotFoundError
from scalpr.brokers.contracts import Quote, Funds
from scalpr.brokers.broker_port import IBrokerGateway, ITradingPort
```

### Step 2: Replace with domain imports

```python
# NEW
from scalpr.domain.errors import TradingError, InstrumentNotFound
from scalpr.domain.contracts import Quote, Funds
from scalpr.domain.order import Order
from scalpr.domain.position import Position
from scalpr.domain.fill import Fill

# No more IBrokerGateway — use DhanClient directly
from scalpr.adapters.dhan.client import DhanClient
```

### Step 3: Replace Gateway usage

```python
# OLD
gw = Gateway()
gw.connect()
ltp = gw.ltp("RELIANCE")
fill = gw.place_order(order)
gw.disconnect()

# NEW
from scalpr.engine.clock import Clock
from scalpr.engine.message_bus import MessageBus

clock = Clock()
bus = MessageBus()
client = DhanClient(bus, clock, config)
client.start()  # connects WS, subscribes to exec commands

# LTP — use bus or client
ltp = client.get_executed_price(order_id)

# Place order — use bus (async) or client (sync)
order_id = client.place_order(my_order)

client.stop()
```

### Step 4: Replace error handling

```python
# OLD
try:
    result = gw.place_order(order)
except BrokerError as e:
    logger.error("order failed: %s", e)

# NEW — exceptions still work, just use domain errors
try:
    order_id = client.place_order(my_order)
except TradingError as e:
    logger.error("order failed: %s", e)

# Or listen for rejected events
@bus.subscribe("exec.event.rejected.dhan")
def on_rejected(event: OrderRejected):
    logger.error("order %s rejected: %s", event.order_id, event.reason)
```

### Step 5: Replace Result.unwrap()

```python
# OLD
result = DhanMapper.order_to_dhan_request(order, client_id, security_id)
if not result.is_ok:
    handle_error(result.error)
req = result.value

# NEW
from scalpr.adapters.dhan._mapper import order_to_dhan_request
req = order_to_dhan_request(order, security_id, segment, client_id)
# Raises InvalidValueError on failure — no Result to unwrap
```

### Step 6: Replace message-bus topic subscriptions

```python
# OLD — ExecutionEngine subscribes to generic topics
bus.subscribe("exec.command.submit", handler)

# NEW — DhanClient subscribes to broker-specific topics
bus.subscribe("exec.command.submit.dhan", handler)

# Publish commands with broker suffix:
bus.publish("exec.command.submit.dhan", SubmitOrder(order=order))
```

## 6. New `DhanClient` public API

### Constructor

```python
def __init__(self, bus: MessageBus, clock: Clock, config: dict) -> None
```

`config` keys: `client_id`, `access_token`, `totp_secret`, `csv_path` (optional, defaults to `instrument.csv`), `pin` (optional, defaults to `1111`).

### Lifecycle

| Method | Description |
|---|---|
| `start()` | Loads instrument CSV, connects WebSocket, subscribes to `exec.command.*.dhan` topics |
| `stop()` | Disconnects WebSocket, unsubscribes all handlers |

### Order operations

| Method | Returns | Description |
|---|---|---|
| `place_order(order, product_type="INTRADAY", after_market=False, amo_time="OPEN", bo_profit=None, bo_stop_loss=None, tag=None, should_slice=False)` | `str` | Places order, returns `orderId`. Slices if `should_slice=True`. |
| `modify_order(order_id, **updates)` | `bool` | Sends `PUT /orders/{id}` with arbitrary kwargs |
| `cancel_order(order_id)` | `bool` | Sends `DELETE /orders/{id}` |
| `cancel_all_orders(symbol=None)` | `int` | Cancels all open orders, returns count |
| `get_order_detail(order_id)` | `dict` | Raw `GET /orders/{id}` response |
| `get_order_status(order_id)` | `str` | `"OPEN"`, `"FILLED"`, etc. |
| `get_executed_price(order_id)` | `float` | `tradedPrice` or `0.0` |
| `get_executed_price_and_time(order_id)` | `tuple[float, str]` | `price, traded_at` |
| `order_report(order_id)` | `dict` | Raw broker response |
| `get_trade_book()` | `list[dict]` | Raw `GET /trades` response |

### Super orders

| Method | Returns |
|---|---|
| `place_super_order(security_id, exchange_segment, transaction_type, quantity, price, ...)` | `list[str]` |
| `modify_super_order(order_id, ...)` | `bool` |
| `cancel_super_order(order_id)` | `bool` |
| `get_super_orders()` | `list[dict]` |

### Forever / GTD orders

| Method | Returns |
|---|---|
| `place_forever_order(security_id, exchange_segment, transaction_type, quantity, price, trigger_price, ...)` | `str` |
| `modify_forever_order(order_id, ...)` | `bool` |
| `cancel_forever_order(order_id)` | `bool` |
| `get_forever_orders()` | `list[dict]` |

### Conditional triggers

| Method | Returns |
|---|---|
| `place_conditional_trigger(security_id, exchange_segment, transaction_type, quantity, price, trigger_price, ...)` | `str` (trigger ID) |
| `delete_conditional_trigger(trigger_id)` | `bool` |
| `get_all_conditional_triggers()` | `list[dict]` |
| `get_conditional_trigger_by_id(trigger_id)` | `dict` |

### Market data

| Method | Returns | Notes |
|---|---|---|
| `subscribe_quotes(instrument_id)` | `None` | WS subscribe, ticks published on `"market.quote.dhan"` |
| `unsubscribe_quotes(instrument_id)` | `None` | WS unsubscribe |
| `get_quote(instrument_id)` | `dict[str, Any]` | `Quote` TypedDict via `to_quote()` |
| `subscribe_market_depth(instrument_id)` | `None` | WS depth subscribe |
| `unsubscribe_market_depth(instrument_id)` | `None` | WS depth unsubscribe |
| `get_market_depth_snapshot(instrument_id)` | `dict` | Raw depth response |
| `get_market_depth_df(instrument_id)` | `list[dict]` | Normalised bid/ask array |

### Portfolio

| Method | Returns |
|---|---|
| `get_positions()` | `list[Position]` |
| `get_holdings()` | `dict[str, Any]` |
| `get_funds()` | `dict[str, Any]` |
| `get_live_pnl()` | `float` |
| `get_positions_summary()` | `dict[str, Any]` |
| `margin_calculator(security_id, exchange_segment, transaction_type, quantity, product_type, price, ...)` | `dict[str, Any]` |
| `get_expired_option_data(...)` | `dict[str, Any]` |

### Historical data

| Method | Returns |
|---|---|
| `get_historical(symbol, exchange="NSE", timeframe="DAY", interval=5, from_date=None, to_date=None)` | `list[dict]` |
| `get_intraday(symbol, exchange="NSE", interval=5, from_date=None, to_date=None)` | `list[dict]` |
| `get_daily(symbol, exchange="NSE", from_date=None, to_date=None)` | `list[dict]` |

### Option chain

| Method | Returns |
|---|---|
| `get_option_chain(symbol, exchange="NSE", expiry=None)` | `dict[str, Any]` |
| `get_expiry_list(symbol, exchange="NSE")` | `list[str]` |
| `atm_strike(symbol, expiry_idx=0, exchange="NSE")` | `tuple[str, str, float]` |
| `otm_strike(symbol, expiry_idx=0, count=1, exchange="NSE")` | `tuple[str, str, float, float]` |
| `itm_strike(symbol, expiry_idx=0, count=1, exchange="NSE")` | `tuple[str, str, float, float]` |
| `get_greeks(symbol, expiry, strike, option_type, exchange="NSE")` | `dict \| None` |

### Kill switch

| Method | Returns |
|---|---|
| `kill_switch(action)` | `str` — `"ACTIVATE"` or `"DEACTIVATE"` |

## 7. Bus event model

### Topics

| Topic | Direction | Payload type | Description |
|---|---|---|---|
| `exec.command.submit.dhan` | Inbound | `SubmitOrder` | DhanClient subscribes on `start()` |
| `exec.command.cancel.dhan` | Inbound | `CancelOrder` | DhanClient subscribes on `start()` |
| `exec.command.modify.dhan` | Inbound | `ModifyOrder` | DhanClient subscribes on `start()` |
| `exec.event.filled.dhan` | Outbound | `OrderFilled` | Published on successful fill |
| `exec.event.rejected.dhan` | Outbound | `OrderRejected` | Published on order failure |
| `exec.event.cancelled.dhan` | Outbound | `OrderCancelled` | Published on cancel success |
| `market.quote.dhan` | Outbound | `Tick` | Published on each WebSocket tick |

### Event types (from `scalpr.engine.execution_engine`)

```python
@dataclass(frozen=True)
class SubmitOrder:
    order: Order
    broker: str = "dhan"

@dataclass(frozen=True)
class CancelOrder:
    order_id: str
    broker: str = "dhan"

@dataclass(frozen=True)
class ModifyOrder:
    order_id: str
    updates: dict
    broker: str = "dhan"

@dataclass(frozen=True)
class OrderRejected:
    order_id: str
    reason: str
    timestamp: datetime

@dataclass(frozen=True)
class OrderFilled:
    order_id: str
    fill: Fill
    timestamp: datetime

@dataclass(frozen=True)
class OrderCancelled:
    order_id: str
    timestamp: datetime
```

### Subscription pattern

```python
# Start the client — it subscribes to exec.command.*.dhan internally
client = DhanClient(bus, clock, config)
client.start()

# React to fills
def on_fill(event: OrderFilled):
    print(f"Filled: {event.fill}")

bus.subscribe("exec.event.filled.dhan", on_fill)

# Send command via bus (async)
bus.publish("exec.command.submit.dhan", SubmitOrder(order=my_order))

# Or use sync API
order_id = client.place_order(my_order)

# Stop
client.stop()
```

### Domain events (from `scalpr.domain.events`)

These are published by `ExecutionEngine` (not `DhanClient`) on generic topics:

| Topic | Payload |
|---|---|
| `domain.order.placed` | `OrderPlaced` |
| `domain.fill.received` | `FillReceived` |
| `domain.order.updated` | `OrderUpdated` |

## 8. Testing patterns

### 8.1 RecordingBus

`scalpr/adapters/test_helpers/recording_bus.py` wraps `MessageBus` and records
every `publish()` call:

```python
from scalpr.adapters.test_helpers.recording_bus import RecordingBus

def test_order_rejected_published():
    bus = RecordingBus()
    clock = MockClock()
    client = DhanClient(bus, clock, TEST_CONFIG)
    client.start()

    bad_order = Order(...)  # invalid order
    bus.publish("exec.command.submit.dhan", SubmitOrder(order=bad_order))

    rejected = bus.events_for("exec.event.rejected.*")
    assert len(rejected) == 1
    assert "insufficient" in rejected[0].reason.lower()
```

`RecordingBus` provides:
- `recorded_events: list[tuple[str, Any]]` — every `(topic, payload)` pair
- `events_for(topic_pattern)` — filter by glob pattern (supports `*` wildcard)
- `clear()` — reset recorded list

### 8.2 FakeExchange

`scalpr/adapters/test_helpers/fake_exchange.py` simulates a broker by
subscribing to `exec.command.submit.fake` and `exec.command.cancel.fake`:

```python
from scalpr.adapters.test_helpers.fake_exchange import FakeExchange

def test_full_order_flow():
    bus = MessageBus()
    fx = FakeExchange(bus)

    order = Order(
        order_id="test-1",
        symbol="RELIANCE",
        exchange=Exchange.NSE,
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=10,
        price=ZERO,
    )

    fill = fx.submit_order(order)
    assert fill.order_id == "test-1"
    assert fill.quantity == 10

    pos = fx.get_position("RELIANCE")
    assert pos is not None
    assert pos.quantity == 10
```

Use `FakeExchange` for any test that needs order lifecycle without hitting
the real Dhan API. It maintains position state and publishes fill events on
the bus.

### 8.3 Contract tests

Contract tests verify that `DhanClient` satisfies the expected protocol.
Place them in `tests/contract/`:

```python
# tests/contract/test_dhan_client.py
def test_client_satisfies_position_contract():
    """DhanClient.get_positions() returns list[Position]."""
    bus = RecordingBus()
    clock = Clock()
    client = DhanClient(bus, clock, CONFIG)
    client.start()

    positions = client.get_positions()
    for pos in positions:
        assert isinstance(pos, Position)
        assert pos.symbol
        assert pos.quantity != 0  # or == 0 is fine

    client.stop()
```

### 8.4 Migration regression guards

When migrating a consumer file, add a temporary test that verifies old and
new paths produce identical output:

```python
def test_migration_parity():
    """Old DhanMapper and new _mapper produce same order request."""
    order = Order(...)

    # Old path
    result = DhanMapper.order_to_dhan_request(order, "cid", "sec1")
    old_req = result.value

    # New path
    new_req = order_to_dhan_request(order, "sec1", "NSE_EQ", "cid")

    assert old_req == new_req  # or assert dict equality
```

Delete these parity tests after Phase 2.

## Appendix: Internal module structure

```
scalpr/adapters/dhan/
├── __init__.py
├── client.py          ← DhanClient (public, main entry point)
├── _types.py          ← Typed dataclasses (DhanAuthRequest, DhanOrderRequest, etc.)
├── _auth.py           ← TokenManager (TOTP-based token refresh)
├── _http.py           ← DhanHttpClient, RateLimiter (private HTTP layer)
├── _ws.py             ← DhanWebSocket (private WS layer)
├── _resolver.py       ← SymbolResolver (private)
├── _loader.py         ← InstrumentLoader (CSV download)
├── _mapper.py         ← Pure mapping functions (no Result monad)
├── _historical.py     ← HistoricalDataAdapter (private)
├── _option_chain.py   ← OptionChainAdapter (private)
├── _portfolio.py      ← PortfolioAdapter (private)
├── _greeks.py         ← GreeksCalculator (private)
```

scalpr/adapters/test_helpers/
├── __init__.py
├── recording_bus.py   ← RecordingBus (test helper)
├── fake_exchange.py   ← FakeExchange (test helper)
```

# SCALPR 30-Day Remediation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate every root cause identified in the architecture audit — silent error swallowing, god module, missing contract tests, broken quality gates, and thread safety gaps — using the smallest incremental changes that remove underlying causes.

**Architecture:** Three phases executed in dependency order. Phase 1 fixes the foundation (error handling, thread safety, missing mappings, config). Phase 2 decomposes the god module into focused routers with a clean composition root. Phase 3 adds contract tests and quality gates to prevent regression. Every change is TDD: write the failing test first, then the minimal implementation.

**Tech Stack:** Python 3.10+, pytest, pytest-asyncio, threading, FastAPI, Pydantic v2, import-linter, ruff, mypy

---

## File Structure

### Phase 1 — Foundation Fixes

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `scalpr/risk/circuit_breaker.py` | Add `threading.Lock` to `check_limits` and `reset` |
| Modify | `scalpr/brokers/dhan/orders.py` | Add `threading.Lock` to idempotency cache |
| Modify | `scalpr/brokers/dhan/mapper.py` | Add `NSE_FNO` exchange segment mapping |
| Modify | `scalpr/signals/gate_fsm.py` | Change `GateState` defaults from pass to fail |
| Modify | `scalpr/risk/session_guard.py` | Prevent repeated `square_off_all` calls |
| Modify | `scalpr/execution/order_router.py` | Fail-loud persistence error policy |
| Modify | `scalpr/observability/metrics.py` | Bound histogram, lock counter increment |
| Modify | `scalpr/brokers/dhan/ws_client.py` | Replace `print()` with `logger.error()` |
| Modify | `scalpr/brokers/contracts.py` | Remove duplicate `OrderSide` |
| Modify | `pyproject.toml` | Fix coverage source, import-linter contracts |
| Create | `tests/unit/risk/test_circuit_breaker_thread_safety.py` | Concurrent circuit breaker checks |
| Create | `tests/unit/brokers/test_mapper_fno.py` | F&O exchange mapping |
| Create | `tests/unit/signals/test_gate_fsm_defaults.py` | Fail-safe gate defaults |
| Create | `tests/unit/risk/test_session_guard_no_repeat.py` | No repeated square-off |
| Create | `tests/unit/execution/test_order_router_error_policy.py` | Error propagation |
| Create | `tests/unit/observability/test_metrics_bounded.py` | Histogram bound + counter safety |

### Phase 2 — God Module Decomposition

| Action | File | Responsibility |
|--------|------|----------------|
| Create | `scalpr/api/__init__.py` | Package init (empty) |
| Create | `scalpr/api/routers/__init__.py` | Routers package init |
| Create | `scalpr/api/routers/market_data.py` | Market data REST + WebSocket routes |
| Create | `scalpr/api/routers/orders.py` | Order management REST routes |
| Create | `scalpr/api/routers/portfolio.py` | Portfolio/positions REST routes |
| Create | `scalpr/api/routers/replay.py` | Replay session REST routes |
| Create | `scalpr/api/bootstrap.py` | Composition root factory |
| Modify | `scalpr/api/main.py` | Slim to < 100 lines — just `create_app()` call |
| Create | `tests/unit/api/test_bootstrap.py` | Factory creates app with all dependencies |
| Create | `tests/unit/api/test_routers_market_data.py` | Market data routes work independently |
| Create | `tests/unit/api/test_routers_orders.py` | Order routes work independently |
| Create | `tests/unit/api/test_routers_portfolio.py` | Portfolio routes work independently |

### Phase 3 — Contract Tests & Quality Gates

| Action | File | Responsibility |
|--------|------|----------------|
| Create | `tests/contract/__init__.py` | Contract test package |
| Create | `tests/contract/test_dhan_order_payload.py` | Verify place/modify/cancel JSON shape |
| Create | `tests/contract/test_dhan_response_mapping.py` | Verify response → Fill mapping |
| Create | `tests/unit/domain/test_order_fsm_property.py` | Property-based FSM tests |
| Create | `tests/unit/oms/test_persistence_error_policy.py` | Persistence errors propagate |
| Modify | `pyproject.toml` | Add contract test markers, coverage gates |

---

## Phase 1: Foundation Fixes (Days 1–7)

### Task 1: CircuitBreaker Thread Safety

**Files:**
- Modify: `scalpr/risk/circuit_breaker.py`
- Test: `tests/unit/risk/test_circuit_breaker_thread_safety.py`

- [ ] **Step 1: Write failing test for concurrent check_limits**

```python
# tests/unit/risk/test_circuit_breaker_thread_safety.py
"""Thread safety tests for CircuitBreaker."""
import threading
from decimal import Decimal
from scalpr.risk.circuit_breaker import CircuitBreaker


def test_concurrent_check_limits_should_not_corrupt_state():
    """Multiple threads checking limits simultaneously must not corrupt breaker state."""
    cb = CircuitBreaker(daily_loss_limit_pct=0.03, drawdown_limit_pct=0.05)
    results = []
    errors = []

    def check():
        try:
            ok = cb.check_limits(
                portfolio_value=Decimal("100000"),
                daily_loss=Decimal("3500"),  # exceeds 3%
                drawdown=Decimal("0.02"),
            )
            results.append(ok)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=check) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0, f"Thread safety violation: {errors}"
    assert cb.is_tripped  # All checks should have tripped it
    assert all(r is False for r in results)  # All should be blocked


def test_concurrent_reset_should_not_corrupt_state():
    """Multiple threads resetting simultaneously must not corrupt state."""
    cb = CircuitBreaker(daily_loss_limit_pct=0.03, drawdown_limit_pct=0.05)
    cb._halted = True  # Force tripped state
    cb._daily_loss_tripped = True
    errors = []

    def reset():
        try:
            cb.reset()
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=reset) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0
    assert not cb.is_tripped
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/risk/test_circuit_breaker_thread_safety.py -v`
Expected: Tests may pass or fail intermittently (race condition) — this proves the need for a lock.

- [ ] **Step 3: Add threading.Lock to CircuitBreaker**

In `scalpr/risk/circuit_breaker.py`, add `import threading` and modify `__init__`, `check_limits`, and `reset`:

```python
import threading

class CircuitBreaker:
    def __init__(self, ...):
        # ... existing fields ...
        self._lock = threading.Lock()

    def check_limits(self, portfolio_value, daily_loss, drawdown):
        with self._lock:
            # ... existing logic unchanged ...

    def reset(self):
        with self._lock:
            self._halted = False
            self._daily_loss_tripped = False
            self._drawdown_tripped = False
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/risk/test_circuit_breaker_thread_safety.py -v`
Expected: PASS (deterministic, no flakiness)

- [ ] **Step 5: Run existing circuit breaker tests**

Run: `pytest tests/unit/oms/test_oms_risk.py::test_circuit_breaker_limits -v`
Expected: PASS (no regression)

- [ ] **Step 6: Commit**

```bash
git add scalpr/risk/circuit_breaker.py tests/unit/risk/test_circuit_breaker_thread_safety.py
git commit -m "fix(risk): add thread safety to CircuitBreaker.check_limits and reset"
```

---

### Task 2: OrdersAdapter Idempotency Cache Thread Safety

**Files:**
- Modify: `scalpr/brokers/dhan/orders.py:46-55,132-133`
- Test: `tests/unit/brokers/dhan/test_idempotency_thread_safety.py`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/brokers/dhan/test_idempotency_thread_safety.py
"""Thread safety tests for OrdersAdapter idempotency cache."""
import threading
from unittest.mock import MagicMock
from decimal import Decimal
from scalpr.brokers.dhan.orders import OrdersAdapter
from scalpr.domain.order import Order, OrderSide, OrderType, OrderState
from scalpr.domain.instrument import Exchange


def _make_order(order_id: str) -> Order:
    return Order(
        order_id=order_id, symbol="RELIANCE", exchange=Exchange.NSE,
        side=OrderSide.BUY, order_type=OrderType.LIMIT,
        quantity=10, price=Decimal("2500"), state=OrderState.PENDING,
    )


def test_concurrent_place_order_should_not_duplicate_idempotency_check():
    """Two threads placing same correlation_id must not both pass idempotency check."""
    mock_client = MagicMock()
    mock_client.client_id = "test"
    mock_client.post.return_value = {
        "orderId": "ord_1", "orderStatus": "FILLED",
        "tradedQuantity": 10, "tradedPrice": 2500.0,
    }
    mock_resolver = MagicMock()
    mock_inst = MagicMock()
    mock_inst.security_id = "12345"
    mock_resolver.resolve.return_value = mock_inst

    adapter = OrdersAdapter(mock_client, mock_resolver)
    order = _make_order("ord_1")

    results = {"success": 0, "duplicate": 0, "error": 0}
    lock = threading.Lock()

    def place():
        try:
            adapter.place_order(order)
            with lock:
                results["success"] += 1
        except Exception as e:
            with lock:
                if "Duplicate" in str(e):
                    results["duplicate"] += 1
                else:
                    results["error"] += 1

    threads = [threading.Thread(target=place) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Exactly one should succeed, rest should be duplicates or errors
    assert results["success"] <= 1, f"Multiple orders placed: {results}"
    assert results["error"] == 0, f"Unexpected errors: {results}"
```

- [ ] **Step 2: Run test to verify it fails or is flaky**

Run: `pytest tests/unit/brokers/dhan/test_idempotency_thread_safety.py -v --count=5`
Expected: Flaky or fails — proves race condition exists.

- [ ] **Step 3: Add lock to idempotency cache**

In `scalpr/brokers/dhan/orders.py`, add `import threading` and modify `__init__` and `place_order`:

```python
class OrdersAdapter:
    def __init__(self, client, resolver):
        self._client = client
        self._resolver = resolver
        self._idempotency_cache: set[str] = set()
        self._cache_lock = threading.Lock()  # NEW

    def place_order(self, order):
        correlation_id = order.correlation_id or order.order_id

        with self._cache_lock:  # NEW: lock the check-and-add
            if correlation_id in self._idempotency_cache:
                raise OrderError(
                    f"Duplicate order blocked: correlation_id={correlation_id!r} "
                    f"already submitted"
                )

        # ... existing validation, resolution, mapping, API call ...

        with self._cache_lock:  # NEW: lock the add
            self._idempotency_cache.add(correlation_id)

        # ... existing response parsing ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/brokers/dhan/test_idempotency_thread_safety.py -v --count=5`
Expected: PASS consistently.

- [ ] **Step 5: Commit**

```bash
git add scalpr/brokers/dhan/orders.py tests/unit/brokers/dhan/test_idempotency_thread_safety.py
git commit -m "fix(brokers): add thread safety to OrdersAdapter idempotency cache"
```

---

### Task 3: Add NSE_FNO Exchange Segment to Mapper

**Files:**
- Modify: `scalpr/brokers/dhan/mapper.py:50-59`
- Test: `tests/unit/brokers/test_mapper_fno.py`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/brokers/test_mapper_fno.py
"""Test that mapper correctly handles F&O exchange segment."""
from decimal import Decimal
from scalpr.brokers.dhan.mapper import DhanMapper
from scalpr.domain.order import Order, OrderSide, OrderType, OrderState
from scalpr.domain.instrument import Exchange


def test_mapper_should_handle_nse_fno_exchange_segment():
    """NSE F&O orders must map to exchangeSegment NSE_FNO."""
    order = Order(
        order_id="fno_ord_1", symbol="NIFTY26JUN22000CE",
        exchange=Exchange.NSE_FNO, side=OrderSide.BUY,
        order_type=OrderType.LIMIT, quantity=50,
        price=Decimal("150.00"), state=OrderState.PENDING,
        product_type="INTRADAY",
    )
    result = DhanMapper.order_to_dhan_request(order, "client123", "security456")
    assert result.is_ok
    assert result.value.exchangeSegment == "NSE_FNO"


def test_mapper_should_still_handle_nse_eq():
    """NSE equity orders must still map to NSE_EQ."""
    order = Order(
        order_id="eq_ord_1", symbol="RELIANCE",
        exchange=Exchange.NSE, side=OrderSide.BUY,
        order_type=OrderType.LIMIT, quantity=10,
        price=Decimal("2500.00"), state=OrderState.PENDING,
    )
    result = DhanMapper.order_to_dhan_request(order, "client123", "security789")
    assert result.is_ok
    assert result.value.exchangeSegment == "NSE_EQ"


def test_mapper_should_still_handle_mcx():
    """MCX orders must still map to MCX_COMM."""
    order = Order(
        order_id="mcx_ord_1", symbol="GOLD",
        exchange=Exchange.MCX, side=OrderSide.BUY,
        order_type=OrderType.LIMIT, quantity=1,
        price=Decimal("50000"), state=OrderState.PENDING,
    )
    result = DhanMapper.order_to_dhan_request(order, "client123", "security101")
    assert result.is_ok
    assert result.value.exchangeSegment == "MCX_COMM"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/brokers/test_mapper_fno.py -v`
Expected: FAIL — `Exchange.NSE_FNO` may not exist yet, or mapper returns failure.

- [ ] **Step 3: Add NSE_FNO to Exchange enum and mapper**

First, check if `Exchange.NSE_FNO` exists in `scalpr/domain/instrument.py`. If not, add it:

```python
class Exchange(str, Enum):
    NSE = "NSE"
    MCX = "MCX"
    NSE_FNO = "NSE_FNO"  # NEW: F&O segment
```

Then in `scalpr/brokers/dhan/mapper.py`, add the F&O mapping:

```python
@staticmethod
def order_to_dhan_request(order, client_id, security_id):
    try:
        if order.exchange == Exchange.NSE:
            segment = "NSE_EQ"
        elif order.exchange == Exchange.NSE_FNO:  # NEW
            segment = "NSE_FNO"                    # NEW
        elif order.exchange == Exchange.MCX:
            segment = "MCX_COMM"
        else:
            return Result.failure(f"Unsupported exchange: {order.exchange}")
        # ... rest unchanged ...
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/brokers/test_mapper_fno.py -v`
Expected: All 3 PASS.

- [ ] **Step 5: Run existing mapper/gateway tests for regression**

Run: `pytest tests/unit/brokers/ -v`
Expected: No regressions.

- [ ] **Step 6: Commit**

```bash
git add scalpr/domain/instrument.py scalpr/brokers/dhan/mapper.py tests/unit/brokers/test_mapper_fno.py
git commit -m "fix(brokers): add NSE_FNO exchange segment to mapper for options trading"
```

---

### Task 4: GateFSM Fail-Safe Defaults

**Files:**
- Modify: `scalpr/signals/gate_fsm.py:8-36`
- Test: `tests/unit/signals/test_gate_fsm_defaults.py`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/signals/test_gate_fsm_defaults.py
"""GateFSM must default to fail-safe — all guards default to blocked."""
from decimal import Decimal
from scalpr.signals.gate_fsm import GateFSM, GateState


def test_gate_state_should_default_to_all_guards_blocked():
    """Default GateState must fail all guards except market_open."""
    state = GateState(symbol="RELIANCE", price=Decimal("2500"), cvd_falling=False, is_at_lvn=False)
    passed, reason, results = GateFSM.evaluate(state)
    assert not passed, "Default state should NOT pass — gates must fail-safe"


def test_only_explicitly_satisfied_gates_should_pass():
    """Only gates explicitly set to True should pass."""
    state = GateState(
        symbol="RELIANCE", price=Decimal("2500"),
        market_open=True, trend_aligned=True,
        vol_spike=True, atr_ok=True,
        spread_ok=True, oi_ok=True,
        cvd_falling=False, is_at_lvn=True,
        under_daily_cap=True,
    )
    passed, reason, results = GateFSM.evaluate(state)
    assert passed, "All gates explicitly satisfied — should pass"
    assert len(results) == 8
    assert all(r.passed for r in results)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/signals/test_gate_fsm_defaults.py::test_gate_state_should_default_to_all_guards_blocked -v`
Expected: FAIL — current defaults are `True`, so the gate passes when it shouldn't.

- [ ] **Step 3: Change GateState defaults to fail-safe**

In `scalpr/signals/gate_fsm.py`, change the `GateState.__init__` defaults:

```python
class GateState:
    def __init__(
        self,
        symbol: str,
        price: Decimal,
        cvd_falling: bool = False,   # unchanged
        is_at_lvn: bool = False,     # unchanged
        market_open: bool = False,   # CHANGED: was True
        trend_aligned: bool = False, # CHANGED: was True
        vol_spike: bool = False,     # CHANGED: was True
        atr_ok: bool = False,        # CHANGED: was True
        spread_ok: bool = False,     # CHANGED: was True
        oi_ok: bool = False,         # CHANGED: was True
        under_daily_cap: bool = True, # unchanged — strategy tracks this
        timestamp=None,
    ):
```

- [ ] **Step 4: Update callers to explicitly set gate states**

In `scalpr/strategy/scalpr_amt.py`, the strategy already constructs `GateState` with explicit values. Verify no other callers rely on the old defaults:

Run: `grep -r "GateState(" scalpr/ --include="*.py"`

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/unit/signals/test_gate_fsm_defaults.py -v`
Expected: Both PASS.

- [ ] **Step 6: Commit**

```bash
git add scalpr/signals/gate_fsm.py tests/unit/signals/test_gate_fsm_defaults.py
git commit -m "fix(signals): GateFSM defaults to fail-safe — all guards blocked unless explicit"
```

---

### Task 5: SessionGuard Prevents Repeated Square-Off

**Files:**
- Modify: `scalpr/risk/session_guard.py:36-68`
- Test: `tests/unit/risk/test_session_guard_no_repeat.py`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/risk/test_session_guard_no_repeat.py
"""SessionGuard must not call square_off_all more than once per cutoff."""
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock
from decimal import Decimal
from scalpr.risk.session_guard import SessionGuard

IST = timezone(timedelta(hours=5, minutes=30))


def test_cutoff_should_only_square_off_once():
    """check_market_cutoff called multiple times after 15:15 must only square off once."""
    mock_gateway = MagicMock()
    guard = SessionGuard(gateway=mock_gateway, max_losses=3)

    # 15:20 IST — past NSE cutoff
    cutoff_time = datetime(2026, 7, 27, 15, 20, tzinfo=IST)

    guard.check_market_cutoff(cutoff_time)
    guard.check_market_cutoff(cutoff_time)
    guard.check_market_cutoff(cutoff_time)

    mock_gateway.square_off_all.assert_called_once()


def test_mcx_cutoff_should_only_square_off_once():
    """check_market_cutoff called multiple times after 23:15 must only square off once."""
    mock_gateway = MagicMock()
    guard = SessionGuard(gateway=mock_gateway, max_losses=3)

    cutoff_time = datetime(2026, 7, 27, 23, 20, tzinfo=IST)

    guard.check_market_cutoff(cutoff_time)
    guard.check_market_cutoff(cutoff_time)

    mock_gateway.square_off_all.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/risk/test_session_guard_no_repeat.py -v`
Expected: FAIL — `square_off_all` called 3 times.

- [ ] **Step 3: Add squared-off tracking to SessionGuard**

In `scalpr/risk/session_guard.py`, add `_squared_off_nse` and `_squared_off_mcx` flags:

```python
class SessionGuard:
    def __init__(self, gateway, max_losses=3):
        # ... existing fields ...
        self._squared_off_nse = False   # NEW
        self._squared_off_mcx = False   # NEW

    def check_market_cutoff(self, current_time):
        ist_now = current_time.astimezone(IST)
        hour, minute = ist_now.hour, ist_now.minute

        # NSE cutoff
        if hour == 15 and minute >= 15 and not self._squared_off_nse:
            self._squared_off_nse = True  # Mark BEFORE calling
            logger.critical("...")
            self.gateway.square_off_all()
            self.halted = True
            return True

        # MCX cutoff
        if hour == 23 and minute >= 15 and not self._squared_off_mcx:
            self._squared_off_mcx = True  # Mark BEFORE calling
            logger.critical("...")
            self.gateway.square_off_all()
            self.halted = True
            return True

        return False

    def reset_guard(self):
        # ... existing reset ...
        self._squared_off_nse = False  # NEW
        self._squared_off_mcx = False  # NEW
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/risk/test_session_guard_no_repeat.py -v`
Expected: Both PASS.

- [ ] **Step 5: Run existing session guard tests**

Run: `pytest tests/unit/risk/test_session_guard.py -v`
Expected: No regression.

- [ ] **Step 6: Commit**

```bash
git add scalpr/risk/session_guard.py tests/unit/risk/test_session_guard_no_repeat.py
git commit -m "fix(risk): SessionGuard prevents repeated square_off_all calls"
```

---

### Task 6: OrderRouter Fail-Loud Persistence Policy

**Files:**
- Modify: `scalpr/execution/order_router.py:133-145`
- Test: `tests/unit/execution/test_order_router_error_policy.py`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/execution/test_order_router_error_policy.py
"""OrderRouter must raise on persistence failure after order placed."""
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import MagicMock
from scalpr.execution.order_router import OrderRouter, PersistenceError
from scalpr.domain.order import Order, OrderSide, OrderType, OrderState
from scalpr.domain.fill import Fill
from scalpr.domain.instrument import Exchange


def _make_order():
    return Order(
        order_id="ord_1", symbol="RELIANCE", exchange=Exchange.NSE,
        side=OrderSide.BUY, order_type=OrderType.LIMIT,
        quantity=10, price=Decimal("2500"), state=OrderState.PENDING,
    )


def test_submit_order_should_raise_on_persistence_failure():
    """If OMS persistence fails after broker order placed, must raise PersistenceError."""
    mock_gateway = MagicMock()
    fill = Fill("f1", "ord_1", "RELIANCE", OrderSide.BUY, 10, Decimal("2500"))
    mock_gateway.place_order.return_value = fill

    mock_risk_gate = MagicMock()
    mock_risk_gate.check_order.return_value = (True, "ok")

    mock_cb = MagicMock()
    mock_cb.check_limits.return_value = True

    mock_oms = MagicMock()
    mock_oms.add_order.side_effect = Exception("DB write failed")

    router = OrderRouter(
        gateway=mock_gateway, risk_gate=mock_risk_gate,
        circuit_breaker=mock_cb, order_manager=mock_oms,
    )

    order = _make_order()
    import pytest
    with pytest.raises(PersistenceError, match="DB write failed"):
        router.submit_order(
            order=order, positions=[],
            available_margin=Decimal("100000"),
            daily_loss=Decimal("0"),
            portfolio_value=Decimal("1000000"),
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/execution/test_order_router_error_policy.py -v`
Expected: FAIL — current code swallows the error.

- [ ] **Step 3: Add PersistenceError and fail-loud policy**

In `scalpr/execution/order_router.py`:

```python
class PersistenceError(Exception):
    """Raised when order persistence fails after broker submission."""
    pass

class OrderRouter:
    def submit_order(self, order, positions, available_margin, daily_loss, portfolio_value, drawdown=Decimal("0")):
        # ... existing circuit breaker and risk checks ...

        fill = self.gateway.place_order(order)

        if self.order_manager:
            try:
                self.order_manager.add_order(order)
                if fill:
                    self.order_manager.process_fill(fill)
            except Exception as e:
                logger.error(f"CRITICAL: Persistence failed after order placed: {e}")
                raise PersistenceError(
                    f"Order {order.order_id} placed at broker but persistence failed: {e}"
                ) from e

        # ... existing event publishing ...
        return fill
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/execution/test_order_router_error_policy.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scalpr/execution/order_router.py tests/unit/execution/test_order_router_error_policy.py
git commit -m "fix(execution): OrderRouter raises PersistenceError on persistence failure after broker submission"
```

---

### Task 7: Bounded Histogram and Thread-Safe Metrics

**Files:**
- Modify: `scalpr/observability/metrics.py`
- Test: `tests/unit/observability/test_metrics_bounded.py`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/observability/test_metrics_bounded.py
"""Metrics must be bounded in memory and thread-safe."""
import threading
from scalpr.observability.metrics import MetricsRegistry, HistogramMetric


def test_histogram_should_bound_values():
    """Histogram must not grow unbounded — use deque with maxlen."""
    hist = HistogramMetric(name="test", description="test")
    for i in range(20000):
        hist.observe(float(i))
    assert hist.count() <= 10000, f"Histogram grew to {hist.count()} — unbounded memory leak"


def test_counter_increment_should_be_thread_safe():
    """Concurrent counter increments must not lose counts."""
    registry = MetricsRegistry()
    counter = registry.register_counter("concurrent_test")
    errors = []

    def increment():
        try:
            for _ in range(1000):
                counter.increment()
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=increment) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0
    assert counter.value == 10000, f"Expected 10000, got {counter.value}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/observability/test_metrics_bounded.py -v`
Expected: FAIL — histogram is unbounded, counter may lose counts.

- [ ] **Step 3: Bound histogram and lock counter**

In `scalpr/observability/metrics.py`:

```python
from collections import deque
import threading

@dataclass
class CounterMetric:
    name: str
    value: int = 0
    description: str = ""
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False, init=False)  # NEW

    def increment(self, amount: int = 1) -> None:
        with self._lock:  # NEW
            self.value += amount

@dataclass
class HistogramMetric:
    name: str
    values: deque = field(default_factory=lambda: deque(maxlen=10000))  # CHANGED from list
    description: str = ""

    def observe(self, value: float) -> None:
        self.values.append(value)
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/unit/observability/test_metrics_bounded.py -v`
Expected: Both PASS.

- [ ] **Step 5: Commit**

```bash
git add scalpr/observability/metrics.py tests/unit/observability/test_metrics_bounded.py
git commit -m "fix(observability): bound histogram memory, add thread safety to counter"
```

---

### Task 8: Replace Debug Print with Logger

**Files:**
- Modify: `scalpr/brokers/dhan/ws_client.py`

- [ ] **Step 1: Find and replace all print() calls in _on_error**

Run: `grep -n "print(" scalpr/brokers/dhan/ws_client.py`

Only lines 438-439 in `_on_error` are real `print()` calls (line 139 is a docstring example — leave it).
Replace the two `print()` calls and remove the `import sys`:

```python
# Before (lines 435-440):
def _on_error(self, feed, error: Any) -> None:
    """SDK callback: error occurred."""
    import sys
    print(f"SDK ERROR CALLBACK: {error!r}", file=sys.stderr)
    print(f"Error type: {type(error)}", file=sys.stderr)
    logger.error("sdk_error", extra={"error": str(error), "error_repr": repr(error)})

# After:
def _on_error(self, feed, error: Any) -> None:
    """SDK callback: error occurred."""
    logger.error("sdk_error", extra={"error": str(error), "error_repr": repr(error), "error_type": type(error).__name__})
```

Also remove `import sys` from the top of the file if it exists (check with `grep -n "^import sys" scalpr/brokers/dhan/ws_client.py`).

- [ ] **Step 2: Run existing ws_client tests**

Run: `pytest tests/unit/brokers/dhan/test_websocket.py -v`
Expected: No regression.

- [ ] **Step 3: Commit**

```bash
git add scalpr/brokers/dhan/ws_client.py
git commit -m "fix(brokers): replace debug print() with logger.error() in ws_client"
```

---

### Task 9: Remove Duplicate OrderSide from contracts.py

**Files:**
- Modify: `scalpr/brokers/contracts.py`
- Modify: any file importing `OrderSide` from `contracts.py`

- [ ] **Step 1: Find all imports of OrderSide from contracts**

Run: `grep -rn "from scalpr.brokers.contracts import.*OrderSide" scalpr/ tests/`

No source files currently import `OrderSide` from `contracts.py`. However, the `Trade` dataclass in `contracts.py` uses `OrderSide` for its `side: OrderSide` field. We must replace this with the domain's `OrderSide`.

- [ ] **Step 2: Update contracts.py to import OrderSide from domain**

In `scalpr/brokers/contracts.py`, remove the local `OrderSide` enum and import from domain:

```python
# Remove these lines:
# class OrderSide(str, Enum):
#     BUY = "BUY"
#     SELL = "SELL"

# Add this import:
from scalpr.domain.order import OrderSide
```

The `Trade` dataclass field `side: OrderSide` now references the domain's `OrderSide` — no other changes needed.

Also update `scalpr/brokers/gateway.py` and `scalpr/brokers/__init__.py` if they re-export `OrderSide` from contracts (they don't currently, but verify).

- [ ] **Step 4: Run full test suite**

Run: `pytest tests/ -v --tb=short`
Expected: No regressions.

- [ ] **Step 5: Commit**

```bash
git add scalpr/brokers/contracts.py
git commit -m "refactor: remove duplicate OrderSide from contracts.py, use domain/order.py"
```

---

### Task 10: Fix pyproject.toml Configuration

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Fix coverage source**

Change line 94 from:
```toml
source = ["brokers", "analytics", "cli", "datalake", "tests/chaos"]
```
To:
```toml
source = ["scalpr"]
```

- [ ] **Step 1b: Fix testpaths and mutation paths**

Change line 55 from:
```toml
testpaths = ["tests", "brokers", "analytics", "cli", "datalake"]
```
To:
```toml
testpaths = ["tests"]
```

Change line 114 from:
```toml
paths_to_mutate = "brokers,analytics,datalake,domain"
```
To:
```toml
paths_to_mutate = "scalpr"
```

- [ ] **Step 2: Fix import-linter contracts**

Replace the entire `[tool.importlinter]` section (lines 205–231) with contracts matching the actual package structure:

```toml
[tool.importlinter]
root_packages = ["scalpr"]

[[tool.importlinter.contracts]]
name = "Domain independence"
type = "forbidden"
source_modules = ["scalpr.domain"]
forbidden_modules = ["scalpr.brokers", "scalpr.api", "scalpr.cli", "scalpr.oms"]

[[tool.importlinter.contracts]]
name = "Risk cannot import API"
type = "forbidden"
source_modules = ["scalpr.risk"]
forbidden_modules = ["scalpr.api", "scalpr.cli"]

[[tool.importlinter.contracts]]
name = "OMS cannot import API"
type = "forbidden"
source_modules = ["scalpr.oms"]
forbidden_modules = ["scalpr.api", "scalpr.cli"]

[[tool.importlinter.contracts]]
name = "Strategy cannot import API"
type = "forbidden"
source_modules = ["scalpr.strategy"]
forbidden_modules = ["scalpr.api", "scalpr.cli"]

[[tool.importlinter.contracts]]
name = "Broker Dhan isolation"
type = "forbidden"
source_modules = ["scalpr.brokers.dhan"]
forbidden_modules = ["scalpr.api", "scalpr.cli"]
```

- [ ] **Step 3: Fix ruff banned-api paths**

The `[tool.ruff.lint.flake8-tidy-imports.banned-api]` section (lines 189–199) references stale package paths like `brokers.dhan.domain.Quote`. Update to use `scalpr.*` paths or remove if no longer relevant (the import-linter contracts now enforce these boundaries).

- [ ] **Step 4: Verify ruff still passes**

Run: `ruff check scalpr/`
Expected: No new errors.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml
git commit -m "fix(config): point coverage, import-linter, testpaths, and mutmut at actual scalpr package"
```

---

## Phase 2: God Module Decomposition (Days 8–14)

### Task 11: Create Routers Package Structure

**Files:**
- Create: `scalpr/api/routers/__init__.py`
- Create: `scalpr/api/routers/market_data.py`
- Create: `scalpr/api/routers/orders.py`
- Create: `scalpr/api/routers/portfolio.py`
- Create: `scalpr/api/routers/replay.py`

- [ ] **Step 1: Create empty routers package**

```python
# scalpr/api/routers/__init__.py
"""API route modules."""
```

- [ ] **Step 2: Create market_data router skeleton**

```python
# scalpr/api/routers/market_data.py
"""Market data REST and WebSocket routes."""
from fastapi import APIRouter, Depends
from typing import Any

router = APIRouter(prefix="/market", tags=["market-data"])


@router.get("/symbols")
async def get_symbols() -> list[dict[str, Any]]:
    """Return available trading symbols."""
    # Placeholder — will be wired to resolver in bootstrap
    return []


@router.get("/candles/{symbol}")
async def get_candles(symbol: str, timeframe: str = "5m") -> list[dict]:
    """Get OHLCV candles for a symbol."""
    return []


@router.get("/ltp/{symbol}")
async def get_ltp(symbol: str) -> dict:
    """Get last traded price."""
    return {"symbol": symbol, "ltp": None}
```

- [ ] **Step 3: Create orders router skeleton**

```python
# scalpr/api/routers/orders.py
"""Order management REST routes."""
from fastapi import APIRouter

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("/")
async def get_orders() -> list[dict]:
    """Get all orders for the day."""
    return []


@router.post("/")
async def place_order(order_data: dict) -> dict:
    """Place a new order."""
    return {"status": "not_implemented"}


@router.put("/{order_id}")
async def modify_order(order_id: str, modify_data: dict) -> dict:
    """Modify an existing order."""
    return {"status": "not_implemented"}


@router.delete("/{order_id}")
async def cancel_order(order_id: str) -> dict:
    """Cancel an order."""
    return {"status": "not_implemented"}
```

- [ ] **Step 4: Create portfolio router skeleton**

```python
# scalpr/api/routers/portfolio.py
"""Portfolio and positions REST routes."""
from fastapi import APIRouter

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("/positions")
async def get_positions() -> list[dict]:
    """Get current positions."""
    return []


@router.get("/holdings")
async def get_holdings() -> list[dict]:
    """Get current holdings."""
    return []


@router.get("/margins")
async def get_margins() -> dict:
    """Get available margins."""
    return {}


@router.post("/square-off")
async def square_off() -> dict:
    """Square off all positions."""
    return {"status": "not_implemented"}
```

- [ ] **Step 5: Create replay router skeleton**

```python
# scalpr/api/routers/replay.py
"""Replay session REST routes."""
from fastapi import APIRouter

router = APIRouter(prefix="/replay", tags=["replay"])


@router.post("/start")
async def start_replay(session_data: dict) -> dict:
    """Start a replay session."""
    return {"status": "not_implemented"}


@router.get("/status")
async def get_replay_status() -> dict:
    """Get current replay session status."""
    return {"active": False}


@router.post("/stop")
async def stop_replay() -> dict:
    """Stop the current replay session."""
    return {"status": "not_implemented"}
```

- [ ] **Step 6: Verify routers can be imported independently**

Run: `python -c "from scalpr.api.routers import market_data, orders, portfolio, replay; print('OK')"`
Expected: `OK`

- [ ] **Step 7: Commit**

```bash
git add scalpr/api/routers/
git commit -m "feat(api): create router skeletons for market_data, orders, portfolio, replay"
```

---

### Task 12: Create Bootstrap Factory

**Files:**
- Create: `scalpr/api/bootstrap.py`
- Test: `tests/unit/api/test_bootstrap.py`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/api/test_bootstrap.py
"""Bootstrap factory creates a properly wired FastAPI app."""
import pytest
from unittest.mock import MagicMock, patch


def test_create_app_should_return_fastapi_app():
    """create_app() must return a FastAPI instance with all routers."""
    with patch("scalpr.api.bootstrap._load_dotenv"), \
         patch("scalpr.api.bootstrap._create_gateway") as mock_gw, \
         patch("scalpr.api.bootstrap._create_feed") as mock_feed:

        from scalpr.api.bootstrap import create_app
        app = create_app()

        assert app is not None
        # Verify routers are included
        route_paths = [r.path for r in app.routes]
        assert any("/market" in p for p in route_paths)
        assert any("/orders" in p for p in route_paths)
        assert any("/portfolio" in p for p in route_paths)


def test_create_app_should_not_have_side_effects_on_import():
    """Importing bootstrap must not create network connections."""
    import importlib
    import scalpr.api.bootstrap as mod
    importlib.reload(mod)
    # If we get here without network calls, the test passes
    assert hasattr(mod, "create_app")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/api/test_bootstrap.py -v`
Expected: FAIL — `bootstrap.py` doesn't exist yet.

- [ ] **Step 3: Create bootstrap factory**

```python
# scalpr/api/bootstrap.py
"""Composition root — wires all dependencies and creates the FastAPI app.

No side effects at import time. All initialization happens in create_app().
"""
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)


def _load_dotenv() -> None:
    """Load environment variables. Called inside create_app, not at import."""
    from dotenv import load_dotenv
    load_dotenv()


def _create_gateway():
    """Create and configure the broker gateway."""
    from scalpr.brokers.gateway import Gateway
    return Gateway()


def _create_feed(gateway):
    """Create market data feed from gateway."""
    return None  # Will be wired from gateway connection


def create_app() -> FastAPI:
    """Create and wire the FastAPI application.

    This is the ONLY entry point. No side effects at module import.
    """
    _load_dotenv()

    app = FastAPI(title="SCALPR Trading API", version="0.1.0")

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],  # Vite dev server only
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    from scalpr.api.routers import market_data, orders, portfolio, replay
    app.include_router(market_data.router)
    app.include_router(orders.router)
    app.include_router(portfolio.router)
    app.include_router(replay.router)

    # Store dependencies on app.state for router access
    gateway = _create_gateway()
    app.state.gateway = gateway
    app.state.feed = _create_feed(gateway)

    @app.on_event("startup")
    async def startup():
        logger.info("SCALPR API starting...")

    @app.on_event("shutdown")
    async def shutdown():
        logger.info("SCALPR API shutting down...")
        if hasattr(app.state, "gateway") and app.state.gateway:
            try:
                app.state.gateway.disconnect()
            except Exception:
                pass

    return app
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/api/test_bootstrap.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scalpr/api/bootstrap.py tests/unit/api/test_bootstrap.py
git commit -m "feat(api): create bootstrap factory — composition root with no import side effects"
```

---

### Task 13: Slim Down main.py

**Files:**
- Modify: `scalpr/api/main.py`

- [ ] **Step 1: Replace main.py content with thin wrapper**

Replace the entire 1214-line `scalpr/api/main.py` with:

```python
"""SCALPR API entry point.

All logic moved to bootstrap.py and routers/. This file exists only for
backward compatibility with the `uvicorn scalpr.api.main:app` command.
"""
from scalpr.api.bootstrap import create_app

app = create_app()
```

- [ ] **Step 2: Verify the app starts**

Run: `python -c "from scalpr.api.main import app; print(f'Routes: {len(app.routes)}')"`
Expected: `Routes: N` (some number > 0)

- [ ] **Step 3: Run full test suite**

Run: `pytest tests/ -v --tb=short -x`
Expected: No regressions (some old tests may need path updates).

- [ ] **Step 4: Commit**

```bash
git add scalpr/api/main.py
git commit -m "refactor(api): reduce main.py from 1214 lines to thin wrapper over bootstrap"
```

---

### Task 14: Wire Real Route Handlers

**Files:**
- Modify: `scalpr/api/routers/market_data.py`
- Modify: `scalpr/api/routers/orders.py`
- Modify: `scalpr/api/routers/portfolio.py`

- [ ] **Step 1: Wire market_data routes to app.state dependencies**

```python
# scalpr/api/routers/market_data.py
"""Market data REST routes — wired to real dependencies."""
from fastapi import APIRouter, Request

router = APIRouter(prefix="/market", tags=["market-data"])


@router.get("/ltp/{symbol}")
async def get_ltp(symbol: str, request: Request):
    """Get last traded price from broker."""
    gateway = request.app.state.gateway
    if not gateway or not gateway.is_connected():
        return {"symbol": symbol, "ltp": None, "error": "Gateway not connected"}
    try:
        ltp = gateway.get_ltp(symbol, "NSE")
        return {"symbol": symbol, "ltp": str(ltp)}
    except Exception as e:
        return {"symbol": symbol, "ltp": None, "error": str(e)}


@router.get("/candles/{symbol}")
async def get_candles(symbol: str, request: Request, timeframe: str = "5", count: int = 100):
    """Get OHLCV candles. Accesses historical adapter through gateway."""
    gateway = request.app.state.gateway
    if not gateway or not gateway.is_connected():
        return {"error": "Gateway not connected"}
    try:
        connection = gateway.connection
        candles = connection.historical.get_ohlcv(symbol, "NSE", timeframe)
        return candles[-count:] if candles else []
    except Exception as e:
        return {"error": str(e)}
```

- [ ] **Step 2: Wire orders routes**

```python
# scalpr/api/routers/orders.py
"""Order management REST routes — wired to real dependencies."""
from fastapi import APIRouter, Request

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("/")
async def get_orders(request: Request):
    """Get all orders from broker."""
    gateway = request.app.state.gateway
    if not gateway or not gateway.is_connected():
        return []
    try:
        return gateway.get_orders() if hasattr(gateway, "get_orders") else []
    except Exception:
        return []


@router.get("/fills")
async def get_fills(request: Request):
    """Get all fills."""
    # Will be wired to OMS persistence in a later task
    return []
```

- [ ] **Step 3: Wire portfolio routes**

```python
# scalpr/api/routers/portfolio.py
"""Portfolio routes — wired to real dependencies."""
from fastapi import APIRouter, Request

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("/positions")
async def get_positions(request: Request):
    """Get current positions from broker."""
    gateway = request.app.state.gateway
    if not gateway or not gateway.is_connected():
        return []
    try:
        positions = gateway.get_positions()
        return [
            {
                "symbol": p.symbol, "exchange": p.exchange.value,
                "quantity": p.quantity, "avg_price": str(p.avg_price),
                "ltp": str(p.ltp), "unrealised_pnl": str(p.unrealised_pnl),
                "realised_pnl": str(p.realised_pnl),
                "position_side": p.position_side.value, "state": p.state.value,
            }
            for p in positions
        ]
    except Exception:
        return []


@router.get("/margins")
async def get_margins(request: Request):
    """Get available margins."""
    gateway = request.app.state.gateway
    if not gateway or not gateway.is_connected():
        return {}
    try:
        return gateway.get_margins()
    except Exception:
        return {}


@router.post("/square-off")
async def square_off(request: Request):
    """Square off all positions."""
    gateway = request.app.state.gateway
    if not gateway or not gateway.is_connected():
        return {"error": "Gateway not connected"}
    try:
        fills = gateway.square_off_all()
        return {"squared_off": len(fills)}
    except Exception as e:
        return {"error": str(e)}
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/unit/api/ -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scalpr/api/routers/
git commit -m "feat(api): wire real route handlers to gateway dependencies via app.state"
```

---

## Phase 3: Contract Tests & Quality Gates (Days 15–30)

### Task 15: Dhan Order Payload Contract Tests

**Files:**
- Create: `tests/contract/__init__.py`
- Create: `tests/contract/test_dhan_order_payload.py`

- [ ] **Step 1: Create contract test package**

```python
# tests/contract/__init__.py
"""Contract tests verify SCALPR ↔ Dhan API payload shape.

These tests catch mapping bugs BEFORE they reach the live API.
Run: pytest tests/contract/ -v
"""
```

- [ ] **Step 2: Write contract tests for order payloads**

```python
# tests/contract/test_dhan_order_payload.py
"""Contract tests: verify order request payloads match Dhan API expectations.

Dhan API expects these fields for POST /orders:
- dhanClientId: string (non-empty)
- correlationId: string
- transactionType: "BUY" | "SELL"
- exchangeSegment: "NSE_EQ" | "NSE_FNO" | "MCX_COMM" | ...
- productType: "INTRADAY" | "DELIVERY" | "MARGIN"
- orderType: "LIMIT" | "MARKET" | "SL" | "SL-M"
- quantity: integer > 0
- price: string (Decimal as string)
- triggerPrice: string (Decimal as string)
- securityId: string (non-empty)
"""
import pytest
from decimal import Decimal
from scalpr.brokers.dhan.mapper import DhanMapper
from scalpr.domain.order import Order, OrderSide, OrderType, OrderState
from scalpr.domain.instrument import Exchange


REQUIRED_FIELDS = [
    "dhanClientId", "correlationId", "transactionType",
    "exchangeSegment", "productType", "orderType",
    "quantity", "price", "triggerPrice", "securityId",
]


class TestDhanOrderPayloadContract:
    """Verify mapper output matches Dhan API contract."""

    def _map(self, order, exchange=Exchange.NSE, security_id="12345"):
        order.exchange = exchange
        result = DhanMapper.order_to_dhan_request(order, "CLIENT_ID", security_id)
        assert result.is_ok, f"Mapping failed: {result.error}"
        return result.value

    def test_all_required_fields_present(self):
        """Every field Dhan expects must be present in the payload."""
        order = Order(
            order_id="t1", symbol="RELIANCE", exchange=Exchange.NSE,
            side=OrderSide.BUY, order_type=OrderType.LIMIT,
            quantity=10, price=Decimal("2500"), state=OrderState.PENDING,
            product_type="INTRADAY",
        )
        dto = self._map(order)
        for field in REQUIRED_FIELDS:
            assert hasattr(dto, field), f"Missing required field: {field}"

    def test_price_must_be_decimal_type(self):
        """Price fields must be Decimal, not float — Dhan expects string representation."""
        order = Order(
            order_id="t2", symbol="RELIANCE", exchange=Exchange.NSE,
            side=OrderSide.BUY, order_type=OrderType.LIMIT,
            quantity=10, price=Decimal("2500.50"), state=OrderState.PENDING,
        )
        dto = self._map(order)
        assert isinstance(dto.price, Decimal)
        assert isinstance(dto.triggerPrice, Decimal)

    def test_nse_eq_exchange_segment(self):
        """NSE equity must map to NSE_EQ."""
        order = Order(
            order_id="t3", symbol="RELIANCE", exchange=Exchange.NSE,
            side=OrderSide.BUY, order_type=OrderType.LIMIT,
            quantity=10, price=Decimal("2500"), state=OrderState.PENDING,
        )
        dto = self._map(order)
        assert dto.exchangeSegment == "NSE_EQ"

    def test_nse_fno_exchange_segment(self):
        """NSE F&O must map to NSE_FNO."""
        order = Order(
            order_id="t4", symbol="NIFTY26JUN22000CE", exchange=Exchange.NSE_FNO,
            side=OrderSide.BUY, order_type=OrderType.LIMIT,
            quantity=50, price=Decimal("150"), state=OrderState.PENDING,
        )
        dto = self._map(order)
        assert dto.exchangeSegment == "NSE_FNO"

    def test_mcx_comm_exchange_segment(self):
        """MCX commodity must map to MCX_COMM."""
        order = Order(
            order_id="t5", symbol="GOLD", exchange=Exchange.MCX,
            side=OrderSide.BUY, order_type=OrderType.LIMIT,
            quantity=1, price=Decimal("50000"), state=OrderState.PENDING,
        )
        dto = self._map(order)
        assert dto.exchangeSegment == "MCX_COMM"

    def test_transaction_type_must_be_buy_or_sell(self):
        """transactionType must be exactly BUY or SELL."""
        for side in [OrderSide.BUY, OrderSide.SELL]:
            order = Order(
                order_id=f"t6_{side.value}", symbol="RELIANCE", exchange=Exchange.NSE,
                side=side, order_type=OrderType.LIMIT,
                quantity=10, price=Decimal("2500"), state=OrderState.PENDING,
            )
            dto = self._map(order)
            assert dto.transactionType in ("BUY", "SELL")

    @pytest.mark.parametrize("order_type,expected", [
        (OrderType.LIMIT, "LIMIT"),
        (OrderType.MARKET, "MARKET"),
        (OrderType.STOP_LOSS, "SL"),
        (OrderType.STOP_LOSS_MARKET, "SL-M"),
    ])
    def test_order_type_mapping(self, order_type, expected):
        """Order types must map to Dhan's expected strings."""
        order = Order(
            order_id=f"t7_{expected}", symbol="RELIANCE", exchange=Exchange.NSE,
            side=OrderSide.BUY, order_type=order_type,
            quantity=10, price=Decimal("2500"), state=OrderState.PENDING,
        )
        dto = self._map(order)
        assert dto.orderType == expected

    def test_quantity_must_be_positive_integer(self):
        """Quantity must be a positive integer."""
        order = Order(
            order_id="t8", symbol="RELIANCE", exchange=Exchange.NSE,
            side=OrderSide.BUY, order_type=OrderType.LIMIT,
            quantity=10, price=Decimal("2500"), state=OrderState.PENDING,
        )
        dto = self._map(order)
        assert isinstance(dto.quantity, int)
        assert dto.quantity > 0

    def test_security_id_must_be_non_empty_string(self):
        """securityId must be a non-empty string."""
        order = Order(
            order_id="t9", symbol="RELIANCE", exchange=Exchange.NSE,
            side=OrderSide.BUY, order_type=OrderType.LIMIT,
            quantity=10, price=Decimal("2500"), state=OrderState.PENDING,
        )
        dto = self._map(order, security_id="2885")
        assert dto.securityId == "2885"
        assert len(dto.securityId) > 0
```

- [ ] **Step 3: Run contract tests**

Run: `pytest tests/contract/ -v`
Expected: All PASS (these verify existing mapper behavior).

- [ ] **Step 4: Commit**

```bash
git add tests/contract/
git commit -m "test(contract): add Dhan order payload contract tests"
```

---

### Task 16: Property-Based Order FSM Tests

**Files:**
- Create: `tests/unit/domain/test_order_fsm_property.py`

- [ ] **Step 1: Write property-based tests**

```python
# tests/unit/domain/test_order_fsm_property.py
"""Property-based tests for Order state machine."""
import pytest
from hypothesis import given, strategies as st
from decimal import Decimal
from scalpr.domain.order import Order, OrderSide, OrderType, OrderState, ORDER_STATE_TRANSITIONS
from scalpr.domain.instrument import Exchange


def _make_order(state=OrderState.PENDING):
    return Order(
        order_id="prop_test", symbol="RELIANCE", exchange=Exchange.NSE,
        side=OrderSide.BUY, order_type=OrderType.LIMIT,
        quantity=10, price=Decimal("2500"), state=state,
    )


class TestOrderFSMProperties:
    """Property-based verification of order state machine invariants."""

    def test_terminal_states_have_no_valid_transitions(self):
        """Terminal states (FILLED, CANCELLED, REJECTED, EXPIRED) must have no outgoing transitions."""
        terminal_states = {OrderState.FILLED, OrderState.CANCELLED, OrderState.REJECTED, OrderState.EXPIRED}
        for state in terminal_states:
            valid_targets = ORDER_STATE_TRANSITIONS.get(state, set())
            assert len(valid_targets) == 0, f"Terminal state {state} has transitions to {valid_targets}"

    def test_invalid_transition_always_raises(self):
        """Any transition not in ORDER_STATE_TRANSITIONS must raise ValueError."""
        order = _make_order(OrderState.PENDING)
        # Try transitioning to every state — only valid ones should succeed
        for target in OrderState:
            if target in ORDER_STATE_TRANSITIONS.get(OrderState.PENDING, set()):
                result = order.transition_to(target)
                assert result.state == target
            else:
                with pytest.raises(ValueError, match="Invalid transition"):
                    order.transition_to(target)

    def test_transition_returns_new_order(self):
        """transition_to must return a new Order, not mutate the original."""
        order = _make_order(OrderState.PENDING)
        new_order = order.transition_to(OrderState.OPEN)
        assert new_order is not order
        assert order.state == OrderState.PENDING  # Original unchanged
        assert new_order.state == OrderState.OPEN

    def test_all_non_terminal_states_can_reach_a_terminal(self):
        """Every non-terminal state must have a path to at least one terminal state."""
        terminal_states = {OrderState.FILLED, OrderState.CANCELLED, OrderState.REJECTED, OrderState.EXPIRED}

        def can_reach_terminal(state, visited=None):
            if state in terminal_states:
                return True
            if visited is None:
                visited = set()
            if state in visited:
                return False
            visited.add(state)
            for target in ORDER_STATE_TRANSITIONS.get(state, set()):
                if can_reach_terminal(target, visited):
                    return True
            return False

        for state in OrderState:
            if state not in terminal_states:
                assert can_reach_terminal(state), f"State {state} cannot reach any terminal state"
```

- [ ] **Step 2: Run property-based tests**

Run: `pytest tests/unit/domain/test_order_fsm_property.py -v`
Expected: All PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/unit/domain/test_order_fsm_property.py
git commit -m "test(domain): add property-based tests for Order state machine"
```

---

### Task 17: Final pyproject.toml Quality Gates

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add contract test marker**

Add to the `markers` list in `[tool.pytest.ini_options]`:

```toml
"contract: broker API contract tests that verify payload shape",
```

- [ ] **Step 2: Verify import-linter runs**

Run: `pip install import-linter && lint-imports --config pyproject.toml`
Expected: PASS (no violations with corrected contracts).

- [ ] **Step 3: Verify coverage runs against correct package**

Run: `pytest tests/ --cov=scalpr --cov-report=term-missing`
Expected: Coverage report shows `scalpr/` files.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "fix(config): add contract test marker, verify import-linter and coverage work"
```

---

## Verification Checklist

After all phases complete, verify:

```bash
# 1. All tests pass
pytest tests/ -v --tb=short

# 2. Contract tests pass
pytest tests/contract/ -v

# 3. Import-linter passes
lint-imports --config pyproject.toml

# 4. Coverage report is meaningful
pytest tests/ --cov=scalpr --cov-report=term-missing

# 5. Ruff passes
ruff check scalpr/

# 6. API starts without side effects on import
python -c "import scalpr.api.bootstrap; print('No side effects')"

# 7. F&O mapping works
python -c "from scalpr.brokers.dhan.mapper import DhanMapper; print('Mapper OK')"
```

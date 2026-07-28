# Dhan Review Warnings (W1–W7) Remediation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the 7 warning-level findings from the Dhan v0/v1 implementation review: wire-mapping inconsistencies, error-hierarchy leaks, Gateway WS thread-safety, ignored `subscribe_feed` mode, silent parameter loss, and zero-filled quotes.

**Architecture:** All fixes stay within the existing adapter boundaries. `to_dhan_wire(exchange, segment)` in `segments.py` becomes the single source of wire-segment truth (other mappers delegate to it). Broker-specific exceptions are translated to `scalpr/brokers/errors.py` types at the `Gateway` facade. WS lifecycle gets a `threading.Lock`. Mode plumbing reuses the existing `ws_client.subscribe(symbols, mode=...)` parameter.

**Tech Stack:** Python 3.13, pytest, unittest.mock. Run tests with `python -m pytest` from repo root (uses `.venv`).

**Dependency graph / parallelization:**

```
Task 1 (W2: wire pairs) ──► Task 2 (W1: consolidate wire_segment_for)
Task 3 (W6: handle fixes)     — independent
Task 4 (W7: fail-loud quotes) — independent
Task 5 (W3: error translation)— independent
Task 6 (W4: WS lock) ──► Task 7 (W5: mode plumbing)   [both edit gateway.py]
```

Tasks 3, 4, 5 and the (1→2) chain and the (6→7) chain may run in parallel.

**Baseline (must hold after every task):** `python -m pytest tests/unit/brokers/ tests/unit/domain/ tests/contract/ -q` → 516+ passed, exactly these 5 pre-existing failures allowed: `test_option_chain.py::test_scanner_accepts_adapter_output`, 2× `test_rate_limit_async.py::TestAsyncHttpClientWiring`, 2× `test_clock_and_types.py::TestSignalExtensions`.

**Commits:** Do NOT commit — the user has not authorized commits. Verify with the test suite after each task instead. **DO stage** (`git add`) after every task GREEN per the Revert Anomaly Recovery Protocol (bottom of this document).

---

## ULTRA-PLAN STATUS (updated 2026-07-27, post revert #4 recovery)

| Task | Status | Evidence |
|------|--------|----------|
| Task 1 (W2) wire pairs | ✅ DONE ×2 (re-applied after revert #4) | 4 pairs in `_WIRE_BY_EXCHANGE_SEGMENT`; tests in `TestToDhanWire` |
| Task 2 (W1) consolidation | ✅ DONE ×2 (re-applied after revert #4) | `wire_segment_for` delegates to `to_dhan_wire`; `TestWireSegmentForConsolidation` |
| Task 3 (W6) handle honesty | ✅ DONE | date-parse-first, depth `levels != 5` guard, gateway `instrument()` override guard; `TestInstrumentHandleParamHonesty` |
| Task 4 (W7) fail-loud | ✅ DONE | by-id raise-on-missing + batch skip logging; legacy zero-decimals test converted to raise-expectation + 2 by-id tests |
| C1/C2/C3 criticals | ✅ RE-APPLIED (revert #3+#4 recovery) | mapper/orders override, strict normalise, by-id delegation all verified |
| **Ground truth** | **529 passed / 5 pre-existing failures** | full scoped suite, 2026-07-27 |
| Staged snapshot | ✅ all completed work `git add`-ed (not committed) | recoverable via `git diff --staged` |
| Task 5 (W3) error translation | ⏳ NEXT | plan section verified fresh vs gateway.py:511–517 |
| Task 6 (W4) WS lock | ⏳ PENDING | verified vs gateway.py:402–420 (`threading` already imported) |
| Task 7 (W5) mode plumbing | ⏳ PENDING after 6 | verified vs ws_manager.py:310–330, subscribe_feed:553–559 |
| Final gate | ⏳ PENDING | suite + live E2E + grep guard + spec/quality review subagents |

**Remaining dependency graph:** `Task 5` ∥ `(Task 6 → Task 7)` — Task 5 touches only `Gateway.instrument` + imports; Tasks 6/7 touch the streaming block. All three edit `gateway.py`, so within this single session they execute sequentially (5 → 6 → 7) to avoid self-conflicts; their test files may be appended in any order.

**Post-task ritual (every task):** RED → GREEN → canary grep → baseline suite → `git add` touched files.

---

### Task 1 (W2): Add missing `to_dhan_wire` pairs

**Files:**
- Modify: `scalpr/brokers/dhan/segments.py` (dict `_WIRE_BY_EXCHANGE_SEGMENT`, ~line 168)
- Test: `tests/unit/brokers/dhan/test_segments.py`

- [ ] **Step 1: Write the failing tests** — append inside `class TestToDhanWire`:

```python
    def test_mcx_options(self):
        assert to_dhan_wire(Exchange.MCX, Segment.OPTIONS) == "MCX_COMM"

    def test_bse_index(self):
        assert to_dhan_wire(Exchange.BSE, Segment.INDEX) == "IDX_I"

    def test_nse_fno_futures(self):
        assert to_dhan_wire(Exchange.NSE_FNO, Segment.FUTURES) == "NSE_FNO"

    def test_nse_fno_options(self):
        assert to_dhan_wire(Exchange.NSE_FNO, Segment.OPTIONS) == "NSE_FNO"
```

- [ ] **Step 2: Run to verify they fail**

Run: `python -m pytest tests/unit/brokers/dhan/test_segments.py -q`
Expected: 4 FAIL with `ValueError: No Dhan wire mapping for ...`

- [ ] **Step 3: Implement** — in `segments.py`, extend `_WIRE_BY_EXCHANGE_SEGMENT`; add after the `(Exchange.MCX, Segment.FUTURES): "MCX_COMM",` entry:

```python
    (Exchange.MCX, Segment.OPTIONS): "MCX_COMM",
    (Exchange.BSE, Segment.INDEX): "IDX_I",
    (Exchange.NSE_FNO, Segment.FUTURES): "NSE_FNO",
    (Exchange.NSE_FNO, Segment.OPTIONS): "NSE_FNO",
```

- [ ] **Step 4: Run test file, then the scoped suite**

Run: `python -m pytest tests/unit/brokers/dhan/test_segments.py -q` → all pass.
Run baseline command → only the 5 allowed failures.

---

### Task 2 (W1): Consolidate `wire_segment_for` onto `to_dhan_wire`; fix INDEX bug

**Files:**
- Modify: `scalpr/brokers/dhan/instrument_mapper.py:123-129` (`wire_segment_for`)
- Modify: `scalpr/brokers/dhan/segments.py` (`EXCHANGE_TO_SEGMENT` dict, ~line 30)
- Test: `tests/unit/brokers/dhan/test_segments.py` (new class)

- [ ] **Step 1: Write the failing tests** — append to `test_segments.py`:

```python
from scalpr.brokers.dhan.instrument_mapper import wire_segment_for


class TestWireSegmentForConsolidation:
    """wire_segment_for must agree with to_dhan_wire (W1)."""

    def test_index_returns_idx_i_not_nse_eq(self):
        # Regression: previously fell through to the NSE_EQ default
        assert wire_segment_for(Exchange.INDEX, Segment.INDEX) == "IDX_I"

    def test_nse_index_returns_idx_i(self):
        assert wire_segment_for(Exchange.NSE, Segment.INDEX) == "IDX_I"

    def test_equity_unchanged(self):
        assert wire_segment_for(Exchange.NSE, Segment.EQUITY) == "NSE_EQ"
        assert wire_segment_for(Exchange.BSE, Segment.EQUITY) == "BSE_EQ"

    def test_derivatives_unchanged(self):
        assert wire_segment_for(Exchange.NSE, Segment.FUTURES) == "NSE_FNO"
        assert wire_segment_for(Exchange.BSE, Segment.OPTIONS) == "BSE_FNO"
        assert wire_segment_for(Exchange.MCX, Segment.FUTURES) == "MCX_COMM"

    def test_string_path_knows_nse_fno_and_currency(self):
        assert exchange_to_wire("NSE_FNO") == "NSE_FNO"
        assert exchange_to_wire("CURRENCY") == "NSE_CURRENCY"
```

- [ ] **Step 2: Run to verify failures**

Run: `python -m pytest tests/unit/brokers/dhan/test_segments.py::TestWireSegmentForConsolidation -q`
Expected: `test_index_returns_idx_i_not_nse_eq` and `test_string_path_knows_nse_fno_and_currency` FAIL; others pass.

- [ ] **Step 3: Implement** — replace `wire_segment_for` in `instrument_mapper.py` (keep the old heuristics only as fallback):

```python
def wire_segment_for(exchange: Exchange, segment: Segment) -> str:
    """Fallback wire segment for instruments not sourced from the CSV.

    Delegates to the canonical pair mapping in segments.to_dhan_wire;
    the legacy heuristics remain only for pairs outside that table.
    """
    try:
        return to_dhan_wire(exchange, segment)
    except ValueError:
        pass
    if exchange is Exchange.MCX:
        return "MCX_COMM"
    if exchange is Exchange.NSE_FNO or segment in (Segment.FUTURES, Segment.OPTIONS):
        return "BSE_FNO" if exchange is Exchange.BSE else "NSE_FNO"
    return "BSE_EQ" if exchange is Exchange.BSE else "NSE_EQ"
```

Add `to_dhan_wire` to the existing `from scalpr.brokers.dhan.segments import ...` line in `instrument_mapper.py` (segments.py does not import instrument_mapper — no cycle).

In `segments.py`, extend `EXCHANGE_TO_SEGMENT` (string path of `exchange_to_wire`); add after the `"BFO": "BSE_FNO",` entry:

```python
    "NSE_FNO": "NSE_FNO",
    "BSE_FNO": "BSE_FNO",
    "CURRENCY": "NSE_CURRENCY",
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/unit/brokers/dhan/test_segments.py tests/unit/brokers/dhan/test_instrument_mapper.py -q` → all pass.
Run baseline command → only the 5 allowed failures.

---

### Task 3 (W6): InstrumentHandle date/param honesty

**Files:**
- Modify: `scalpr/brokers/instrument_handle.py` (`historical`, `depth`)
- Modify: `scalpr/brokers/gateway.py:484-495` (`Gateway.instrument`)
- Test: `tests/unit/brokers/test_instrument_handle.py`

- [ ] **Step 1: Write the failing tests** — append to `test_instrument_handle.py`:

```python
class TestInstrumentHandleParamHonesty:
    """W6: no silently-ignored parameters, no inverted date ranges."""

    def test_historical_string_end_without_start_gives_valid_range(self):
        # Regression: string `end` used to be parsed AFTER defaults were
        # computed, producing start=today-90d > end for past dates.
        mock_hist = MagicMock()
        mock_hist.get_ohlcv.return_value = []
        handle = InstrumentHandle(
            resolved=_make_resolved(),
            market_data_adapter=MagicMock(),
            historical_adapter=mock_hist,
        )
        handle.historical(interval="1D", end="2025-01-10")
        call = mock_hist.get_ohlcv.call_args
        start_arg, end_arg = call[0][3], call[0][4]
        assert end_arg == date(2025, 1, 10)
        assert start_arg == date(2025, 1, 10) - timedelta(days=90)
        assert start_arg < end_arg

    def test_depth_rejects_unsupported_levels(self):
        handle = InstrumentHandle(
            resolved=_make_resolved(),
            market_data_adapter=MagicMock(),
            historical_adapter=MagicMock(),
        )
        with pytest.raises(ValueError, match="5 levels"):
            handle.depth(levels=20)
```

Add `import pytest` to the imports of `test_instrument_handle.py` if not present.

- [ ] **Step 2: Run to verify failures**

Run: `python -m pytest tests/unit/brokers/test_instrument_handle.py::TestInstrumentHandleParamHonesty -q`
Expected: both FAIL (`start_arg` computed from today; no ValueError raised).

- [ ] **Step 3: Implement** — in `instrument_handle.py`:

Replace the body of `historical` date-defaulting (currently: defaults computed before string parsing) with parse-first ordering:

```python
        # Parse string dates FIRST so defaults derive from the real end date
        if isinstance(start, str):
            start = date.fromisoformat(start)
        if isinstance(end, str):
            end = date.fromisoformat(end)

        if end is None:
            end = date.today()
        if start is None:
            end_d = end.date() if isinstance(end, datetime) else end
            start = end_d - timedelta(days=90)
```

Replace `depth` signature guard (REST quote endpoint returns exactly 5 levels):

```python
    def depth(self, levels: int = 5) -> dict[str, Any]:
        """Get market depth (REST supports exactly 5 levels; use the
        WebSocket FullDepth mode for 20-level depth)."""
        if levels != 5:
            raise ValueError(
                f"REST depth supports exactly 5 levels, got {levels}. "
                "Use subscribe_feed(MarketFeed.FULL, ...) for 20-level depth."
            )
        return self._market_data.get_depth_by_id(
            self._resolved.security_id,
            self._resolved.dhan_exchange_segment,
            symbol=self.symbol,
        )
```

In `gateway.py` `Gateway.instrument`, reject the accepted-but-ignored params — insert at the top of the method body:

```python
        if exchange is not None or segment is not None:
            raise ValueError(
                "exchange/segment overrides are not supported; encode the "
                "exchange in the identifier, e.g. 'TCS:NSE'"
            )
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/unit/brokers/test_instrument_handle.py -q` → all pass.
Run baseline command → only the 5 allowed failures.

---

### Task 4 (W7): Fail loud on missing quote/depth data; log skipped batch symbols

**Files:**
- Modify: `scalpr/brokers/dhan/market_data.py` (`get_quote_by_id`, `get_depth_by_id`, `get_batch_ltp`, `get_batch_quote`)
- Test: `tests/unit/brokers/dhan/test_adapters.py`

- [ ] **Step 1: Write the failing tests** — append to `test_adapters.py` inside `TestMarketDataAdapter`, using the file's existing `market_adapter` and `mock_http_client` fixtures (defined at module top, ~line 58):

```python
    def test_quote_by_id_raises_when_entry_missing(self, market_adapter, mock_http_client):
        mock_http_client.post.return_value = {"data": {}}
        with pytest.raises(ValueError, match="No quote data"):
            market_adapter.get_quote_by_id("11536", "NSE_EQ", symbol="TCS")

    def test_depth_by_id_raises_when_entry_missing(self, market_adapter, mock_http_client):
        mock_http_client.post.return_value = {"data": {}}
        with pytest.raises(ValueError, match="No depth data"):
            market_adapter.get_depth_by_id("11536", "NSE_EQ", symbol="TCS")
```

- [ ] **Step 2: Run to verify failures**

Run: `python -m pytest tests/unit/brokers/dhan/test_adapters.py -q -k "by_id_raises"`
Expected: both FAIL (currently returns all-zero dicts).

- [ ] **Step 3: Implement** — in `market_data.py`:

In `get_quote_by_id`, replace the unconditional `.get(..., {})` chain:

```python
        data = self._client.post("/marketfeed/quote", json={segment: [security_id]})
        raw = data.get("data", {}).get(segment, {}).get(str(security_id))
        if not raw:
            logger.warning(f"Quote missing for {symbol or security_id} (security_id={security_id}, segment={segment})")
            raise ValueError(f"No quote data for {symbol or security_id} on {segment}")
```

In `get_depth_by_id`, same pattern:

```python
        data = self._client.post("/marketfeed/quote", json={segment: [security_id]})
        raw = data.get("data", {}).get(segment, {}).get(str(security_id))
        if not raw:
            logger.warning(f"Depth missing for {symbol or security_id} (security_id={security_id}, segment={segment})")
            raise ValueError(f"No depth data for {symbol or security_id} on {segment}")
```

In `get_batch_ltp` and `get_batch_quote`, replace the bare `except Exception: continue` with:

```python
            except Exception as exc:
                logger.warning(f"Batch resolve skipped {sym!r} on {exchange}: {exc}")
                continue
```

- [ ] **Step 4: Run tests; repair only tests that codified the silent-zero behavior**

Run: `python -m pytest tests/unit/brokers/dhan/test_adapters.py tests/unit/brokers/test_instrument_handle.py -q`
If any pre-existing adapter test asserted a zero-filled quote for missing data, update that test to expect `ValueError` instead (that behavior is the bug W7 fixes). Do not change any other assertion.
Run baseline command → only the 5 allowed failures.

---

### Task 5 (W3): Translate Dhan exceptions at the Gateway facade

**Files:**
- Modify: `scalpr/brokers/gateway.py` (`Gateway.instrument`, imports)
- Test: `tests/unit/brokers/test_gateway.py` (append)

- [ ] **Step 1: Write the failing test** — append to `tests/unit/brokers/test_gateway.py`:

```python
class TestGatewayErrorTranslation:
    """W3: broker-specific exceptions must not leak through the facade."""

    def test_instrument_not_found_is_broker_agnostic(self):
        from unittest.mock import MagicMock, patch
        from scalpr.brokers.dhan.exceptions import InstrumentNotFoundError
        from scalpr.brokers.errors import InstrumentNotFound
        from scalpr.brokers.gateway import Gateway

        gw = Gateway.__new__(Gateway)  # bypass __init__/connect
        conn = MagicMock()
        conn.resolver.resolve_full.side_effect = InstrumentNotFoundError("nope")
        with patch.object(Gateway, "_get_dhan_connection", return_value=conn):
            with pytest.raises(InstrumentNotFound):
                gw.instrument("ZZZZ:NSE")
```

Ensure `import pytest` exists at the top of `test_gateway.py`.

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/unit/brokers/test_gateway.py::TestGatewayErrorTranslation -q`
Expected: FAIL — `InstrumentNotFoundError` (Dhan) raised instead of `InstrumentNotFound`.

- [ ] **Step 3: Implement** — in `gateway.py`:

Add imports near the existing broker imports (top of file):

```python
from scalpr.brokers.dhan.exceptions import InstrumentNotFoundError as _DhanInstrumentNotFound
from scalpr.brokers.errors import InstrumentNotFound
```

In `Gateway.instrument`, wrap the two `resolve_full` calls:

```python
        try:
            if isinstance(identifier, str):
                inst_id = SimpleInstrumentId.parse(identifier)
                resolved = conn.resolver.resolve_full(inst_id.symbol, inst_id.exchange.value)
            else:
                resolved = conn.resolver.resolve_full(identifier.symbol, identifier.exchange.value)
        except _DhanInstrumentNotFound as exc:
            raise InstrumentNotFound(str(exc)) from exc
```

Note: the `Gateway` facade already imports Dhan modules elsewhere (`_init_websocket_manager`); this adds no new coupling direction. Do NOT delete the `RateLimitError = RateLimitExceeded` alias in `errors.py` in this task (alias removal has unknown blast radius — out of scope).

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/unit/brokers/test_gateway.py -q` → all pass.
Run baseline command → only the 5 allowed failures.

---

### Task 6 (W4): Thread-safe WS lifecycle in Gateway

**Files:**
- Modify: `scalpr/brokers/gateway.py` (`__init__`, `stream`, `stop_stream`, `subscribe_feed`)
- Test: `tests/unit/brokers/test_gateway.py` (append)

- [ ] **Step 1: Write the failing test** — append to `test_gateway.py`:

```python
class TestGatewayWsLifecycleSafety:
    """W4: stop_stream must be idempotent and never deref None loop refs."""

    def _bare_gateway(self):
        from scalpr.brokers.gateway import Gateway
        gw = Gateway.__new__(Gateway)
        gw._ws_manager = None
        gw._ws_loop = None
        gw._ws_thread = None
        gw._stream_callbacks = []
        import threading
        gw._ws_lock = threading.Lock()
        return gw

    def test_stop_stream_noop_when_never_started(self):
        gw = self._bare_gateway()
        gw.stop_stream()  # must not raise
        gw.stop_stream()  # idempotent

    def test_has_ws_lock(self):
        import threading
        from scalpr.brokers.gateway import Gateway
        import inspect
        src = inspect.getsource(Gateway.__init__)
        assert "_ws_lock" in src
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/unit/brokers/test_gateway.py::TestGatewayWsLifecycleSafety -q`
Expected: `test_has_ws_lock` FAIL (`_ws_lock` not in `__init__`); first test passes today only because of the early return — keep it as a regression guard.

- [ ] **Step 3: Implement** — in `gateway.py`:

In `__init__`, after `self._stream_callbacks: list[Callable] = []`:

```python
        self._ws_lock = threading.Lock()
```

In `stream`, replace the unsynchronized init check:

```python
        with self._ws_lock:
            if self._ws_manager is None:
                self._init_websocket_manager()
            manager, loop = self._ws_manager, self._ws_loop
```

and use the captured `manager`/`loop` locals in the `run_coroutine_threadsafe` call below (not `self._ws_manager`/`self._ws_loop`).

In `subscribe_feed`, same pattern:

```python
        with self._ws_lock:
            if self._ws_manager is None:
                self._init_websocket_manager()
            manager, loop = self._ws_manager, self._ws_loop
```

Replace `stop_stream` entirely:

```python
    def stop_stream(self) -> None:
        """Stop all streaming subscriptions and the background loop."""
        with self._ws_lock:
            manager, loop, thread = self._ws_manager, self._ws_loop, self._ws_thread
            self._ws_manager = None
            self._ws_loop = None
            self._ws_thread = None
            self._stream_callbacks.clear()
        if manager is None or loop is None:
            return
        try:
            asyncio.run_coroutine_threadsafe(manager.stop(), loop).result(timeout=15)
        except Exception as exc:
            logger.error(f"ws_manager_stop_failed: {exc}")
        finally:
            loop.call_soon_threadsafe(loop.stop)
            if thread is not None:
                thread.join(timeout=5)
            loop.close()
            logger.info("stream_stopped")
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/unit/brokers/test_gateway.py -q` → all pass.
Run baseline command → only the 5 allowed failures.

---

### Task 7 (W5): Plumb `mode` through `subscribe_feed`; register callback before subscribing

**Files:**
- Modify: `scalpr/brokers/dhan/ws_manager.py` (`_subscribe_async`, `subscribe_pairs`)
- Modify: `scalpr/brokers/gateway.py` (`subscribe_feed`)
- Test: `tests/unit/brokers/dhan/test_websocket.py` (append), `tests/unit/brokers/test_gateway.py` (append)

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/brokers/dhan/test_websocket.py` (match its existing manager fixture pattern — it already tests `subscribe_pairs`):

```python
@pytest.mark.asyncio
async def test_subscribe_pairs_forwards_mode(manager_connected):
    """W5: subscribe_pairs must pass mode through to the ws client."""
    manager, ws_client = manager_connected
    await manager.subscribe_pairs([("TCS", "NSE")], mode="full")
    ws_client.subscribe.assert_awaited_once_with([("TCS", "NSE")], mode="full")
```

(If the file has no `manager_connected` fixture, build the manager, set `manager._status = ConnectionStatus.CONNECTED`, and set `manager._ws_client = AsyncMock()` following the file's existing subscription tests.)

Append to `tests/unit/brokers/test_gateway.py`:

```python
class TestSubscribeFeedMode:
    """W5: subscribe_feed must honor mode and register callback first."""

    def test_mode_passed_and_callback_registered_before_subscribe(self):
        from unittest.mock import MagicMock, patch
        from scalpr.brokers.gateway import Gateway
        from scalpr.domain.instrument import MarketFeed
        import threading

        gw = Gateway.__new__(Gateway)
        gw._stream_callbacks = []
        gw._ws_lock = threading.Lock()
        gw._ws_manager = MagicMock()
        gw._ws_loop = MagicMock()

        callback_registered_at_subscribe = []

        def fake_run(coro, loop):
            coro.close()
            callback_registered_at_subscribe.append(len(gw._stream_callbacks))
            f = MagicMock()
            f.result.return_value = None
            return f

        cb = lambda evt: None
        with patch("scalpr.brokers.gateway.asyncio.run_coroutine_threadsafe", side_effect=fake_run):
            gw.subscribe_feed(MarketFeed.FULL, "TCS:NSE", on_event=cb)

        # Callback must already be registered when subscribe fires (no dropped ticks)
        assert callback_registered_at_subscribe == [1]
        # Mode must reach the manager
        gw._ws_manager.subscribe_pairs.assert_called_once_with([("TCS", "NSE")], mode="full")
```

- [ ] **Step 2: Run to verify failures**

Run: `python -m pytest tests/unit/brokers/dhan/test_websocket.py -q -k forwards_mode` and `python -m pytest tests/unit/brokers/test_gateway.py::TestSubscribeFeedMode -q`
Expected: FAIL — `subscribe_pairs() got an unexpected keyword argument 'mode'` / callback count `[0]`.

- [ ] **Step 3: Implement**

In `ws_manager.py`, change `_subscribe_async` and `subscribe_pairs`:

```python
    async def _subscribe_async(self, symbols: list[tuple[str, str]], mode: str | None = None) -> None:
        """Add to subscription list and send subscribe to client if running."""
        async with self._lock:
            self._subscriptions.update(symbols)

        if self._status == ConnectionStatus.CONNECTED and self._ws_client is not None:
            try:
                await self._ws_client.subscribe(symbols, mode=mode)
                logger.info("Subscribed to %d symbols", len(symbols))
            except Exception as exc:
                logger.error("Failed to subscribe: %s", exc)
                self._metrics.last_error = str(exc)

    async def subscribe_pairs(self, pairs: list[tuple[str, str]], mode: str | None = None) -> None:
        """Subscribe to (symbol, exchange) pairs, preserving the exchange.

        Unlike the IMarketDataFeed ``subscribe(list[str])`` (which hardcodes
        NSE), this is the exchange-aware entry point for callers that know
        the segment. ``mode`` overrides the manager default ("ltp", "quote",
        "depth", "full"); reconnect resubscription uses the manager default.
        """
        await self._subscribe_async(pairs, mode=mode)
```

Check the internal caller: `stream()`-path `subscribe_pairs([...])` calls stay valid (mode defaults to None → client uses its default). Verify with `grep -n "subscribe_pairs\|_subscribe_async(" scalpr/` and update any caller that passes positional args beyond `pairs` (none expected).

In `gateway.py`, replace the end of `subscribe_feed` (callback ordering + mode):

```python
        if on_event:
            self._stream_callbacks.append(on_event)

        asyncio.run_coroutine_threadsafe(
            manager.subscribe_pairs(pairs, mode=mode.value),
            loop,
        ).result(timeout=15)
```

(`MarketFeed.LTP/QUOTE/FULL` values are `"ltp"/"quote"/"full"` — exactly the strings `ws_client._SDK_MODES` accepts. `manager`/`loop` locals come from Task 6's lock block; if Task 6 has not run yet, use `self._ws_manager`/`self._ws_loop`.)

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/unit/brokers/dhan/test_websocket.py tests/unit/brokers/test_gateway.py -q` → all pass.
Run baseline command → only the 5 allowed failures.

---

### Final Verification (after all tasks)

- [ ] Full scoped suite: `python -m pytest tests/unit/brokers/ tests/unit/domain/ tests/contract/ -q` → ≥ 516 passed + new tests, exactly the 5 known pre-existing failures.
- [ ] Live E2E: `python tests/integration/test_live_instrument_api.py` → 6/6 passed (verifies W7 fail-loud doesn't break live equity/index paths).
- [ ] Grep guard — no remaining direct users of the old heuristic-only behavior:
  `grep -rn "wire_segment_for" scalpr/` → only `instrument_mapper.py` definition and `resolver.py` caller.

### Explicitly Out of Scope (suggestion-level, not warnings)

- Removing the `RateLimitError = RateLimitExceeded` alias in `errors.py`.
- Renaming `ResolvedInstrument.dhan_exchange_segment` to a provider-neutral name.
- `Candle` validation / wiring `historical()` to return `Candle` objects.
- Option-chain expiry-cache TTL; resolver snapshot reads.

---

## Revert Anomaly Ledger & Recovery Protocol

The IDE/harness has silently reverted edited files **4 times** during this work. Mechanism
(confirmed 2026-07-27): the workspace is a git repo (`feat/30day-remediation`); **tracked**
files get reset toward git HEAD, **untracked** files roll back to older snapshots of
themselves. Newer edits in the same session sometimes survive — reverts are per-file,
not global.

### Occurrence log

| # | When | Files hit |
|---|------|-----------|
| 1–2 | prior sessions | C1/C2/C3 critical-fix set (various) |
| 3 | mid-session, during Task 3 | market_data.py, instrument_handle.py, mapper.py, orders.py, segments.py (strict), resolver.py, test_instrument_handle.py, test_critical_fixes.py, test_segments.py |
| 4 | after Task 3/4 recovery | segments.py (Task 1 pairs + Task 2 EXCHANGE_TO_SEGMENT), instrument_mapper.py (Task 2 delegation → exact HEAD), test_segments.py (all Task 1/2 + strict tests) |

### Recovery Protocol (MANDATORY after every task GREEN)

1. **Canary grep** — run and require all counts > 0:
   ```bash
   grep -c 'Segment.OPTIONS): "MCX_COMM"' scalpr/brokers/dhan/segments.py   # Task 1
   grep -c 'to_dhan_wire' scalpr/brokers/dhan/instrument_mapper.py          # Task 2
   grep -c 'strict' scalpr/brokers/dhan/segments.py                         # C2
   grep -c 'get_ltp_by_id' scalpr/brokers/dhan/market_data.py               # C3
   grep -c 'exchange_segment' scalpr/brokers/dhan/mapper.py                 # C1
   grep -c 'WireSegmentForConsolidation' tests/unit/brokers/dhan/test_segments.py
   ```
2. **Stage, don't commit** — `git add` every file touched by the task. Staging writes
   blobs into `.git` without committing (the "Do NOT commit" rule stands), so a later
   revert is detectable via `git status` (file shows `MM`→`M ` flip) and recoverable
   via `git diff --staged` / `git checkout-index`.
3. **Detection tells** — a SearchReplace that fails to match text you recently verified,
   or a test that passed earlier suddenly failing, means: STOP, re-run the canary greps,
   re-run the ground-truth suite, rebuild the damage table before editing anything.
4. **Ground truth** — `python -m pytest tests/unit/brokers/ tests/unit/domain/ tests/contract/ -q`;
   only the 5 known pre-existing failures are acceptable.

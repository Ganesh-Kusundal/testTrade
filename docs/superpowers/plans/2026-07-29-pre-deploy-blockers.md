# Pre-Deployment Blocker Resolution Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve the 3 NO-GO blockers (K-033, K-034, K-035) and 5 cleanup items (K-036–K-040) blocking deployment.

**Architecture:** Wave 1 dispatches 4 parallel agents (independent files). Wave 2 is sequential on `http_client.py` (3 tasks touching same file). Wave 3 adds tests after fix.

**Tech Stack:** Python 3.13, pytest, aiohttp

## Global Constraints

- **1007/1007 existing tests must remain passing**
- Stage only (`git add`), never commit unless explicitly asked
- K-033 is P0 — data corruption risk. Must be verified with test.

---

## Dependency Map

```
Wave 1 (parallel)        Wave 2 (sequential)      Wave 3
─────────────────────     ────────────────────     ──────────
K-033 order_manager  →                            K-040 tests
K-035 ws_manager/ws_client
K-036 _token_lifecycle
K-037 gateway.py
                         K-034 rename CB     (http_client.py)
                         K-038 remove wrappers (http_client.py)
                         K-039 merge helpers   (http_client.py + auth)
```

All files in Wave 1 are independent. K-034/038/039 all edit `http_client.py` — must be sequential to avoid merge conflicts.

---

## Wave 1: 4 Parallel Agents

### Task 1.1: K-033 — Fix _append_event ordering (P0)

**Files:**
- Modify: `scalpr/execution/order_manager.py`

**Problem:** All 3 callers (`add_order`, `update_order_state`, `process_fill`) call `_append_event` AFTER mutating OMS state. If append raises, state is corrupted with no rollback.

**Fix:** In each caller, move `_append_event` BEFORE the state mutation (before `OmsRepository.save()`).

**Current pattern (WRONG):**
```python
self._oms.save(order)          # state mutated FIRST
self._append_event(event)      # if this raises → corrupted
```

**Target pattern (CORRECT):**
```python
self._append_event(event)      # append FIRST
self._oms.save(order)          # then mutate state
```

**Do for all 3 callers: `add_order`, `update_order_state`, `process_fill`.**

Run:
```bash
pytest tests/unit/execution/ tests/unit/oms/ -q --tb=short
```

**Report to:** `.superpowers/sdd/p1-k033-report.md`

---

### Task 1.2: K-035 — Remove dead token_refresh_fn (P2)

**Files:**
- Modify: `scalpr/brokers/dhan/ws_manager.py:114,124,681`
- Modify: `scalpr/brokers/dhan/ws_client.py` (search for token_refresh_fn)
- Modify: `scalpr/brokers/gateway/_streaming.py:231`
- Check: `scalpr/api/bootstrap.py:165` (still passes the fn)

**Problem:** `token_refresh_fn` parameter is accepted by `ws_manager.py`, stored, passed to `ws_client.py` — but `ws_client.py` was simplified during K-021 auth refactor and no longer uses it. It's dead code end-to-end.

**Fix:**
1. Remove `token_refresh_fn` from `DhanWebSocketManager.__init__()` and `self._token_refresh_fn` storage
2. Remove `token_refresh_fn` from `DhanWebSocketClient` (search for all occurrences)
3. Remove `token_refresh_fn=self._token_refresh_fn` pass-through at ws_manager.py line 681
4. Update `_streaming.py:231` to not pass `token_refresh_fn`
5. Keep `ensure_fresh_token` lambda in `bootstrap.py:165` if it's used elsewhere (check — it's passed to `DhanWebSocketManager` which no longer needs it)

Run:
```bash
pytest tests/unit/brokers/dhan/test_websocket.py tests/unit/brokers/dhan/test_ws_subscribe_honest.py -q --tb=short
```

**Report to:** `.superpowers/sdd/p1-k035-report.md`

---

### Task 1.3: K-036 — Delete dead TokenRefreshScheduler (P3)

**Files:**
- Modify: `scalpr/brokers/dhan/_token_lifecycle.py:73-143`
- Check: any remaining imports in production code

**Problem:** `TokenRefreshScheduler` class was removed from `connection.py` (K-025/K-030) but the class definition survives in `_token_lifecycle.py`. Only its test file (`test_token_scheduler.py`) references it.

**Fix:**
1. Delete `TokenRefreshScheduler` class (lines 73-143)
2. Keep `TokenBroadcast` class (used by `auth.py`)
3. Remove `TokenRefreshScheduler` from `_token_lifecycle.py` imports if re-exported
4. Delete `tests/unit/brokers/dhan/test_token_scheduler.py`

Run:
```bash
pytest tests/unit/brokers/dhan/ -q --tb=short
```

**Report to:** `.superpowers/sdd/p1-k036-report.md`

---

### Task 1.4: K-037 — Delete dead DhanGateway.adapters() (P3)

**Files:**
- Modify: `scalpr/brokers/dhan/gateway.py:396-407`
- Check: `scalpr/brokers/gateway/facade.py` no longer calls `.adapters()`

**Problem:** `adapters()` method returns dict of connection/resolver/http_client. `facade.py` now uses `self._gateway.connection` directly. No production caller.

**Fix:**
1. Remove `adapters()` method from `DhanGateway` class (lines 396-407)
2. Check no test references it — if they do, remove those too

Run:
```bash
pytest tests/unit/brokers/dhan/test_gateway_connection.py -q --tb=short
```

**Report to:** `.superpowers/sdd/p1-k037-report.md`

---

## Wave 2: Sequential on http_client.py

### Task 2.1: K-034 — Rename CircuitBreaker → HttpCircuitBreaker

**Files:**
- Modify: `scalpr/brokers/dhan/http_client.py:40`
- Modify: `scalpr/brokers/dhan/connection.py:21` (import)
- Check: all references

**Fix:**
1. Rename class `CircuitBreaker` → `HttpCircuitBreaker` in `http_client.py`
2. Update import in `connection.py` line 21
3. Update any test imports

Run:
```bash
pytest tests/unit/brokers/dhan/ -q --tb=short
```

**Report to:** `.superpowers/sdd/p2-k034-report.md`

---

### Task 2.2: K-038 — Remove _bucket_for/_backoff_delay wrappers

**Files:**
- Modify: `scalpr/brokers/dhan/http_client.py:148-151,252-255`

**Fix:**
1. Remove `_bucket_for()` static method
2. Remove `_backoff_delay()` static method
3. Update `_request()` to call `bucket_for()` and `backoff_delay()` directly from `_http_common`

Run:
```bash
pytest tests/unit/brokers/dhan/ -q --tb=short
```

**Report to:** `.superpowers/sdd/p2-k038-report.md`

---

### Task 2.3: K-039 — Merge _http_common into http_client, TokenBroadcast into auth

**Files:**
- Delete: `scalpr/brokers/dhan/_http_common.py` (83 lines)
- Modify: `scalpr/brokers/dhan/http_client.py` — inline contents
- Modify: `scalpr/brokers/dhan/auth.py` — inline `TokenBroadcast` class
- Delete: `scalpr/brokers/dhan/_token_lifecycle.py` (after moving TokenBroadcast)

**Fix:**
1. Move `_http_common.py` constants and helpers into `http_client.py`
2. Delete `_http_common.py`
3. Move `TokenBroadcast` class into `auth.py`
4. Delete `_token_lifecycle.py`
5. Remove any test imports of deleted modules

**Important:** This merges, not copies. Delete the old files after merging.

Run:
```bash
pytest tests/unit/brokers/dhan/ -q --tb=short
```

**Report to:** `.superpowers/sdd/p2-k039-report.md`

---

## Wave 3: Tests

### Task 3.1: K-040 — Add pre-mutation atomicity + broadcast isolation tests

**Files:**
- Modify: `tests/unit/oms/test_event_store_wiring.py` — add pre-mutation test
- Modify: `tests/unit/brokers/dhan/test_token_broadcast.py` — add isolation test

**Test 1: Pre-mutation ordering**
```python
def test_append_failure_does_not_mutate_state(mock_event_store):
    """If EventStore.append() raises, OMS state must remain unchanged."""
    mock_event_store.append.side_effect = EventStoreError("storage full")
    # Attempt to process a fill
    with pytest.raises(EventStoreError):
        order_manager.process_fill(order, fill)
    # OMS state must NOT have been mutated
    assert order_manager.get_order(order.order_id) is None
```

**Test 2: Broadcast receiver isolation**
```python
def test_broadcast_receiver_crash_does_not_block_others():
    broadcast = TokenBroadcast()
    received = []
    def crashing(_):
        raise RuntimeError("boom")
    def normal(tok):
        received.append(tok)
    broadcast.register(crashing)
    broadcast.register(normal)
    count = broadcast.broadcast("new-token")
    assert count == 1  # one delivered despite crash
    assert received == ["new-token"]
```

Run:
```bash
pytest tests/unit/oms/test_event_store_wiring.py tests/unit/brokers/dhan/test_token_broadcast.py -v --tb=short
```

**Report to:** `.superpowers/sdd/p3-k040-report.md`

---

## Execution Order

```
Wave 1 (parallel) │ Wave 2 (sequential)   │ Wave 3
───────────────────┼───────────────────────┼─────────────────
K-033   order_mgr │ K-034  rename CB      │ K-040  add tests
K-035   ws_deadfn │ K-038  remove helpers │
K-036   del sched │ K-039  merge modules  │
K-037   del adapt │                      │
                   │                      │
4 PARALLEL        │ 3 SEQUENTIAL         │ 1 task
                   │ (same file)          │ (depends on K-033)
```

**After each wave:** run `pytest tests/unit/ -q --tb=short` to validate no regressions.

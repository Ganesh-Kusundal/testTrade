# Pre-Deployment System Review

## 1. System Intent

SCALPR is a single-broker (Dhan) algorithmic trading platform. It receives market data via WebSocket, evaluates a single strategy (`ScalprAmtStrategy`), routes orders through risk gates + circuit breaker + OMS persistence, and exposes a FastAPI + CLI interface. The gateway facade wraps Dhan-specific adapters behind broker-agnostic port interfaces.

---

## 2. Active Execution Paths

### Path A: Live Trading (API + WebSocket)
```
main.py → bootstrap.create_app()
  → _lifespan → _start_trading()
    → wire(gateway, watchlist)    # builds RiskGate → CB → OMS → Router → Executor
    → DhanWebSocketManager.start()  # live tick feed
    → feed.add_subscriber(executor.on_tick)
    → executor.on_tick(tick) per symbol
      → ScalprAmtStrategy.on_tick()
        → OrderRouter.place_order()
          → PreTradeRiskGate.check_order()
          → CircuitBreaker.check_limits()
          → OrderManager.add_order()
            → OmsRepository.persist()
            → EventStore.append()
          → DhanGateway.place_order()
            → DhanConnection.orders.place_order()
```

### Path B: REST API (no trading)
```
main.py → bootstrap.create_app()
  → routers/{health,market_data,orders,portfolio,replay}
    → gateway.get_ltp / get_quote / get_ohlcv
    → connection.market_data / connection.historical
```

### Path C: CLI
```
cli/main.py → commands/{broker,quote,orders,positions,funds,holdings,trades,history,stream}
  → Gateway() (facade)
    → gateway.ltp / gateway.quote / gateway.positions / etc
```

---

## 3. Dead / Duplicate / Legacy Code (DELETE list)

### DELETE 1: `TokenRefreshScheduler` class
- **File:** `scalpr/brokers/dhan/_token_lifecycle.py:73-143`
- **Status:** Dead code. Removed from `connection.py` (K-025/K-030) but class and its test file survive.
- **Action:** Remove class definition. Keep `TokenBroadcast` (used by auth.py).

### DELETE 2: `DhanGateway.adapters()` method
- **File:** `scalpr/brokers/dhan/gateway.py:396-407`
- **Status:** Dead code. `facade.py` uses `self._gateway.connection` directly. No production caller.
- **Action:** Remove method.

### DELETE 3: `DhanHttpClient._bucket_for()` static wrapper
- **File:** `scalpr/brokers/dhan/http_client.py:148-151`
- **Status:** Unnecessary delegation. `_request()` calls `self._bucket_for(endpoint)` which calls `bucket_for(endpoint)` from `_http_common.py`. Just call `bucket_for()` directly.
- **Action:** Inline `_bucket_for` → use `bucket_for` directly in `_request()`.

### DELETE 4: `DhanHttpClient._backoff_delay()` static wrapper
- **File:** `scalpr/brokers/dhan/http_client.py:252-255`
- **Status:** Same pattern as #3. Unnecessary delegation.
- **Action:** Remove method.

### DELETE 5: `token_refresh_fn` param in `DhanWebSocketManager`
- **File:** `scalpr/brokers/dhan/ws_manager.py:114,124,681`
- **Status:** Dead parameter. `DhanWebSocketClient` was simplified to not use it during K-021/K-030 auth refactor. Checked in `ws_client.py`.
- **Action:** Remove `token_refresh_fn` from `__init__`, `__init__` call, and internal usage. Remove from `_streaming.py:231` which passes it.

### DELETE 6: `token_refresh_fn` in `DhanWebSocketClient`
- **File:** `scalpr/brokers/dhan/ws_client.py` (verify)
- **Status:** Likely dead after auth refactor.
- **Action:** Verify and remove.

### MERGE 1: Two `CircuitBreaker` implementations
- **File 1:** `scalpr/risk/circuit_breaker.py:11` — Financial risk (daily loss, drawdown, halt)
- **File 2:** `scalpr/brokers/dhan/http_client.py:40` — HTTP fault isolation (failure threshold, recovery timeout)
- **Status:** Different domains, same name. Not true duplication — they solve different problems. But naming conflict is confusing.
- **Action:** Rename `http_client.CircuitBreaker` → `HttpCircuitBreaker` to disambiguate.

---

## 4. Shotgun Surgery Findings

### SS-1: `Gateway._init_websocket_manager()` duplicates `_start_trading()` flow
- **Files:** `scalpr/brokers/gateway/_streaming.py:196-239` and `scalpr/api/bootstrap.py:144-183`
- **Problem:** Both create a `DhanWebSocketManager`, subscribe pairs, register callbacks. The streaming mixin does it via `BrokerRegistry.get_adapter("dhan", "ws_manager")` while bootstrap imports `DhanWebSocketManager` directly.
- **Impact:** A change to WebSocket init (e.g., new param) requires edits in 2+ files.
- **Fix:** `_streaming.py` should delegate to bootstrap's `_start_trading()` or share a common factory.

### SS-2: `Gateway._load_config_from_env()` duplicates env loading
- **Files:** `scalpr/brokers/gateway/facade.py:123-157` and `scalpr/api/bootstrap.py:30-33`
- **Problem:** Both call `load_dotenv()`. Both read `DHAN_CLIENT_ID`, `DHAN_ACCESS_TOKEN` from env. Bootstrap also reads `SCALPR_WATCHLIST`, `SCALPR_LIVE_ORDERS`, etc.
- **Impact:** Adding a new config variable requires edits in 2+ files.
- **Severity:** Low — config is stable.

### SS-3: `OrderManager._append_event()` callers do pre- vs post-mutation inconsistently
- **Files:** `scalpr/execution/order_manager.py` — `add_order` (post-append), `update_order_state` (post-append), `process_fill` (post-append)
- **Problem:** K-014 made `_append_event` transactional (raises on failure). But `add_order` persists state in `OmsRepository` BEFORE calling `_append_event`. If `_append_event` raises, the OMS state has already been mutated with no rollback.
- **Fix:** All three callers must invoke `_append_event` BEFORE mutating OMS state, so a failed append leaves no side effects.

---

## 5. Simplified Target Architecture

### Keep
| Module | Role | Reason |
|--------|------|--------|
| `api/bootstrap.py` | Composition root | Single entry point, `Dependencies` dataclass |
| `api/main.py` | Uvicorn entry | 4-line delegator, trivial |
| `brokers/broker_port.py` | 3 typed ports | Clean interface boundary |
| `brokers/dhan/connection.py` | Connection orchestrator | Cleanly decomposed |
| `brokers/dhan/http_client.py` | HTTP transport | Without CircuitBreaker duplication, with inlined helpers |
| `brokers/dhan/auth.py` | Token lifecycle | TOTP cooldown + refresh |
| `brokers/dhan/gateway.py` | Dhan impl | Implements IBrokerGateway |
| `brokers/gateway/facade.py` | Broker-agnostic facade | High-level API |
| `brokers/contracts.py` | Canonical models | Single source of truth |
| `execution/order_router.py` | Order routing | Clean, uses ITradingPort |
| `oms/order_manager.py` | Order lifecycle + persistence | Fix pre/post mutation ordering |
| `risk/circuit_breaker.py` | Financial risk circuit breaker | KEEP and RENAME http_client version |
| `domain/` | Domain models | Pure, no broker dependencies |
| `simulation/simulated_gateway.py` | Test double | Full IBrokerGateway implementation |

### Merge
| From | Into | Reason |
|------|------|--------|
| `_http_common.py` | `http_client.py` | Only used by `http_client.py`. 83 lines of trivial helpers. |
| `_token_lifecycle.py:TokenBroadcast` | `auth.py` | `TokenBroadcast` is only used by `auth.py`. `TokenRefreshScheduler` is deleted. |
| `gateway/_market_data.py` | `facade.py` | 180-line mixin, single consumer. |
| `gateway/_portfolio.py` | `facade.py` | 110-line mixin, single consumer. |

### Delete
| File | Lines | Reason |
|------|-------|--------|
| `_token_lifecycle.py` (class TokenRefreshScheduler) | ~70 | Dead code |
| `gateway.py:adapters()` | ~12 | Dead code |
| `http_client.py:_bucket_for, _backoff_delay` | ~8 | Unnecessary wrappers |
| `ws_manager.py:token_refresh_fn` param | ~10 | Dead parameter |

---

## 6. Required Tests Before Deploy

### Critical (gate failures)
1. **Full lifecycle test** — `SimulatedGateway` connect → trade → position → disconnect (exists in `test_e2e_5day_replay.py` and `test_gateway_connection.py`)
2. **Auth failure recovery** — 401 triggers `ensure_fresh_token(force=True)`, retries, eventual success or `AuthenticationError` (exists: `test_verify_connection_retry.py`)
3. **TOTP cooldown propagation** — `TotpRateLimitError` from `generate_token` propagates to caller (exists: `test_auth.py`)
4. **Order persistence atomicity** — `_append_event` failure does NOT leave mutated OMS state (NEW: add test for pre-mutation ordering fix)
5. **EventStore transactional guarantee** — `append()` failure raises and caller can retry (exists: `test_event_store_wiring.py`)
6. **Circuit breaker open → order rejection** — CB trip blocks orders (exists: `test_pre_trade.py`)

### Important
7. **Kill switch `SCALPR_LIVE_ORDERS=0`** — all orders rejected (exists: `test_bootstrap.py`)
8. **WebSocket reconnect on token change** — `_handle_token_change` triggers reconnect (exists: `test_ws_token_refresh.py`)
9. **5-day replay simulation** — deterministic synthetic run with 6 invariants (exists: `test_e2e_5day_replay.py`)

### Missing (ADD)
10. **`_append_event` pre-mutation ordering** — Test that `process_fill` fails cleanly when EventStore is down (OMS state unchanged)
11. **`TokenBroadcast` survives receiver crash** — One receiver raising does not prevent others from receiving

---

## 7. Go / No-Go Deployment Decision

### NO-GO — 3 blockers must be resolved first:

| # | Blocker | Severity | Fix |
|---|---------|----------|-----|
| B1 | **`OrderManager._append_event` called AFTER state mutation** | HIGH (data corruption on partial write) | Reorder calls: append BEFORE OmsRepository.save() in all 3 callers |
| B2 | **`CircuitBreaker` naming collision** | MEDIUM (confusion, wrong import) | Rename `http_client.CircuitBreaker` → `HttpCircuitBreaker` |
| B3 | **Dead `token_refresh_fn` path through `ws_manager.py` → `ws_client.py`** | MEDIUM (dead code, false sense of safety) | Remove parameter end-to-end |

### Once blockers are resolved and tests added (items 10-11 above):
- **GO** — Architecture is sound. Code is clean. All critical paths are tested.
- Existing contract tests (1007 unit+contract passing) provide strong regression protection.
- Integration tests require Dhan credentials (CI cannot run them) — this is an accepted risk.

### Deployment checklist:
- [ ] B1 fixed: `_append_event` called before state mutation in all 3 callers
- [ ] B2 fixed: `http_client.CircuitBreaker` renamed to `HttpCircuitBreaker`
- [ ] B3 fixed: `token_refresh_fn` removed from `ws_manager.py` and `ws_client.py`
- [ ] Delete dead code per section 3
- [ ] Merge `_http_common.py` into `http_client.py`
- [ ] Add pre-mutation ordering test (item 10)
- [ ] Add TokenBroadcast isolation test (item 11)
- [ ] Run `pytest tests/unit/ tests/contract/ -q --tb=short` — expect 1007+ passed, 0 failures
- [ ] Deleted files removed from version control

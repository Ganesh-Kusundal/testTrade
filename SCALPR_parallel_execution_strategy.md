# SCALPR PARALLEL EXECUTION STRATEGY: Multi-Agent Team Deployment

## EXECUTIVE SUMMARY

Transformed the sequential 24-day build plan into a **11.5-day parallel execution strategy** using 6 waves of multi-agent teams. Based on actual import dependency analysis of the codebase.

**Key Insight**: 60% of modules can be built in parallel after foundational domain layer completes.

---

## DETAILED IMPORT DEPENDENCY ANALYSIS

Based on actual `from scalpr.*` imports across the codebase:

### LEVEL 0 (NO DEPENDENCIES - CAN RUN IN PARALLEL)
```
scalpr/domain/
├── order.py → instrument.py
├── position.py → instrument.py, order.py  
├── fill.py → order.py
├── tick.py (NO imports) ← CAN START IMMEDIATELY
├── instrument.py (NO imports) ← CAN START IMMEDIATELY
├── signal.py (NO imports) ← CAN START IMMEDIATELY
└── events.py → order.py, fill.py, position.py, tick.py
```

### LEVEL 1 (DEPENDS ON LEVEL 0 ONLY - PARALLEL AFTER L0)
```
scalpr/brokers/broker_port.py → domain (order, fill, position)
scalpr/market_data/feed_port.py → domain (tick)
scalpr/strategy/strategy_port.py → domain (tick, OHLCV)
scalpr/scanner/scanner_port.py → domain (instrument)
scalpr/brokers/dhan/dtos.py (NO domain imports) ← CAN START IMMEDIATELY
scalpr/signals/indicators.py → domain (tick, OHLCV)
```

### LEVEL 2 (DEPENDS ON LEVEL 1 - SOME PARALLELIZATION)
```
scalpr/brokers/dhan/mapper.py → broker_port, dtos, domain
scalpr/market_data/validators.py → domain (tick)
scalpr/market_data/aggregator.py → domain (tick, OHLCV)
scalpr/risk/position_sizer.py → domain (tick, OHLCV)
scalpr/signals/volume_profile.py → domain (OHLCV)
scalpr/signals/cvd.py → domain (tick)
scalpr/simulation/fill_simulator.py → domain (order, OHLCV)
```

### LEVEL 3 (DEPENDS ON LEVEL 2 - CRITICAL PATH)
```
scalpr/brokers/dhan/gateway.py → broker_port, mapper, dtos, domain
scalpr/market_data/dhan_feed.py → feed_port, domain (tick)
scalpr/market_data/historical.py → broker_port, domain (tick, OHLCV)
scalpr/signals/gate_fsm.py → (standalone)
scalpr/oms/paper_oms.py → broker_port, domain (all)
scalpr/risk/pre_trade.py → domain (order, position)
scalpr/risk/session_guard.py → domain (position)
scalpr/risk/circuit_breaker.py → domain (position)
```

### LEVEL 4 (DEPENDS ON LEVEL 3 - INTEGRATION LAYER)
```
scalpr/oms/order_manager.py → domain (order, fill)
scalpr/oms/persistence.py → domain (order, fill, position)
scalpr/strategy/scalpr_amt.py → broker_port, domain, signals
scalpr/strategy/executor.py → strategy_port, broker_port, risk
scalpr/simulation/backtester.py → domain, paper_oms, fill_simulator, strategy
scalpr/simulation/replay_engine.py → domain, executor
scalpr/simulation/walk_forward.py → backtester
scalpr/portfolio/portfolio.py → domain (fill, position, tick)
scalpr/portfolio/analytics.py → portfolio, domain
scalpr/scanner/options_scanner.py → domain (instrument)
```

### LEVEL 5 (TOP-LEVEL INTEGRATION)
```
scalpr/api/main.py → brokers, market_data, strategy, domain
frontend/ → API (WebSocket + REST)
```

---

## PARALLEL EXECUTION WAVES

### WAVE 1: DOMAIN CORE + PORT INTERFACES (Day 1-2)
**4 PARALLEL TEAMS - NO CROSS-DEPENDENCIES**

#### TEAM A: Domain Types (1 day)
**Files**: `scalpr/domain/order.py`, `position.py`, `fill.py`, `instrument.py`, `tick.py`

**Tasks**:
1. Strengthen `__post_init__` validation in all domain types
2. Add helper methods: `Order.is_active()`, `Order.notional_value()`, `Position.is_reducing()`
3. Add invariants: non-negative quantities, price bounds, timestamp sanity checks
4. Ensure all Decimal precision maintained

**Tests** (expand `tests/unit/domain/test_domain.py`):
- `test_order_rejects_negative_quantity()`
- `test_order_rejects_zero_price_for_limit_orders()`
- `test_position_detects_reducing_fill()`
- `test_order_notional_is_decimal()`

**Dependencies**: NONE (can start immediately)

---

#### TEAM B: Domain Events + Instrument Registry (1 day)
**Files**: `scalpr/domain/events.py`, NEW `scalpr/domain/instrument_registry.py`

**Tasks**:
1. Complete event system with all missing frozen dataclasses:
   - `OrderModified`, `OrderCancelled`, `OrderRejected`, `OrderExpired`
   - `PositionOpened`, `PositionClosed`, `PositionReversed`
   - `SignalGenerated`, `GateFailed`, `CircuitBreakerTripped`
   - `TickReceived`, `BarClosed`, `HistoricalDataLoaded`
   - `RiskCheckPassed`, `RiskCheckFailed`, `SessionHalted`
2. Add event base class with immutable UTC timestamp
3. Build instrument registry with thread-safe reads
4. Support lookup by: symbol, security_id, strike+expiry+option_type

**Tests** (NEW files):
- `tests/unit/domain/test_events.py`: `test_all_events_are_frozen_and_immutable()`
- `tests/unit/domain/test_instrument_registry.py`: `test_registry_lookup_by_symbol()`

**Dependencies**: NONE (can start immediately)

---

#### TEAM C: Port Interfaces (0.5 days)
**Files**: `scalpr/brokers/broker_port.py`, `market_data/feed_port.py`, `strategy/strategy_port.py`, `scanner/scanner_port.py`

**Tasks**:
1. Review all abstract interfaces for completeness
2. Ensure type safety (no bare dicts)
3. Add missing methods to `IBrokerGateway` if needed
4. Verify all ports use domain types only (no framework imports)

**Tests**: Integration tests for interface contracts

**Dependencies**: NONE (can start immediately)

---

#### TEAM D: Signal Indicators (1 day)
**Files**: `scalpr/signals/indicators.py`

**Tasks**:
1. Complete ATR calculation with Decimal precision
2. Implement momentum indicators
3. Add structure detection (higher highs, lower lows)
4. Ensure all calculations use Decimal, not float

**Tests** (NEW `tests/unit/signals/test_indicators.py`):
- `test_atr_calculation_is_decimal()`
- `test_momentum_detects_uptrend()`
- `test_structure_identifies_higher_highs()`

**Dependencies**: NONE (can start immediately)

---

### WAVE 2: BROKER MAPPING + MARKET DATA VALIDATION (Day 2-3)
**3 PARALLEL TEAMS - DEPENDS ON WAVE 1**

#### TEAM E: Dhan Mapper + DTOs (1 day)
**Files**: `scalpr/brokers/dhan/mapper.py`, `dtos.py`

**Tasks**:
1. Ensure all mapper functions are pure (no side effects)
2. Use Result types for error handling (no exceptions)
3. Complete order → DhanRequest mapping
4. Complete DhanResponse → Fill mapping
5. Complete position mapping with Decimal conversion

**Tests** (expand `tests/unit/brokers/test_gateway.py`):
- `test_mapper_price_is_decimal_not_float()`
- `test_mapper_is_pure_same_input_same_output()`
- `test_mapper_raises_nothing_returns_result_type()`

**Dependencies**: TEAM A (Domain Types), TEAM C (Port Interfaces)

---

#### TEAM F: Market Data Validators + Aggregator (1.5 days)
**Files**: `scalpr/market_data/validators.py`, `aggregator.py`

**Tasks**:
1. **CRITICAL FIX**: Change aggregator to mutate current bar instead of creating new objects
2. Complete tick validators: dedup, staleness, price sanity
3. Add out-of-order tick handling
4. Add performance monitoring (ticks/sec)

**Tests** (expand `tests/unit/market_data/test_market_data.py`):
- `test_aggregator_mutates_current_bar_not_recreate()` ← CRITICAL
- `test_aggregator_rolls_over_at_bar_boundary()`
- `test_validator_rejects_stale_tick()`
- `test_validator_deduplicates_same_exchange_timestamp()`

**Dependencies**: TEAM A (Domain Types)

---

#### TEAM G: Risk Core + Volume Profile + CVD (1.5 days)
**Files**: `scalpr/risk/position_sizer.py`, `signals/volume_profile.py`, `signals/cvd.py`

**Tasks**:
1. Complete ATR-based position sizing (lot-size aligned)
2. Implement session VP (OHLCV-only) and tick VP
3. Recalculate POC, VAH, VAL on bar close
4. Detect LVN/HVN areas
5. CVD accumulation and divergence detection

**Tests** (NEW files):
- `tests/unit/risk/test_position_sizer.py`: `test_sizer_returns_lot_aligned_quantity()`
- `tests/unit/signals/test_volume_profile.py`: `test_vp_recalculates_poc_on_bar_close()`
- `tests/unit/signals/test_cvd.py`: `test_cvd_accumulates_delta()`

**Dependencies**: TEAM A (Domain Types), TEAM D (Indicators)

---

### WAVE 3: BROKER GATEWAY + MARKET DATA FEED + RISK ENGINE (Day 4-6)
**4 PARALLEL TEAMS - DEPENDS ON WAVE 2**

#### TEAM H: DhanGateway HTTP Integration (2 days)
**Files**: `scalpr/brokers/dhan/gateway.py`

**Tasks**:
1. Integrate `httpx.AsyncClient` as default HTTP client
2. Implement real authentication (login, token refresh)
3. Implement DhanHQ v2 REST API endpoints (place, modify, cancel, positions, margins)
4. Add error classification (transient vs permanent)
5. Add request/response logging (redact sensitive data)

**Tests** (expand `tests/unit/brokers/test_gateway.py`):
- `test_gateway_auth_token_refresh_on_401()`
- `test_gateway_maps_dhan_error_codes()`
- `test_gateway_retries_on_transient_error()`
- Integration test: `test_gateway_place_order_live_paper_account()`

**Dependencies**: TEAM E (Dhan Mapper)

---

#### TEAM I: UpstoxGateway Implementation (2 days)
**Files**: NEW `scalpr/brokers/upstox/gateway.py`, `mapper.py`, `dtos.py`

**Tasks**:
1. Mirror DhanGateway architecture exactly
2. Implement OAuth2 authentication flow
3. Rate limiting (Upstox: 20 req/sec)
4. Error classification
5. Segment/exchange mapping

**Tests** (NEW `tests/unit/brokers/test_upstox_gateway.py`):
- Mirror all DhanGateway tests
- `test_upstox_mapper_is_pure()`
- `test_upstox_gateway_rate_limiter()`

**Dependencies**: TEAM E (Dhan Mapper - for architecture reference)

---

#### TEAM J: DhanFeed WebSocket (2 days)
**Files**: `scalpr/market_data/dhan_feed.py`

**Tasks**:
1. Integrate `websockets` library or DhanHQ WebSocket SDK
2. Persistent WebSocket with authentication
3. Automatic reconnection with exponential backoff (max 5 attempts)
4. Ping/pong keepalive (30s idle detection)
5. Backpressure handling (async queue, 10k tick buffer)
6. Connection state monitoring

**Tests** (expand `tests/unit/market_data/test_market_data.py`):
- `test_feed_reconnects_on_disconnect()`
- `test_feed_drops_ticks_when_queue_full()`
- `test_feed_calculates_delta_volume_correctly()`
- Integration test: `test_feed_streams_live_ticks()`

**Dependencies**: TEAM F (Validators + Aggregator)

---

#### TEAM K: Risk Engine Integration (1.5 days)
**Files**: `scalpr/risk/pre_trade.py`, `session_guard.py`, `circuit_breaker.py`

**Tasks**:
1. **Pre-Trade Gate**: Hard enforcement (non-bypassable)
2. **Session Guard**: 3-loss halt, IST square-off timers
3. **Circuit Breaker**: Daily loss (3%), drawdown (5%), manual reset
4. Add logging for all risk checks

**Tests** (NEW files):
- `tests/unit/risk/test_pre_trade.py`: `test_gate_blocks_order_exceeding_risk()`
- `tests/unit/risk/test_session_guard.py`: `test_guard_halts_after_3_losses()`
- `tests/unit/risk/test_circuit_breaker.py`: `test_breaker_halts_on_daily_loss()`

**Dependencies**: TEAM G (Risk Core)

---

### WAVE 4: OMS PERSISTENCE + STRATEGY EXECUTOR + SIMULATION CORE (Day 7-9)
**3 PARALLEL TEAMS - DEPENDS ON WAVE 3**

#### TEAM L: OMS + Persistence (2 days)
**Files**: `scalpr/oms/order_manager.py`, `persistence.py`

**Tasks**:
1. SQLite CRUD: save_order, save_fill, save_position, save_daily_pnl
2. WAL mode for concurrent reads
3. Atomic transactions for order+fill saves
4. Heartbeat reconciliation (every 30s)
5. Crash recovery: restore_from_db()

**Tests** (NEW `tests/unit/oms/test_persistence.py`):
- `test_persistence_saves_and_restores_order()`
- `test_persistence_atomic_transaction_on_order_fill()`
- `test_persistence_restores_oms_state_on_restart()`
- `test_heartbeat_reconciles_positions()`

**Dependencies**: TEAM H (DhanGateway), TEAM K (Risk Engine)

---

#### TEAM M: Strategy Executor + Gate FSM (2 days)
**Files**: `scalpr/strategy/executor.py`, `signals/gate_fsm.py`

**Tasks**:
1. Create StrategyExecutor orchestrator
2. Integrate risk check before every order
3. Add staleness guards to Gate FSM
4. Handle strategy exceptions gracefully
5. Track metrics: signals, orders, fills, latency

**Tests** (NEW files):
- `tests/unit/strategy/test_executor.py`: `test_executor_runs_risk_check_before_order()`
- `tests/unit/signals/test_gate_fsm.py`: `test_gate_fsm_rejects_stale_data()`

**Dependencies**: TEAM K (Risk Engine), TEAM G (Volume Profile + CVD)

---

#### TEAM N: Simulation: Backtester + Fill Simulator (2 days)
**Files**: `scalpr/simulation/backtester.py`, `fill_simulator.py`

**Tasks**:
1. Look-ahead bias prevention (strategy only sees bar T)
2. Slippage model (market orders: next-bar open + slippage)
3. Transaction costs (brokerage + STT + exchange fees)
4. Limit order fill logic (bar low/high crosses limit)
5. Performance metrics output

**Tests** (NEW files):
- `tests/unit/simulation/test_backtester.py`: `test_backtester_prevents_lookahead_bias()`
- `tests/unit/simulation/test_fill_simulator.py`: `test_simulator_applies_slippage()`

**Dependencies**: TEAM L (OMS), TEAM M (Strategy Executor)

---

### WAVE 5: PORTFOLIO + SCANNER + REPLAY ENGINE (Day 10-11)
**3 PARALLEL TEAMS - DEPENDS ON WAVE 4**

#### TEAM O: Portfolio + Analytics (1.5 days)
**Files**: `scalpr/portfolio/portfolio.py`, `analytics.py`

**Tasks**:
1. Decimal audit (no float leakage)
2. Per-strategy PnL attribution
3. Drawdown series (not just max DD)
4. Per-trade analytics (entry, exit, duration, R-multiple)

**Tests** (NEW files):
- `tests/unit/portfolio/test_portfolio.py`: `test_portfolio_all_arithmetic_is_decimal()`
- `tests/unit/portfolio/test_analytics.py`: `test_analytics_calculates_sharpe_ratio()`

**Dependencies**: TEAM L (OMS), TEAM N (Backtester)

---

#### TEAM P: Options Scanner (1.5 days)
**Files**: `scalpr/scanner/options_scanner.py`

**Tasks**:
1. ATM strike selection (based on delta)
2. Liquidity filter (OI, volume, spread)
3. IST scheduling (run at 09:45)
4. Rank by setup quality

**Tests** (NEW `tests/unit/scanner/test_options_scanner.py`):
- `test_scanner_selects_atm_strikes()`
- `test_scanner_filters_illiquid_contracts()`

**Dependencies**: TEAM A (Domain Types)

---

#### TEAM Q: Replay Engine + Walk-Forward (2 days)
**Files**: `scalpr/simulation/replay_engine.py`, `walk_forward.py`

**Tasks**:
1. Configurable replay speed (1x, 10x, 100x, realtime)
2. Pause/resume, step-forward/backward
3. State checkpoint (save/restore)
4. Walk-forward: train → test → roll forward
5. Overfitting detection

**Tests** (NEW files):
- `tests/unit/simulation/test_replay_engine.py`: `test_replay_replays_at_configurable_speed()`
- `tests/unit/simulation/test_walk_forward.py`: `test_walk_forward_detects_overfitting()`

**Dependencies**: TEAM N (Backtester)

---

### WAVE 6: API + FRONTEND INTEGRATION (Day 12-14)
**2 PARALLEL TEAMS - DEPENDS ON WAVE 5**

#### TEAM R: FastAPI Backend (2 days)
**Files**: `scalpr/api/main.py`, NEW `scalpr/api/routes/`, `scalpr/api/ws/`

**Tasks**:
1. REST endpoints: /positions, /orders, /pnl, /strategy/status, /health
2. WebSocket hub: stream ticks, OHLCV, signals, order events
3. JWT authentication
4. CORS configuration

**Tests** (NEW `tests/integration/test_api.py`):
- `test_api_returns_positions()`
- `test_api_streams_ticks_via_websocket()`
- `test_api_requires_jwt_authentication()`

**Dependencies**: TEAM H (DhanGateway), TEAM J (DhanFeed), TEAM M (Strategy Executor)

---

#### TEAM S: Frontend Integration (3 days)
**Files**: `frontend/src/` (all components)

**Tasks**:
1. Connect to FastAPI WebSocket hub
2. Bloomberg-style terminal layout
3. Real-time data streaming
4. Canvas-based charts
5. Historical-to-live seam

**Tests** (expand `frontend/src/__tests__/`):
- `test_websocket_connects_and_receives_ticks()`
- `test_chart_renders_candles_from_live_data()`

**Dependencies**: TEAM R (FastAPI Backend)

---

## CRITICAL PATH ANALYSIS

### Longest Sequential Path (CANNOT be parallelized):
```
TEAM A: Domain Types (1 day)
  → TEAM E: Dhan Mapper (1 day)
    → TEAM H: DhanGateway (2 days)
      → TEAM L: OMS Persistence (2 days)
        → TEAM M: Strategy Executor (2 days)
          → TEAM N: Backtester (2 days)
            → TEAM R: API (2 days)
              → TEAM S: Frontend (3 days)

TOTAL CRITICAL PATH: 15 days
```

### With Parallel Execution:
```
Wave 1: 1 day (4 teams parallel)
Wave 2: 1.5 days (3 teams parallel)
Wave 3: 2 days (4 teams parallel)
Wave 4: 2 days (3 teams parallel)
Wave 5: 2 days (3 teams parallel)
Wave 6: 3 days (2 teams parallel)

TOTAL WITH PARALLELISM: 11.5 days
```

**Speedup**: 2.1x faster than pure sequential (24 days → 11.5 days)

---

## MULTI-AGENT DEPLOYMENT PROTOCOL

### Agent Assignment per Wave:

**Wave 1** (4 agents parallel):
- Agent A → TEAM A (Domain Types)
- Agent B → TEAM B (Events + Registry)
- Agent C → TEAM C (Port Interfaces)
- Agent D → TEAM D (Indicators)

**Wave 2** (3 agents parallel):
- Agent E → TEAM E (Dhan Mapper)
- Agent F → TEAM F (Validators + Aggregator)
- Agent G → TEAM G (Risk Core + VP + CVD)

**Wave 3** (4 agents parallel):
- Agent H → TEAM H (DhanGateway)
- Agent I → TEAM I (UpstoxGateway)
- Agent J → TEAM J (DhanFeed WebSocket)
- Agent K → TEAM K (Risk Engine)

**Wave 4** (3 agents parallel):
- Agent L → TEAM L (OMS + Persistence)
- Agent M → TEAM M (Strategy Executor + Gate FSM)
- Agent N → TEAM N (Backtester + Fill Simulator)

**Wave 5** (3 agents parallel):
- Agent O → TEAM O (Portfolio + Analytics)
- Agent P → TEAM P (Options Scanner)
- Agent Q → TEAM Q (Replay Engine + Walk-Forward)

**Wave 6** (2 agents parallel):
- Agent R → TEAM R (FastAPI Backend)
- Agent S → TEAM S (Frontend Integration)

---

## TESTING STRATEGY (PARALLEL-FRIENDLY)

### Unit Tests (run in parallel with pytest-xdist):
```bash
pytest -n auto tests/unit/ --cov=scalpr --cov-report=html
```

### Integration Tests (run after each wave):
```bash
pytest tests/integration/ -v
```

### Performance Tests (run after Wave 4):
```bash
pytest tests/performance/ -v --benchmark-only
```

---

## RISK MITIGATIONS FOR PARALLEL EXECUTION

### Risk 1: Team Dependencies Block Progress
**Mitigation**: Daily sync at wave boundaries. If TEAM A finishes early, TEAM E can start early.

### Risk 2: Merge Conflicts in Shared Files
**Mitigation**: 
- Domain types (TEAM A) touch different files than Events (TEAM B)
- Port interfaces (TEAM C) are read-only after Wave 1
- Use feature branches per team, merge at wave boundaries

### Risk 3: Inconsistent Decimal Usage
**Mitigation**: CI test that fails if `float` detected in price/PnL paths:
```bash
grep -r "float" scalpr/domain/ scalpr/oms/ scalpr/portfolio/ && exit 1
```

### Risk 4: Test Interdependencies
**Mitigation**: Each team's tests are isolated. No cross-team test dependencies.

---

## SUCCESS CRITERIA PER WAVE

### Wave 1 Complete:
- ✅ All domain types have 100% test coverage
- ✅ Event system complete with all event types
- ✅ All port interfaces reviewed and finalized

### Wave 2 Complete:
- ✅ DhanMapper is pure, uses Result types
- ✅ Aggregator mutates current bar (performance fix)
- ✅ Position sizer returns lot-aligned quantities

### Wave 3 Complete:
- ✅ DhanGateway places orders on live paper account
- ✅ UpstoxGateway implemented with same contract
- ✅ WebSocket streams live ticks with reconnection
- ✅ Risk engine enforces hard halts

### Wave 4 Complete:
- ✅ OMS persists to SQLite, recovers from crash
- ✅ Strategy executor runs risk checks before orders
- ✅ Backtester prevents look-ahead bias

### Wave 5 Complete:
- ✅ Portfolio tracks per-strategy PnL with Decimal
- ✅ Scanner selects ATM strikes at 09:45 IST
- ✅ Replay engine supports pause/resume/checkpoint

### Wave 6 Complete:
- ✅ API streams data via WebSocket to frontend
- ✅ Bloomberg-style terminal live with real-time updates

---

## REJECTED ALTERNATIVES

### Alternative 1: Pure Sequential Execution (24 days)
**Rejected Because**: 2.1x slower. Many modules have NO cross-dependencies and can be built in parallel. Wastes 12.5 days.

### Alternative 2: Microservices Architecture
**Rejected Because**: Over-engineering for single-machine deployment. In-process modules with clear boundaries are sufficient. Introduce microservices only when scaling to distributed architecture.

### Alternative 3: Skip Tests to Save Time
**Rejected Because**: Build plan Rule #4: "Tests are not optional." Skipping tests leads to untestable code, coverage gaps, and production bugs. TDD ensures testability from day 1.

### Alternative 4: Use ORM (SQLAlchemy) for OMS
**Rejected Because**: Adds unnecessary abstraction. Direct SQLite is simpler, faster, easier to audit. OMS persistence is a single seam class, not a full data layer.

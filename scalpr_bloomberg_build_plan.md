# SCALPR — Bloomberg-Style Quant Infrastructure
## Principal Lead Architect Build Plan: Ground-Up, Module-by-Module

> **Mandate**: Build a professional-grade, Bloomberg Terminal-inspired quantitative
> trading infrastructure for strategy execution, backtesting, replay, risk management,
> and live trading on Indian markets (NSE/MCX). Every module is built correctly once,
> tested before it is coded, and composed cleanly from the domain outward.

---

## The Architecture Vision

```
┌─────────────────────────────────────────────────────────────────────┐
│                    SCALPR BLOOMBERG INFRASTRUCTURE                  │
├─────────────────────────────────────────────────────────────────────┤
│  PRESENTATION LAYER                                                 │
│  Bloomberg-style Terminal UI (React + Canvas)                       │
│  Multi-pane: Chart | Order Book | Positions | P&L | Risk Dashboard  │
├─────────────────────────────────────────────────────────────────────┤
│  APPLICATION LAYER                                                  │
│  FastAPI + WebSocket Hub | REST API | Event Bus                     │
├─────────────────────────────────────────────────────────────────────┤
│  STRATEGY LAYER                                                     │
│  Strategy Executor | Gate FSM | Signal Engine | Scanner             │
├─────────────────────────────────────────────────────────────────────┤
│  TRADING LAYER                                                      │
│  OMS | Risk Engine | Position Sizer | Portfolio Manager             │
├─────────────────────────────────────────────────────────────────────┤
│  SIMULATION LAYER                                                   │
│  Backtester | Replay Engine | Walk-Forward | Paper OMS              │
├─────────────────────────────────────────────────────────────────────┤
│  DATA LAYER                                                         │
│  Market Data Pipeline | Historical Store | Tick Aggregator          │
├─────────────────────────────────────────────────────────────────────┤
│  BROKER LAYER                                                       │
│  IBrokerGateway | DhanGateway | UpstoxGateway | Mapper | DTOs       │
├─────────────────────────────────────────────────────────────────────┤
│  DOMAIN CORE                                                        │
│  Order | Position | Fill | Signal | Tick | OHLCV | Instrument       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Repository Structure

```
scalpr/
├── domain/
│   ├── order.py           # Order, OrderSide, OrderType, OrderState FSM
│   ├── position.py        # Position, PositionSide, PositionState
│   ├── fill.py            # Fill, PartialFill
│   ├── signal.py          # Signal, SignalType, Gate
│   ├── instrument.py      # Instrument, Exchange, Segment, OptionType
│   ├── tick.py            # Tick, OHLCV, Delta, CVD
│   └── events.py          # All domain events (immutable, frozen)
│
├── brokers/
│   ├── broker_port.py     # IBrokerGateway — the abstract contract
│   ├── dhan/
│   │   ├── gateway.py     # Auth, retry, rate limit, error norm
│   │   ├── mapper.py      # Pure DTO ↔ Domain transforms
│   │   └── dtos.py        # DhanOrderRequest/Response (frozen)
│   └── upstox/
│       ├── gateway.py
│       ├── mapper.py
│       └── dtos.py
│
├── market_data/
│   ├── feed_port.py       # IMarketDataFeed interface
│   ├── dhan_feed.py       # WS connection, tick parsing, reconnect
│   ├── historical.py      # Historical OHLCV loader + seam stitcher
│   ├── aggregator.py      # Tick → OHLCV candle builder (mutates last)
│   └── validators.py      # Dedup, staleness, gap detection
│
├── oms/
│   ├── order_manager.py   # OMS lifecycle FSM
│   ├── paper_oms.py       # Paper trading OMS
│   └── persistence.py     # SQLite crash-safe state
│
├── risk/
│   ├── pre_trade.py       # Pre-trade checks (margin, limits, halts)
│   ├── position_sizer.py  # ATR-based 1% fixed risk sizing
│   ├── session_guard.py   # 3-loss halt, IST square-off timer
│   └── circuit_breaker.py # Daily loss, drawdown circuit breakers
│
├── signals/
│   ├── gate_fsm.py        # Gates 01-08 sequential FSM
│   ├── volume_profile.py  # VP, POC, VAH, VAL, LVN/HVN
│   ├── cvd.py             # CVD, Delta, imbalance detection
│   └── indicators.py      # ATR, momentum, structure
│
├── strategy/
│   ├── strategy_port.py   # IStrategy contract
│   ├── scalpr_amt.py      # Fabio Valentini AMT strategy
│   └── executor.py        # Strategy orchestrator
│
├── simulation/
│   ├── backtester.py      # Event-driven backtester
│   ├── replay_engine.py   # Tick-by-tick historical replay
│   ├── walk_forward.py    # Walk-forward test framework
│   └── fill_simulator.py  # Slippage + fill probability model
│
├── portfolio/
│   ├── portfolio.py       # Portfolio state, Decimal PnL
│   └── analytics.py       # Per-trade, per-strategy attribution
│
├── scanner/
│   ├── scanner_port.py    # IScanner interface
│   └── options_scanner.py # 09:45 options contract scanner
│
├── api/
│   ├── main.py            # FastAPI entrypoint
│   ├── routes/            # REST endpoints
│   └── ws/                # WebSocket hub
│
├── frontend/              # React + TypeScript + Canvas charts
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── system/
│
└── config/
    ├── settings.py        # Pydantic settings
    └── broker_config.py
```

---

## MODULE BUILD SEQUENCE

Build in this exact order. Each module must be fully tested before the next begins.

---

### MODULE 1 — Domain Core

**Why first**: Every other module speaks the domain language. Define it once, correctly.

**Build targets**:
- `Instrument` — Exchange, Segment, OptionType, lot_size, tick_size (Decimal)
- `Order` — OrderSide, OrderType, OrderState FSM with validated transitions
- `Fill` — All prices as `Decimal`. No float ever.
- `Position` — PositionSide, avg_price, unrealised_pnl, realised_pnl (all Decimal)
- `Tick` — ltp, bid, ask, delta_volume, cumulative_volume, exchange_timestamp
- `OHLCV` — open/high/low/close/volume, bar_open_time (UTC), is_closed flag
- `Events` — All domain events as frozen dataclasses (OrderPlaced, FillReceived, etc.)

**Non-negotiable rules**:
- All money values: `Decimal`, never `float`
- All dataclasses: `frozen=True` — domain objects are immutable
- Zero external imports in domain/
- OrderState transitions raise `ValueError` on invalid moves

**Tests to write first (TDD)**:
```
test_order_state_invalid_transition_raises()
test_fill_price_is_decimal_not_float()
test_tick_delta_volume_separate_from_cumulative()
test_instrument_tick_size_decimal_precision()
test_ohlcv_bar_boundary_is_utc()
```

---

### MODULE 2 — Broker Gateway (PRIMARY TARGET)

**Why second**: The broker boundary is the most dangerous seam. Own it completely
before anything else touches external APIs.

**The correct layer architecture**:
```
Domain Order
     ↓
IBrokerGateway          ← abstract port (broker_port.py)
     ↓
DhanGateway             ← owns ALL broker interaction concerns:
     │                     authentication + session refresh
     │                     rate limiting (DhanHQ: 25 req/sec)
     │                     exponential backoff retry
     │                     error classification + normalisation
     │                     broker-specific quirks
     │                     DTO construction via DhanMapper injection
     ↓
DhanMapper              ← pure data transformer only:
     │                     Domain Order → DhanOrderRequest
     │                     DhanOrderResponse → Domain Fill
     │                     NO error handling, NO API calls, NO state
     ↓
DhanOrderRequest        ← frozen DTO (brokers/dhan/dtos.py)
     ↓
DhanHQ v2 REST API
     ↓
DhanOrderResponse       ← frozen DTO
     ↓
DhanMapper.to_domain()
     ↓
Domain Fill / OrderResult
```

**broker_port.py — THE CONTRACT (IBrokerGateway)**:
```python
from abc import ABC, abstractmethod
from domain.order import Order
from domain.fill import Fill
from domain.position import Position
from domain.instrument import Instrument
from typing import List

class IBrokerGateway(ABC):

    @abstractmethod
    def place_order(self, order: Order) -> Fill: ...

    @abstractmethod
    def modify_order(self, order_id: str, price: Decimal,
                     quantity: int) -> bool: ...

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool: ...

    @abstractmethod
    def get_order_status(self, order_id: str) -> Order: ...

    @abstractmethod
    def get_positions(self) -> List[Position]: ...

    @abstractmethod
    def get_margins(self) -> dict: ...

    @abstractmethod
    def is_connected(self) -> bool: ...

    @abstractmethod
    def square_off_all(self) -> List[Fill]: ...
```

**DhanGateway owns (exclusively)**:
- Session auth + token refresh
- Rate limiter (token bucket: 25 req/sec for DhanHQ)
- Retry: exponential backoff, max 3 attempts, non-retryable errors identified
- Error normalisation: Dhan error codes → domain `BrokerError` enum
- Broker quirks: NSE/MCX segment codes, exchange-specific field mappings
- Circuit breaker: opens after 5 consecutive broker errors

**DhanMapper owns (exclusively)**:
- `order_to_dhan_request(order: Order) -> DhanOrderRequest`
- `dhan_response_to_fill(response: DhanOrderResponse) -> Fill`
- `dhan_position_to_domain(pos: dict) -> Position`
- Pure functions: same input always produces same output
- No exceptions raised (returns `Result` type for invalid mappings)
- No API calls, no logging, no state

**Tests to write first (TDD)**:
```
test_gateway_retries_on_transient_error()
test_gateway_does_not_retry_on_400_bad_request()
test_gateway_rate_limiter_blocks_above_25_rps()
test_gateway_opens_circuit_after_5_failures()
test_mapper_price_is_decimal_not_float()
test_mapper_is_pure_same_input_same_output()
test_mapper_raises_nothing_returns_result_type()
test_square_off_all_calls_sell_for_all_long_positions()
```

---

### MODULE 3 — Market Data Pipeline

**Why third**: Live data must be rock-solid before strategy or backtest can consume it.

**Build targets**:

**dhan_feed.py (WebSocket)**:
- Persistent WebSocket connection to DhanHQ market data stream
- Automatic reconnection with exponential backoff
- Ping/pong keepalive with 30s idle detection
- Tick parsing: raw WS message → `Tick` domain object
- Volume: `delta_volume = current_tick.cumulative_vol - prev_tick.cumulative_vol`
- Timestamp: always store both `exchange_timestamp` and `received_at`
- Backpressure: async queue with max 10,000 tick buffer

**aggregator.py (Tick → OHLCV)**:
- Mutates the CURRENT candle for ticks within the same bar:
  ```
  last_candle.close = tick.ltp
  last_candle.high = max(last_candle.high, tick.ltp)
  last_candle.low = min(last_candle.low, tick.ltp)
  last_candle.volume += tick.delta_volume
  ```
- Rolls over to new candle only when `tick.exchange_timestamp` crosses bar boundary
- Bar boundary: calculated in IST (Indian Standard Time), UTC stored
- Thread-safe: mutable `current_candle` behind asyncio.Lock

**historical.py (The Seam Stitcher)**:
- Loads OHLCV history via DhanHQ REST
- Returns bars up to `last_bar_timestamp T`
- WebSocket consumer drops any tick where `tick.exchange_timestamp <= T`
- Applies only `tick.exchange_timestamp > T` to live aggregator
- Prevents: duplicate bars, gap bars, overwritten history

**validators.py**:
- Tick deduplication by `exchange_timestamp`
- Staleness check: reject tick if `exchange_timestamp` > 5 seconds old
- Gap detection: alert if bar sequence has missing bars
- Price sanity: reject tick if `ltp` deviates > 5% from last tick

**Tests to write first (TDD)**:
```
test_aggregator_mutates_last_candle_not_push_new()
test_aggregator_rolls_over_at_bar_boundary()
test_seam_stitcher_drops_ticks_before_history_end()
test_validator_rejects_stale_tick()
test_validator_deduplicates_same_exchange_timestamp()
test_volume_delta_not_cumulative_in_ohlcv()
```

---

### MODULE 4 — Order Management System (OMS)

**Build targets**:

**order_manager.py**:
- Full OrderState FSM with validated transitions
- Complete event log per order (every state change logged)
- Order deduplication by client_order_id
- Partial fill accumulation: fill quantities sum to total quantity
- Handles: PARTIALLY_FILLED → FILLED correctly
- Heartbeat reconciliation with broker positions every 30s

**paper_oms.py**:
- Identical interface to live OMS (implements IBrokerGateway)
- Fill simulation: market orders fill immediately at last tick price
- Slippage model: ±1 tick for market orders (configurable)
- Tracks: balance, positions, daily PnL, drawdown (all Decimal)

**persistence.py (SQLite)**:
- Persists OMS state after every state change
- `restore_from_db()` on restart — full crash recovery
- Tables: `orders`, `fills`, `positions`, `oms_state`, `daily_pnl`
- WAL mode enabled for concurrent reads

---

### MODULE 5 — Risk Engine

**Build targets**:

**pre_trade.py (Pre-Trade Risk Gate)**:
- Runs BEFORE every order submission — cannot be bypassed
- Checks (all configurable per strategy):
  - Capital at risk per trade ≤ 1% of portfolio
  - Max open positions ≤ N
  - Instrument concentration ≤ 20% of portfolio
  - Available margin ≥ required margin × 1.2 buffer
  - Market not halted or in auction
  - Daily loss limit not breached

**session_guard.py**:
- Tracks consecutive losses per session
- After 3 consecutive losses: calls `oms.square_off_all()`, halts new orders
- IST-aware auto square-off:
  - NSE EQ/FO: hard close at 15:15 IST
  - MCX: hard close at 23:15 IST
  - Warning alert 15 minutes before cutoff

**position_sizer.py**:
- ATR-based fixed-risk sizing:
  `quantity = floor(risk_amount / (atr * multiplier * lot_size))`
- Risk amount = portfolio_value × 0.01 (1%)
- Never exceeds `max_quantity` cap regardless of algorithm output
- Always returns int (lot-size aligned), never float

**circuit_breaker.py**:
- Daily loss circuit: halts if daily_loss > portfolio × 0.03 (3%)
- Drawdown circuit: halts if drawdown from peak > 5%
- Both circuits require manual reset (cannot auto-recover)
- Kill switch: `circuit_breaker.halt_all()` — stops all new orders instantly

---

### MODULE 6 — Signal Engine & Gate FSM

**Build targets**:

**gate_fsm.py (Gates 01–08 Sequential)**:
- Each gate is a pure function: `Gate.evaluate(market_state) -> GateResult`
- Gates evaluated in strict order: failure at Gate N short-circuits N+1 to N+8
- Gate 03 (CVD/Price correlation):
  - BLOCK if: CVD falling AND price NOT at LVN
  - PASS if: CVD falling AND price IS at LVN (institutional absorption)
- All gate decisions logged with snapshot of input data
- Staleness guard: reject evaluation if tick data older than threshold

**volume_profile.py**:
- Session VP: OHLCV-only profile (not tick-based)
- Tick VP: tick-based for impulse legs and CVD
- POC, VAH, VAL recalculate as each new bar closes
- LVN/HVN detection: areas of low/high volume concentration
- Anchor reset: on session open, on structural breaks
- Thread-safe: reads from VP never blocked by updates (read-write lock)

**cvd.py**:
- CVD = cumulative sum of delta across session
- Delta per tick: `delta = ask_qty - bid_qty` at execution price
- Divergence detection: CVD slope vs price slope (5-bar lookback)
- Imbalance detection: bid/ask imbalance at 5-level depth

---

### MODULE 7 — Simulation Engine (Backtester + Replay)

**Build targets**:

**backtester.py (Event-Driven)**:
- Driven by the SAME domain objects as live (no separate backtest models)
- Same strategy logic, same gate FSM, same risk engine
- Processes historical OHLCV in chronological order
- Calls strategy.on_bar(ohlcv) — identical to live on_tick()
- Look-ahead bias prevention: strategy only sees data up to current bar T
- Slippage model: market orders fill at next-bar open + slippage
- Transaction costs: brokerage + STT + exchange fees (Indian market rates)

**replay_engine.py (Tick-by-Tick)**:
- Replays stored tick data at configurable speed (1x, 10x, 100x, realtime)
- Same WebSocket feed interface as live — strategy cannot distinguish
- Supports pause, step-forward, step-backward
- State checkpoint: save/restore replay position

**walk_forward.py**:
- Train window → test window → roll forward → repeat
- Configurable: walk_period, train_ratio, test_ratio
- Output: per-window PnL, Sharpe, drawdown, win rate

**fill_simulator.py**:
- Market order: fills at `last_price + (1 tick * side_multiplier)`
- Limit order: fills if bar's low ≤ limit_price (buy) or high ≥ limit_price (sell)
- Partial fill probability model for limit orders at illiquid levels

---

### MODULE 8 — Portfolio Manager

**Build targets**:

**portfolio.py**:
- Tracks all open positions across all strategies
- All arithmetic: `Decimal` only
- Realised PnL: updated on every fill
- Unrealised PnL: updated on every tick (mark-to-market)
- Per-strategy PnL attribution
- Peak equity tracking for drawdown calculation

**analytics.py**:
- Per-trade: entry, exit, side, duration, PnL, R-multiple
- Per-strategy: total PnL, win rate, avg winner, avg loser, Sharpe, max DD
- Per-session: daily PnL, daily win rate, consecutive wins/losses
- Per-instrument: PnL by symbol, segment, expiry
- Drawdown series (not just max drawdown point)

---

### MODULE 9 — Scanner

**Build targets**:

**options_scanner.py**:
- Runs at 09:45 IST, scans NSE options universe
- ATM strike selection: based on delta, not price distance
- Liquidity filter: OI > threshold, volume > threshold, spread < max_spread
- Outputs: `List[Instrument]` ranked by setup quality
- Same `IScanner` interface for backtesting and live

---

### MODULE 10 — FastAPI Backend

**Build targets**:

**main.py + routes/ + ws/**:
- REST: positions, orders, PnL, strategy status, system health
- WebSocket hub: streams tick data, OHLCV bars, signals, order events
- Event bus: all domain events published to WS subscribers
- Authentication: JWT for UI access
- CORS configured for React frontend

---

### MODULE 11 — Bloomberg-Style React Frontend

**Build targets**:

**Terminal Layout (Bloomberg-inspired)**:
```
┌──────────────┬───────────────────┬──────────────────┐
│  INSTRUMENT  │   OHLCV + VP      │   ORDER BOOK     │
│  SELECTOR    │   CANVAS CHART    │   BID/ASK DEPTH  │
├──────────────┤   (multi-pane)    ├──────────────────┤
│  GATE FSM    │                   │   POSITIONS      │
│  STATUS      │                   │   TABLE          │
│  01-08       ├───────────────────┤                  │
├──────────────┤   CVD + DELTA     ├──────────────────┤
│  RISK        │   PANEL           │   DAILY PnL      │
│  DASHBOARD   │                   │   EQUITY CURVE   │
├──────────────┴───────────────────┴──────────────────┤
│              STRATEGY EXECUTION LOG                  │
│  (gate decisions, signals, orders, fills — live)     │
└─────────────────────────────────────────────────────┘
```

**Chart implementation rules**:
- HTML5 Canvas only — no SVG for financial charts
- Separate canvas layers: candles | volume | overlays | crosshair
- Crosshair on independent transparent overlay canvas (no candle repaint on mouse move)
- Partial repaint: only last candle bounding box repainted on live tick
- Historical-to-live seam: WS buffers until REST history resolves

---

## THE MASTER BUILD PROMPT

Use this prompt with your agents for each module:

---

```
You are the Principal Lead Architect building the SCALPR Bloomberg-style 
quantitative trading infrastructure from scratch.

You are building MODULE [N]: [MODULE NAME].

Context of what is already built:
[PASTE PREVIOUS MODULE SUMMARIES HERE]

Your rules for this module:
1. Write the failing test FIRST. Then write the code that makes it pass.
2. No float on any money, price, or PnL value. Decimal or int (paise) only.
3. Domain objects never import from infrastructure, brokers, or framework packages.
4. Every external boundary has exactly ONE seam class.
5. No hollow delegation layers. Every class must answer: "what would be lost if I deleted this?"
6. All dataclasses are frozen=True. Domain objects are immutable.
7. Every public method has a type annotation. No bare dicts as return types.

For this module, produce in this order:
STEP 1: The interface/port (if applicable) — the contract this module satisfies.
STEP 2: The tests — write all unit tests as failing stubs.
STEP 3: The implementation — make each test pass in turn.
STEP 4: The integration test — show this module working with the previous module.
STEP 5: The documentation — a single docstring per class stating its ONE responsibility.

Do not proceed to the next step until the current step is complete.
Do not build what the next module will build.
Ask for clarification if the module boundary is unclear.
```

---

## BUILD PHASES & TIMELINE

| Phase | Modules | Duration | Milestone |
|-------|---------|----------|-----------|
| Foundation | 1 (Domain Core) | Day 1 | All domain types tested |
| Broker | 2 (Broker Gateway) | Days 2-3 | Place/cancel order live on paper account |
| Data | 3 (Market Data Pipeline) | Days 3-4 | Live ticks flowing, OHLCV building correctly |
| Execution | 4-5 (OMS + Risk) | Days 5-6 | Paper trade executes with pre-trade risk gate |
| Intelligence | 6 (Signal + Gate FSM) | Days 7-8 | Gate 03 correctly blocking on CVD divergence |
| Strategy | 7 (Strategy Executor) | Day 9 | Full Valentini AMT signal-to-order live on paper |
| Simulation | 8 (Backtester + Replay) | Days 10-11 | Backtest run on 30 days NSE data |
| Portfolio | 9 (Portfolio + Analytics) | Day 12 | Per-strategy PnL with drawdown series |
| Scanner | 10 (Scanner) | Day 13 | 09:45 IST scanner selecting ATM strikes |
| API | 11 (FastAPI + WS) | Day 14 | All data streaming to frontend |
| Frontend | 12 (Terminal UI) | Days 15-18 | Bloomberg-style terminal live |

---

## NON-NEGOTIABLE ARCHITECTURAL RULES

1. **Float is forbidden for financial data.** `Decimal` for prices, PnL, quantities in rupees. `int` for quantities in paise. A float PnL is a bug waiting to compound.

2. **Domain is the centre of the universe.** Nothing in `domain/` imports from `brokers/`, `api/`, `market_data/`, or any framework. The domain speaks only to itself.

3. **One seam per boundary.** The broker boundary has ONE seam class (the Gateway). The database boundary has ONE seam class (the Repository). Never split a seam across a shim + mapper + adapter.

4. **Tests are not optional.** Every module starts with failing tests. Code exists to make tests pass.

5. **The 3-loss rule is a hard system halt.** It is not a warning. It is not a suggestion. After 3 consecutive losses, `square_off_all()` is called and new orders are blocked until manual reset.

6. **IST-aware square-off is a safety-critical timer.** Missing it means overnight risk on an intraday position. It runs independently of strategy logic.

7. **Backtest and live share the same strategy code.** There is no `BacktestStrategy` class. There is only `Strategy`. The data source differs. The logic does not.

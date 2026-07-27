from __future__ import annotations

import asyncio
import os
import json
import logging
import random
from contextlib import suppress
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from scalpr.domain.tick import Tick
from scalpr.domain.events import (
    DomainEvent,
    TickReceived,
    OrderPlaced,
    FillReceived,
    OrderCancelled,
    OrderRejected,
    PositionOpened,
    PositionClosed,
    SignalGenerated,
    CircuitBreakerTripped,
    RiskCheckFailed,
    SessionHalted,
    PositionUpdated,
    InMemoryEventBus,
)
from scalpr.brokers.dhan.gateway import DhanGateway
from scalpr.risk.pre_trade import PreTradeRiskGate
from scalpr.risk.circuit_breaker import CircuitBreaker
from scalpr.execution.order_router import OrderRouter
from scalpr.brokers.dhan.ws_manager import DhanWebSocketManager
from scalpr.strategy.executor import StrategyExecutor
from scalpr.strategy.scalpr_amt import ScalprAmtStrategy
from scalpr.observability import setup_logging, TraceContext
from scalpr.observability.metrics import metrics as global_metrics
from scalpr.observability.event_store import EventStore
from scalpr.simulation.replay_engine import ReplayEngine
from scalpr.oms.persistence import OmsRepository
from scalpr.oms.order_manager import OrderManager
from config.secrets_manager import SecretsManager

logger = logging.getLogger(__name__)

# Environment configuration
SCALPR_ENV = os.getenv("SCALPR_ENV", "development")

app = FastAPI(title="SCALPR Quantitative Trading API")

# Configure CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Live Dhan Configuration - Centralized via SecretsManager
secrets = SecretsManager()
CLIENT_ID = secrets.get_dhan_client_id()
ACCESS_TOKEN = secrets.get_dhan_access_token()

# Global Broker Gateway
broker_gateway = DhanGateway(config={"client_id": CLIENT_ID, "access_token": ACCESS_TOKEN})



# Global Market Feed (production-ready WebSocket manager)
dhan_feed = DhanWebSocketManager(access_token=ACCESS_TOKEN, client_id=CLIENT_ID)

# Global Strategy Executor
strategy_executor = StrategyExecutor()


risk_gate = PreTradeRiskGate()
circuit_breaker = CircuitBreaker()

# Initialize event bus for domain event publishing
event_bus = InMemoryEventBus()

# Initialize OMS persistence (crash recovery)
oms_db_path = os.getenv("OMS_DB_PATH", "data/oms.db")
oms_repo = OmsRepository(oms_db_path)
order_manager = OrderManager(repository=oms_repo)

# Initialize EventStore for replay and audit trail
event_store = EventStore(db_path=os.getenv("EVENT_DB_PATH", "data/events.db"))

# Initialize ReplayEngine with async strategy executor
replay_engine = ReplayEngine(executor=strategy_executor, speed_multiplier=1.0)

# Add audit logging subscribers for critical events
def _on_tick_received(event: TickReceived) -> None:
    """Log tick receipt for audit trail."""
    logger.debug(
        f"[EVENT] TickReceived: {event.tick.symbol} LTP={event.tick.ltp} "
        f"volume={event.tick.cumulative_volume}"
    )

def _on_order_placed(event: OrderPlaced) -> None:
    """Log order placement for audit trail."""
    logger.info(
        f"[EVENT] OrderPlaced: {event.order.symbol} {event.order.side.value} "
        f"qty={event.order.quantity} price={event.order.price} "
        f"order_id={event.order.order_id}"
    )

def _on_fill_received(event: FillReceived) -> None:
    """Log fill execution for audit trail."""
    logger.info(
        f"[EVENT] FillReceived: {event.fill.symbol} {event.fill.side.value} "
        f"qty={event.fill.quantity} price={event.fill.price} "
        f"fill_id={event.fill.fill_id}"
    )

def _on_position_updated(event: PositionUpdated) -> None:
    """Log position changes for audit trail."""
    logger.info(
        f"[EVENT] PositionUpdated: {event.position.symbol} "
        f"qty: {event.previous_quantity} → {event.position.quantity} "
        f"avg_price={event.position.avg_price}"
    )

# Register event subscribers
event_bus.subscribe(TickReceived, _on_tick_received)
event_bus.subscribe(OrderPlaced, _on_order_placed)
event_bus.subscribe(FillReceived, _on_fill_received)
event_bus.subscribe(PositionUpdated, _on_position_updated)

# WebSocket Order Event Broadcasters (async)
def _ws_on_order_placed_sync(event: OrderPlaced) -> None:
    """Sync wrapper for async WebSocket broadcast of OrderPlaced events."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_ws_broadcast_order_placed(event))
    except RuntimeError:
        logger.warning("No running event loop — skipping WS broadcast for OrderPlaced")

async def _ws_broadcast_order_placed(event: OrderPlaced) -> None:
    """Broadcast OrderPlaced event to all connected WebSocket clients."""
    msg = {
        "type": "order_placed",
        "order": {
            "order_id": event.order.order_id,
            "symbol": event.order.symbol,
            "side": event.order.side.name,
            "quantity": event.order.quantity,
            "price": str(event.order.price),
            "state": event.order.state.name,
        },
    }
    await manager.broadcast_to_all(msg)

def _ws_on_fill_received_sync(event: FillReceived) -> None:
    """Sync wrapper for async WebSocket broadcast of FillReceived events."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_ws_broadcast_fill_received(event))
    except RuntimeError:
        logger.warning("No running event loop — skipping WS broadcast for FillReceived")

async def _ws_broadcast_fill_received(event: FillReceived) -> None:
    """Broadcast FillReceived event to all connected WebSocket clients."""
    msg = {
        "type": "fill_received",
        "fill": {
            "fill_id": event.fill.fill_id,
            "order_id": event.fill.order_id,
            "symbol": event.fill.symbol,
            "side": event.fill.side.name,
            "quantity": event.fill.quantity,
            "price": str(event.fill.price),
        },
    }
    await manager.broadcast_to_all(msg)

# Register async WS broadcasters
event_bus.subscribe(OrderPlaced, _ws_on_order_placed_sync)
event_bus.subscribe(FillReceived, _ws_on_fill_received_sync)

# Initialize order router (enforces risk checks on all orders)
order_router = OrderRouter(
    gateway=broker_gateway,
    risk_gate=risk_gate,
    circuit_breaker=circuit_breaker,
    event_bus=event_bus,
    order_manager=order_manager,
)

# Register strategies for default watchlists
strategies = {
    "RELIANCE": ScalprAmtStrategy(order_router, "RELIANCE"),
    "TCS": ScalprAmtStrategy(order_router, "TCS"),
    "INFY": ScalprAmtStrategy(order_router, "INFY"),
    "SBIN": ScalprAmtStrategy(order_router, "SBIN"),
}
for strat in strategies.values():
    strategy_executor.register_strategy(strat)

# Event persistence subscriber (wired to event bus)
def _persist_event_to_store(event: Any) -> None:
    """Persist domain events to EventStore for replay and audit."""
    try:
        session_id = TraceContext.get_trace_id() or "default"
        event_store.append(event, session_id=session_id)
    except Exception as e:
        # Persistence should never break the main flow
        logger.warning(f"Failed to persist event to store: {e}")

# Subscribe event bus to EventStore for key events
for event_type in (
    OrderPlaced, FillReceived, OrderCancelled, OrderRejected,
    PositionOpened, PositionClosed, TickReceived, SignalGenerated,
    CircuitBreakerTripped, RiskCheckFailed, SessionHalted,
):
    event_bus.subscribe(event_type, _persist_event_to_store)

# --- In-memory ring buffers for observability endpoints ---
from collections import deque

MAX_SIGNAL_HISTORY = 50
MAX_RISK_EVENT_HISTORY = 50

_recent_signals: deque[dict] = deque(maxlen=MAX_SIGNAL_HISTORY)
_recent_risk_events: deque[dict] = deque(maxlen=MAX_RISK_EVENT_HISTORY)


def _capture_signal_generated(event: SignalGenerated) -> None:
    """Capture SignalGenerated events for the /strategy/signals endpoint."""
    try:
        _recent_signals.append({
            "symbol": event.signal.symbol,
            "signal_type": event.signal.signal_type.value,
            "price": float(event.signal.price),
            "timestamp": event.signal.timestamp.isoformat(),
            "gate_results": event.gate_results,
        })
    except Exception as exc:
        logger.warning(f"Failed to capture signal event: {exc}")


def _capture_circuit_breaker(event: CircuitBreakerTripped) -> None:
    """Capture CircuitBreakerTripped events for risk monitoring."""
    try:
        _recent_risk_events.append({
            "component": event.component,
            "reason": event.reason,
            "threshold": event.threshold,
            "current_value": event.current_value,
            "timestamp": event.timestamp.isoformat(),
        })
    except Exception as exc:
        logger.warning(f"Failed to capture circuit breaker event: {exc}")


def _capture_risk_check_failed(event: RiskCheckFailed) -> None:
    """Capture RiskCheckFailed events."""
    try:
        _recent_risk_events.append({
            "event_type": "RiskCheckFailed",
            "check_name": event.check_name,
            "timestamp": event.timestamp.isoformat(),
        })
    except Exception as exc:
        logger.warning(f"Failed to capture risk check event: {exc}")


def _capture_session_halted(event: SessionHalted) -> None:
    """Capture SessionHalted events."""
    try:
        _recent_risk_events.append({
            "event_type": "SessionHalted",
            "reason": event.reason,
            "halted_by": event.halted_by,
            "timestamp": event.timestamp.isoformat(),
        })
    except Exception as exc:
        logger.warning(f"Failed to capture session halt event: {exc}")


# Register ring buffer subscribers
event_bus.subscribe(SignalGenerated, _capture_signal_generated)
event_bus.subscribe(CircuitBreakerTripped, _capture_circuit_breaker)
event_bus.subscribe(RiskCheckFailed, _capture_risk_check_failed)
event_bus.subscribe(SessionHalted, _capture_session_halted)
# Seeded list of Nifty 50 symbols for search
SYMBOLS_DB = [
    {"symbol": "RELIANCE", "name": "Reliance Industries Ltd", "exchange": "NSE", "segment": "EQ", "isin": "INE002A01018", "lotSize": 1, "tickSize": 0.05, "sector": "OilGas"},
    {"symbol": "TCS", "name": "Tata Consultancy Services Ltd", "exchange": "NSE", "segment": "EQ", "isin": "INE467B01029", "lotSize": 1, "tickSize": 0.05, "sector": "IT"},
    {"symbol": "HDFCBANK", "name": "HDFC Bank Ltd", "exchange": "NSE", "segment": "EQ", "isin": "INE040A01034", "lotSize": 1, "tickSize": 0.05, "sector": "Finance"},
    {"symbol": "INFY", "name": "Infosys Ltd", "exchange": "NSE", "segment": "EQ", "isin": "INE009A01021", "lotSize": 1, "tickSize": 0.05, "sector": "IT"},
    {"symbol": "ICICIBANK", "name": "ICICI Bank Ltd", "exchange": "NSE", "segment": "EQ", "isin": "INE090A01021", "lotSize": 1, "tickSize": 0.05, "sector": "Finance"},
    {"symbol": "SBIN", "name": "State Bank of India", "exchange": "NSE", "segment": "EQ", "isin": "INE062A01020", "lotSize": 1, "tickSize": 0.05, "sector": "Finance"},
    {"symbol": "BHARTIARTL", "name": "Bharti Airtel Ltd", "exchange": "NSE", "segment": "EQ", "isin": "INE397D01024", "lotSize": 1, "tickSize": 0.05, "sector": "Telecom"},
    {"symbol": "KOTAKBANK", "name": "Kotak Mahindra Bank Ltd", "exchange": "NSE", "segment": "EQ", "isin": "INE237A01028", "lotSize": 1, "tickSize": 0.05, "sector": "Finance"},
    {"symbol": "LT", "name": "Larsen & Toubro Ltd", "exchange": "NSE", "segment": "EQ", "isin": "INE018A01030", "lotSize": 1, "tickSize": 0.05, "sector": "CapitalGoods"},
    {"symbol": "AXISBANK", "name": "Axis Bank Ltd", "exchange": "NSE", "segment": "EQ", "isin": "INE238A01034", "lotSize": 1, "tickSize": 0.05, "sector": "Finance"},
    {"symbol": "ITC", "name": "ITC Ltd", "exchange": "NSE", "segment": "EQ", "isin": "INE154A01025", "lotSize": 1, "tickSize": 0.05, "sector": "FMCG"},
    {"symbol": "TATAMOTORS", "name": "Tata Motors Ltd", "exchange": "NSE", "segment": "EQ", "isin": "INE155A01022", "lotSize": 1, "tickSize": 0.05, "sector": "Auto"},
    {"symbol": "MARUTI", "name": "Maruti Suzuki India Ltd", "exchange": "NSE", "segment": "EQ", "isin": "INE585B01010", "lotSize": 1, "tickSize": 0.05, "sector": "Auto"},
    {"symbol": "WIPRO", "name": "Wipro Ltd", "exchange": "NSE", "segment": "EQ", "isin": "INE075A01022", "lotSize": 1, "tickSize": 0.05, "sector": "IT"},
    {"symbol": "HCLTECH", "name": "HCL Technologies Ltd", "exchange": "NSE", "segment": "EQ", "isin": "INE860A01027", "lotSize": 1, "tickSize": 0.05, "sector": "IT"},
    {"symbol": "SUNPHARMA", "name": "Sun Pharmaceutical Industries", "exchange": "NSE", "segment": "EQ", "isin": "INE044A01036", "lotSize": 1, "tickSize": 0.05, "sector": "Pharma"},
    {"symbol": "TITAN", "name": "Titan Company Ltd", "exchange": "NSE", "segment": "EQ", "isin": "INE280A01028", "lotSize": 1, "tickSize": 0.05, "sector": "ConsumerDur"},
]

# Track active replay sessions
REPLAY_SESSIONS: dict[str, dict[str, Any]] = {}

# Map symbol -> current simulated price
CURRENT_PRICES: dict[str, Decimal] = {
    "RELIANCE": Decimal("2935.40"),
    "TCS": Decimal("4080.50"),
    "HDFCBANK": Decimal("1670.20"),
    "INFY": Decimal("1847.30"),
    "ICICIBANK": Decimal("1290.50"),
    "SBIN": Decimal("825.00"),
    "BHARTIARTL": Decimal("1610.20"),
    "KOTAKBANK": Decimal("1750.00"),
    "LT": Decimal("3680.00"),
    "AXISBANK": Decimal("1175.00"),
    "ITC": Decimal("480.00"),
    "TATAMOTORS": Decimal("950.00"),
    "MARUTI": Decimal("12450.00"),
    "WIPRO": Decimal("530.00"),
    "HCLTECH": Decimal("1800.00"),
    "SUNPHARMA": Decimal("1820.00"),
    "TITAN": Decimal("3640.00"),
}

# Map symbol -> daily stats for generating quotes
DAILY_STATS: dict[str, dict[str, Any]] = {
    "RELIANCE": {"open": Decimal("2930.00"), "high": Decimal("2955.00"), "low": Decimal("2920.00"), "prevClose": Decimal("2930.00"), "volume": 1250000},
    "TCS": {"open": Decimal("4070.00"), "high": Decimal("4110.00"), "low": Decimal("4060.00"), "prevClose": Decimal("4075.00"), "volume": 850000},
    "HDFCBANK": {"open": Decimal("1665.00"), "high": Decimal("1680.00"), "low": Decimal("1660.00"), "prevClose": Decimal("1668.00"), "volume": 2500000},
    "INFY": {"open": Decimal("1840.00"), "high": Decimal("1860.00"), "low": Decimal("1835.00"), "prevClose": Decimal("1845.00"), "volume": 1100000},
    "ICICIBANK": {"open": Decimal("1285.00"), "high": Decimal("1298.00"), "low": Decimal("1280.00"), "prevClose": Decimal("1288.00"), "volume": 1500000},
    "SBIN": {"open": Decimal("820.00"), "high": Decimal("832.00"), "low": Decimal("818.00"), "prevClose": Decimal("822.00"), "volume": 3200000},
    "BHARTIARTL": {"open": Decimal("1600.00"), "high": Decimal("1620.00"), "low": Decimal("1595.00"), "prevClose": Decimal("1605.00"), "volume": 1400000},
    "KOTAKBANK": {"open": Decimal("1740.00"), "high": Decimal("1765.00"), "low": Decimal("1735.00"), "prevClose": Decimal("1745.00"), "volume": 900000},
    "LT": {"open": Decimal("3660.00"), "high": Decimal("3700.00"), "low": Decimal("3650.00"), "prevClose": Decimal("3670.00"), "volume": 750000},
    "AXISBANK": {"open": Decimal("1170.00"), "high": Decimal("1185.00"), "low": Decimal("1165.00"), "prevClose": Decimal("1172.00"), "volume": 1800000},
    "ITC": {"open": Decimal("478.00"), "high": Decimal("484.00"), "low": Decimal("476.00"), "prevClose": Decimal("479.00"), "volume": 5500000},
    "TATAMOTORS": {"open": Decimal("945.00"), "high": Decimal("960.00"), "low": Decimal("940.00"), "prevClose": Decimal("948.00"), "volume": 2800000},
    "MARUTI": {"open": Decimal("12400.00"), "high": Decimal("12550.00"), "low": Decimal("12350.00"), "prevClose": Decimal("12420.00"), "volume": 350000},
    "WIPRO": {"open": Decimal("528.00"), "high": Decimal("535.00"), "low": Decimal("525.00"), "prevClose": Decimal("529.00"), "volume": 2100000},
    "HCLTECH": {"open": Decimal("1790.00"), "high": Decimal("1815.00"), "low": Decimal("1785.00"), "prevClose": Decimal("1795.00"), "volume": 1200000},
    "SUNPHARMA": {"open": Decimal("1810.00"), "high": Decimal("1835.00"), "low": Decimal("1805.00"), "prevClose": Decimal("1815.00"), "volume": 800000},
    "TITAN": {"open": Decimal("3620.00"), "high": Decimal("3665.00"), "low": Decimal("3610.00"), "prevClose": Decimal("3630.00"), "volume": 600000},
}

# Async lock for shared state protection
shared_state_lock = asyncio.Lock()

def hash_string(s: str) -> int:
    h = 2166136261
    for char in s:
        h = ((h ^ ord(char)) * 16777619) & 0xFFFFFFFF
    return h


async def generate_mock_candles(symbol: str, timeframe: str, limit: int, end_time: datetime) -> list[dict[str, Any]]:
    """Generate realistic mock candles based on a deterministic symbol seed."""
    async with shared_state_lock:
        base = float(CURRENT_PRICES.get(symbol, Decimal("500.00")))

    tf_ms = {
        "1m": 60, "3m": 180, "5m": 300, "15m": 900, "30m": 1800,
        "1h": 3600, "4h": 14400, "1d": 86400, "1w": 604800
    }
    ms = tf_ms.get(timeframe, 60)

    rng = random.Random(hash_string(symbol))  # noqa: S311

    candles = []
    price = base * 0.95
    start_t = int(end_time.timestamp()) - limit * ms

    for i in range(limit):
        o = price
        drift = (base - price) * 0.02
        c = o + drift + (rng.random() - 0.5) * base * 0.005
        h = max(o, c) + rng.random() * base * 0.003
        low_val = min(o, c) - rng.random() * base * 0.003
        v = int(rng.random() * 50000) + 1000

        price = c
        candles.append({
            "t": (start_t + i * ms) * 1000,
            "o": round(o, 2),
            "h": round(h, 2),
            "l": round(low_val, 2),
            "c": round(c, 2),
            "v": v
        })
    return candles


def get_quote_data(symbol: str) -> dict[str, Any]:
    """Retrieve quote structure for a given symbol."""
    ltp = CURRENT_PRICES.get(symbol, Decimal("500.00"))
    stats = DAILY_STATS.get(symbol, {"open": ltp * Decimal("0.99"), "high": ltp * Decimal("1.01"), "low": ltp * Decimal("0.98"), "prevClose": ltp, "volume": 100000})

    open_val = stats["open"]
    high_val = stats["high"]
    low_val = stats["low"]
    prev_close = stats["prevClose"]
    volume = stats["volume"]

    # Update high/low based on ltp
    if ltp > high_val:
        stats["high"] = ltp
        high_val = ltp
    if ltp < low_val:
        stats["low"] = ltp
        low_val = ltp

    change = ltp - prev_close
    change_pct = (change / prev_close) * Decimal("100") if prev_close else Decimal("0")

    return {
        "symbol": symbol,
        "exchange": "NSE",
        "ltp": float(ltp),
        "open": float(open_val),
        "high": float(high_val),
        "low": float(low_val),
        "prevClose": float(prev_close),
        "change": float(change),
        "changePct": float(change_pct),
        "volume": volume,
        "bid": float(ltp - Decimal("0.05")),
        "ask": float(ltp + Decimal("0.05")),
        "bidQty": 100,
        "askQty": 120,
        "ts": int(datetime.utcnow().timestamp() * 1000)
    }


class ConnectionManager:
    """Manages active WebSockets connections and broadcasts streaming messages."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []
        self.subscriptions: dict[WebSocket, set[str]] = {}

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)
        self.subscriptions[websocket] = set()

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if websocket in self.subscriptions:
            del self.subscriptions[websocket]

    def subscribe(self, websocket: WebSocket, symbols: list[str]) -> None:
        if websocket in self.subscriptions:
            for symbol in symbols:
                self.subscriptions[websocket].add(symbol.upper())

    def unsubscribe(self, websocket: WebSocket, symbols: list[str]) -> None:
        if websocket in self.subscriptions:
            for symbol in symbols:
                self.subscriptions[websocket].discard(symbol.upper())

    async def broadcast_to_subscribers(self, symbol: str, message: dict[str, Any]) -> None:
        serialized_msg = json.dumps(message, default=lambda x: str(x) if isinstance(x, Decimal) else x)
        for connection in self.active_connections:
            subs = self.subscriptions.get(connection, set())
            if symbol.upper() in subs:
                try:
                    await connection.send_text(serialized_msg)
                except Exception as exc:
                    logger.debug("Failed to send WS message: %s", exc)

    async def broadcast_to_all(self, message: dict[str, Any]) -> None:
        """Broadcast a message to ALL connected WebSocket clients."""
        serialized_msg = json.dumps(message, default=lambda x: str(x) if isinstance(x, Decimal) else x)
        for connection in self.active_connections:
            try:
                await connection.send_text(serialized_msg)
            except Exception as exc:
                logger.debug("Failed to send WS message: %s", exc)


manager = ConnectionManager()


def feed_on_tick_callback(tick: Tick) -> None:
    # Start trace context for this tick
    trace_ctx = TraceContext.start(tick.symbol)
    
    # Publish TickReceived event with trace_id
    tick_event = TickReceived(
        timestamp=datetime.now(timezone.utc),
        tick=tick,
    )
    tick_event.trace_id = trace_ctx.trace_id
    event_bus.publish(tick_event)
    
    # Increment metrics
    global_metrics.get_counter("strategy_ticks").increment()
    
    # Schedule async update with lock protection
    async def _update_and_broadcast():
        import time
        start_time = time.time()
        
        async with shared_state_lock:
            CURRENT_PRICES[tick.symbol] = tick.ltp
        
        # Route to registered strategies (outside lock to avoid holding it during execution)
        strategy_executor.on_tick(tick)
        
        # Broadcast to websocket with lock protection for get_quote_data
        async with shared_state_lock:
            quote_data = get_quote_data(tick.symbol)
        await manager.broadcast_to_subscribers(tick.symbol, quote_data)
        
        # Record latency
        latency_ms = (time.time() - start_time) * 1000
        global_metrics.get_histogram("tick_processing_latency_ms").observe(latency_ms)
    
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_update_and_broadcast())
    except RuntimeError:
        pass

dhan_feed.on_tick(feed_on_tick_callback)

async def tick_simulation_loop() -> None:
    """Generates synthetic ticks for development — bypasses the real feed."""
    while True:
        try:
            async with shared_state_lock:
                symbols_to_process = list(CURRENT_PRICES.keys())
            
            for symbol in symbols_to_process:
                async with shared_state_lock:
                    old_price = float(CURRENT_PRICES[symbol])
                
                change = random.uniform(-0.001, 0.001) * old_price  # noqa: S311
                new_price = round(old_price + change, 2)

                tick = Tick(
                    symbol=symbol,
                    ltp=Decimal(str(new_price)),
                    bid=Decimal(str(new_price - 0.05)),
                    ask=Decimal(str(new_price + 0.05)),
                    delta_volume=random.randint(10, 500),  # noqa: S311
                    cumulative_volume=random.randint(1000, 50000),  # noqa: S311
                    exchange_timestamp=datetime.now(timezone.utc),
                )
                
                # Call the same callback that real feed uses — keeps pipeline intact
                feed_on_tick_callback(tick)

            await asyncio.sleep(1.0)
        except asyncio.CancelledError:
            break
        except Exception:
            logger.exception("Error in tick simulation loop")
            await asyncio.sleep(1.0)


background_tasks: set[asyncio.Task[Any]] = set()


@app.on_event("startup")
async def startup_event() -> None:
    # Initialize observability
    setup_logging(environment=SCALPR_ENV)
    logger.info(f"Observability initialized (environment={SCALPR_ENV})")
    
    # Restore OMS state from persistence (crash recovery)
    try:
        order_manager.restore_state()
        logger.info(f"OMS state restored from {oms_db_path}")
    except Exception as e:
        logger.warning(f"Failed to restore OMS state: {e}")
    
    dhan_feed.connect()
    
    # Subscribe to all tracked symbols for real-time ticks
    tracked_symbols = list(CURRENT_PRICES.keys())
    dhan_feed.subscribe(tracked_symbols)
    logger.info(f"Subscribed to {len(tracked_symbols)} symbols: {tracked_symbols}")
    
    # Start synthetic tick simulation ONLY in development mode
    if SCALPR_ENV != "production":
        logger.info("Starting synthetic tick simulation (development mode)")
        task = asyncio.create_task(tick_simulation_loop())
        background_tasks.add(task)
        task.add_done_callback(background_tasks.discard)
    else:
        logger.info("Production mode: synthetic tick simulation disabled")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Gracefully disconnect market feed on application shutdown."""
    logger.info("Shutting down market feed...")
    dhan_feed.disconnect()
    logger.info("Market feed disconnected")


@app.get("/api/v1/health")
@app.get("/healthz")
def health_check() -> dict[str, str]:
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.get("/metrics")
async def get_metrics():
    """Prometheus-style metrics endpoint for production monitoring."""
    return global_metrics.snapshot()


# ===================================================================
# OBSERVABILITY & HEALTH ENDPOINTS
# ===================================================================

@app.get("/api/v1/strategy/status")
def get_strategy_status() -> dict:
    """Return active strategies and their current state."""
    try:
        strategies_info = strategy_executor.get_strategy_info()
    except AttributeError:
        strategies_info = []
    return {"strategies": strategies_info, "total": len(strategies_info), "timestamp": datetime.utcnow().isoformat()}


@app.get("/api/v1/strategy/gates")
def get_strategy_gates() -> dict:
    """Return last known Gate FSM evaluation per symbol."""
    latest_gates_by_symbol: dict[str, dict] = {}
    for sig in reversed(_recent_signals):
        symbol = sig.get("symbol")
        if symbol and symbol not in latest_gates_by_symbol:
            latest_gates_by_symbol[symbol] = {
                "signal_type": sig.get("signal_type"),
                "price": sig.get("price"),
                "timestamp": sig.get("timestamp"),
                "gate_results": sig.get("gate_results", {}),
            }
    return {"symbols": latest_gates_by_symbol, "timestamp": datetime.utcnow().isoformat()}


@app.get("/api/v1/strategy/signals")
def get_strategy_signals(limit: int = 50) -> dict:
    """Return recent trading signals, bounded to last N (default 50)."""
    safe_limit = min(max(1, limit), 50)
    signals = list(_recent_signals)[-safe_limit:]
    return {"signals": signals, "total_available": len(_recent_signals), "returned": len(signals), "timestamp": datetime.utcnow().isoformat()}


@app.get("/api/v1/risk/session")
def get_risk_session() -> dict:
    """Return session risk state: circuit breaker status, halt state."""
    try:
        cb_state = circuit_breaker.state
    except AttributeError:
        cb_state = {"halted": False, "is_tripped": False, "tripped_reason": None}
    return {"circuit_breaker": cb_state, "recent_risk_events": list(_recent_risk_events)[-20:], "timestamp": datetime.utcnow().isoformat()}


@app.get("/api/v1/risk/limits")
def get_risk_limits() -> dict:
    """Return current Risk limit configuration."""
    return {
        "portfolio_value": float(risk_gate.portfolio_value),
        "max_open_positions": risk_gate.max_open_positions,
        "max_concentration_pct": float(risk_gate.max_concentration),
        "max_capital_risk_pct": float(risk_gate.max_capital_risk),
        "circuit_breaker": {
            "daily_loss_limit_pct": float(circuit_breaker.daily_loss_limit_pct),
            "drawdown_limit_pct": float(circuit_breaker.drawdown_limit_pct),
        },
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/api/v1/health/dhan")
async def get_health_dhan() -> dict:
    """Dhan connection health — actual connectivity check."""
    if hasattr(dhan_feed, "get_health_status"):
        health = dhan_feed.get_health_status()
    else:
        health = {"connected": False}
    
    connected = health.get("connected", False)
    overall = "healthy" if connected else "disconnected"
    
    return {
        "status": overall, "connected": connected,
        "active_subscriptions": health.get("active_subscriptions", 0),
        "last_message_at": health.get("last_message_at"),
        "reconnect_count": health.get("reconnect_count", 0),
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/api/v1/symbols/search")
def search_symbols(q: str = "", limit: int = 25) -> dict[str, Any]:
    needle = q.strip().upper()
    if not needle:
        return {"results": SYMBOLS_DB[:limit]}

    filtered = [
        s for s in SYMBOLS_DB
        if needle in s["symbol"] or needle in s["name"].upper()
    ]
    return {"results": filtered[:limit]}


@app.get("/api/v1/market/quote/{symbol}")
async def get_quote(symbol: str) -> dict[str, Any]:
    sym = symbol.upper()
    async with shared_state_lock:
        if sym not in CURRENT_PRICES:
            raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")
        quote_data = get_quote_data(sym)
    return quote_data


@app.get("/api/v1/market/candles")
async def get_candles(
    symbol: str,
    timeframe: str,
    limit: int = 200,
    exchange: str = "NSE",
) -> dict[str, Any]:
    """Fetch historical OHLCV candles from Dhan (real data, no mocks)."""
    sym = symbol.upper()
    exch = exchange.upper()
    
    if limit <= 0 or limit > 2000:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 2000")
    
    # Map frontend timeframe to Dhan timeframe
    tf_map = {"1h": "1H", "4h": "4H", "1d": "1D", "1w": "1W"}
    dhan_timeframe = tf_map.get(timeframe, timeframe)
    
    from scalpr.brokers.dhan.historical import _VALID_TIMEFRAMES
    if dhan_timeframe not in _VALID_TIMEFRAMES:
        raise HTTPException(status_code=400, detail=f"Invalid timeframe: {timeframe}")
    
    try:
        if not broker_gateway.is_connected():
            broker_gateway.connect()
        
        candles_raw = broker_gateway.connection.historical.get_ohlcv_latest(
            symbol=sym, exchange=exch, timeframe=dhan_timeframe, count=limit,
        )
        
        candles = []
        for c in candles_raw:
            ts = c["timestamp"]
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            else:
                ts = ts.astimezone(timezone.utc)
            
            candles.append({
                "t": int(ts.timestamp() * 1000),
                "o": float(c["open"]),
                "h": float(c["high"]),
                "l": float(c["low"]),
                "c": float(c["close"]),
                "v": int(c["volume"]),
            })
        
        return {"symbol": sym, "exchange": exch, "timeframe": timeframe, "candles": candles}
    
    except Exception as exc:
        logger.warning(f"candles_fallback_empty: symbol={sym} timeframe={timeframe} error={exc}")
        return {"symbol": sym, "exchange": exch, "timeframe": timeframe, "candles": []}


@app.get("/api/v1/market/depth/{symbol}")
async def get_market_depth(symbol: str, exchange: str = "NSE") -> dict[str, Any]:
    """Get Level 2 order book (top 5 bid/ask levels) from Dhan."""
    sym = symbol.upper()
    exch = exchange.upper()
    
    if exch not in ("NSE", "BSE", "MCX", "NFO", "MCX-SX"):
        raise HTTPException(status_code=400, detail=f"Unsupported exchange: {exchange}")
    
    try:
        if not broker_gateway.is_connected():
            broker_gateway.connect()
        
        raw_depth = broker_gateway.connection.market_data.get_depth(sym, exch)
        bids = raw_depth.get("bids", [])
        asks = raw_depth.get("asks", [])
        
        best_bid = float(bids[0]["price"]) if bids else 0.0
        best_ask = float(asks[0]["price"]) if asks else 0.0
        spread = best_ask - best_bid if best_bid and best_ask else 0.0
        
        return {
            "symbol": sym, "exchange": exch,
            "spread": spread,
            "bids": [{"price": float(b["price"]), "bidSize": int(b["quantity"]), "bidOrders": int(b.get("orders", 0))} for b in bids],
            "asks": [{"price": float(a["price"]), "askSize": int(a["quantity"]), "askOrders": int(a.get("orders", 0))} for a in asks],
            "ts": int(datetime.now(timezone.utc).timestamp() * 1000),
        }
    
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Dhan market depth error: {exc}")


@app.get("/api/v1/market/historical/{symbol}")
async def get_historical(
    symbol: str,
    exchange: str = "NSE",
    timeframe: str = "1D",
    from_date: str = "",
    to_date: str = "",
    limit: int = 200,
) -> dict[str, Any]:
    """Fetch historical OHLCV for a specific date range from Dhan."""
    sym = symbol.upper()
    exch = exchange.upper()
    
    tf_map = {"1h": "1H", "4h": "4H", "1d": "1D", "1w": "1W"}
    dhan_timeframe = tf_map.get(timeframe, timeframe)
    
    from scalpr.brokers.dhan.historical import _VALID_TIMEFRAMES
    if dhan_timeframe not in _VALID_TIMEFRAMES:
        raise HTTPException(status_code=400, detail=f"Invalid timeframe: {timeframe}")
    
    from datetime import date
    try:
        parsed_from = date.fromisoformat(from_date) if from_date else date.today() - timedelta(days=90)
        parsed_to = date.fromisoformat(to_date) if to_date else date.today()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid date format (YYYY-MM-DD): {exc}")
    
    if parsed_from > parsed_to:
        raise HTTPException(status_code=400, detail="from_date must be <= to_date")
    if (parsed_to - parsed_from).days > 365:
        raise HTTPException(status_code=400, detail="Date range cannot exceed 365 days")
    
    try:
        if not broker_gateway.is_connected():
            broker_gateway.connect()
        
        candles_raw = broker_gateway.connection.historical.get_ohlcv(
            symbol=sym, exchange=exch, timeframe=dhan_timeframe,
            from_date=parsed_from, to_date=parsed_to,
        )
        
        candles_raw = candles_raw[-limit:] if len(candles_raw) > limit else candles_raw
        
        candles = []
        for c in candles_raw:
            ts = c["timestamp"]
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            candles.append({
                "t": int(ts.timestamp() * 1000), "o": float(c["open"]),
                "h": float(c["high"]), "l": float(c["low"]),
                "c": float(c["close"]), "v": int(c["volume"]),
            })
        
        return {"symbol": sym, "exchange": exch, "timeframe": timeframe, "candles": candles}
    
    except Exception as exc:
        return {"symbol": sym, "exchange": exch, "timeframe": timeframe, "candles": []}


@app.get("/api/v1/replay/sessions")
async def get_replay_sessions(symbol: str = "", date: str = "") -> dict[str, Any]:
    async with shared_state_lock:
        sessions = []
        for s in REPLAY_SESSIONS.values():
            if symbol and s["symbol"].upper() != symbol.upper():
                continue
            sessions.append(s)
    return {"sessions": sessions}


@app.get("/api/v1/events/stats")
async def get_event_stats(session_id: str = "default") -> dict[str, Any]:
    """Get event statistics for a session."""
    try:
        event_count = event_store.get_event_count(session_id)
        latest_seq = event_store.get_latest_sequence(session_id)
        
        return {
            "session_id": session_id,
            "total_events": event_count,
            "latest_sequence": latest_seq,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get event stats: {e}")


@app.delete("/api/v1/events/{session_id}")
async def delete_session_events(session_id: str) -> dict[str, Any]:
    """Delete all events for a session."""
    try:
        count = event_store.delete_session(session_id)
        return {"deleted_count": count, "session_id": session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete events: {e}")


@app.post("/api/v1/replay/sessions")
async def create_session(body: dict[str, Any]) -> dict[str, Any]:
    symbol = body.get("symbol", "RELIANCE").upper()
    date_str = body.get("date", datetime.utcnow().strftime("%Y-%m-%d"))
    timeframe = body.get("timeframe", "1m")

    try:
        from_dt = datetime.strptime(f"{date_str} 09:15:00", "%Y-%m-%d %H:%M:%S")
        to_dt = datetime.strptime(f"{date_str} 15:30:00", "%Y-%m-%d %H:%M:%S")
    except ValueError:
        from_dt = datetime.utcnow()
        to_dt = from_dt + timedelta(hours=6)

    from_t = int(from_dt.timestamp() * 1000)
    to_t = int(to_dt.timestamp() * 1000)

    session_id = f"replay_{symbol}_{date_str}_{timeframe}"
    session = {
        "id": session_id,
        "symbol": symbol,
        "exchange": "NSE",
        "timeframe": timeframe,
        "from_t": from_t,
        "to_t": to_t,
        "cursor_t": from_t,
        "state": "IDLE",
        "speed": 1
    }
    async with shared_state_lock:
        REPLAY_SESSIONS[session_id] = session
    return session


@app.post("/api/v1/replay/sessions/{session_id}/control")
async def control_session(session_id: str, body: dict[str, Any]) -> dict[str, Any]:
    action = body.get("action")
    
    async with shared_state_lock:
        if session_id not in REPLAY_SESSIONS:
            raise HTTPException(status_code=404, detail="Session not found")
        session = REPLAY_SESSIONS[session_id]
        
        if action == "play":
            session["state"] = "PLAYING"
            
            # Load events from EventStore and replay
            try:
                events = event_store.get_session_events(session_id)
                if events:
                    tick_count = replay_engine.load_from_events(events)
                    replay_engine.speed_multiplier = session.get("speed", 1.0)
                    logger.info(f"Replay session {session_id}: Starting replay of {tick_count} ticks")
                    
                    # Start replay in background
                    asyncio.create_task(replay_engine.start())
                else:
                    logger.warning(f"Replay session {session_id}: No events found")
            except Exception as e:
                logger.error(f"Replay session {session_id} failed: {e}")
                
        elif action == "pause":
            session["state"] = "PAUSED"
            replay_engine.stop()
        elif action == "seek":
            to_t = body.get("to_t")
            if to_t is not None:
                session["cursor_t"] = to_t
                session["state"] = "PAUSED"
        elif action == "set_speed":
            speed = body.get("speed")
            if speed is not None:
                session["speed"] = speed

    return session


@app.get("/api/positions")
@app.get("/api/v1/positions")
async def get_positions() -> list[dict[str, Any]]:
    try:
        positions = broker_gateway.get_positions()
    except Exception as exc:
        logger.error(f"Failed to fetch positions: {exc}")
        positions = []
    return [
        {
            "symbol": pos.symbol,
            "exchange": pos.exchange.name if pos.exchange else "NSE",
            "quantity": pos.quantity,
            "avg_price": str(pos.avg_price),
            "ltp": str(pos.ltp),
            "unrealised_pnl": str(pos.unrealised_pnl),
            "realised_pnl": str(pos.realised_pnl),
            "position_side": pos.position_side.name,
            "state": pos.state.name,
        }
        for pos in positions
    ]


@app.get("/api/orders")
@app.get("/api/v1/orders")
async def get_orders() -> list[dict[str, Any]]:
    """Return all orders from Dhan broker, merged with local OMS state."""
    from scalpr.domain.order import Order
    
    dhan_orders: list[Order] = []
    try:
        dhan_orders = broker_gateway.get_orders()
    except Exception as exc:
        logger.error(f"Failed to fetch orders from Dhan: {exc}")
        dhan_orders = order_manager.get_orders()
    
    local_orders = order_manager.get_orders()
    dhan_ids = {o.order_id for o in dhan_orders}
    merged = list(dhan_orders) + [o for o in local_orders if o.order_id not in dhan_ids]
    
    return [
        {
            "order_id": o.order_id, "symbol": o.symbol,
            "exchange": o.exchange.name, "side": o.side.name,
            "order_type": o.order_type.name, "quantity": o.quantity,
            "price": str(o.price) if o.price else None,
            "state": o.state.name, "filled_quantity": o.filled_quantity,
            "avg_price": str(o.avg_price) if o.avg_price else None,
            "timestamp": o.timestamp.isoformat() if o.timestamp else None,
        }
        for o in merged
    ]


@app.get("/api/fills")
@app.get("/api/v1/fills")
async def get_fills() -> list[dict[str, Any]]:
    """Return execution fills/trades from Dhan broker."""
    from scalpr.domain.fill import Fill
    
    fills: list[Fill] = []
    try:
        fills = broker_gateway.get_tradebook()
    except Exception as exc:
        logger.error(f"Failed to fetch fills from Dhan: {exc}")
    
    return [
        {
            "fill_id": f.fill_id, "order_id": f.order_id,
            "symbol": f.symbol, "side": f.side.name,
            "quantity": f.quantity, "price": str(f.price),
            "timestamp": f.timestamp.isoformat() if f.timestamp else None,
        }
        for f in fills
    ]


@app.get("/api/portfolio")
@app.get("/api/v1/portfolio")
def get_portfolio() -> dict[str, Any]:
    try:
        margins = broker_gateway.get_margins()
        avail = margins.get("available_margin", Decimal("1000000.00"))
    except Exception:
        avail = Decimal("1000000.00")
        
    try:
        positions = broker_gateway.get_positions()
        daily_pnl = sum((pos.realised_pnl + pos.unrealised_pnl for pos in positions), Decimal("0"))
    except Exception:
        daily_pnl = Decimal("0")
        
    return {
        "balance": str(avail),
        "peak_balance": str(avail),
        "daily_pnl": str(daily_pnl),
        "drawdown": "0.0",
    }


@app.websocket("/ws/market")
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                action = msg.get("action")
                symbols = msg.get("symbols", [])
                if action == "subscribe":
                    manager.subscribe(websocket, symbols)
                elif action == "unsubscribe":
                    manager.unsubscribe(websocket, symbols)
            except Exception as exc:
                logger.debug("Failed to handle WS message: %s", exc)
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.websocket("/ws/replay/{session_id}")
async def websocket_replay_endpoint(websocket: WebSocket, session_id: str) -> None:
    """WebSocket endpoint to drive progressive chart replay visualization."""
    await websocket.accept()
    async with shared_state_lock:
        if session_id not in REPLAY_SESSIONS:
            await websocket.send_text(json.dumps({"type": "error", "message": "Session not found"}))
            await websocket.close()
            return
        session = dict(REPLAY_SESSIONS[session_id])  # Make a copy

    # Pre-generate mock candles for the session timeframe
    candles = await generate_mock_candles(session["symbol"], session["timeframe"], 375, datetime.fromtimestamp(session["to_t"]/1000.0, tz=timezone.utc))

    cursor = 0
    for i, c in enumerate(candles):
        if c["t"] >= session["cursor_t"]:
            cursor = i
            break

    try:
        # Start a silent receiver task
        async def receive_loop() -> None:
            try:
                while True:
                    await websocket.receive_text()
            except WebSocketDisconnect:
                pass

        receiver_task = asyncio.create_task(receive_loop())

        while True:
            async with shared_state_lock:
                if session_id not in REPLAY_SESSIONS:
                    break
                session = REPLAY_SESSIONS[session_id]
                state = session["state"]
                speed = session["speed"]
                cursor_t = session["cursor_t"]

            # Broadcast state update
            state_event = {
                "type": "replay_state",
                "session_id": session_id,
                "state": state,
                "speed": speed,
                "cursor_t": cursor_t
            }
            await websocket.send_text(json.dumps(state_event))

            if state == "PLAYING" and cursor < len(candles):
                c = candles[cursor]
                cursor += 1
                
                async with shared_state_lock:
                    REPLAY_SESSIONS[session_id]["cursor_t"] = c["t"]

                # Send next candle
                candle_event = {
                    "type": "replay_candle",
                    "session_id": session_id,
                    "candle": c
                }
                await websocket.send_text(json.dumps(candle_event))

                # Set price on paper OMS
                # Replay price setting bypassed for live broker: (session["symbol"], Decimal(str(c["c"])))

                # Delay based on speed multiplier
                delay = max(0.02, 0.2 / speed)
                await asyncio.sleep(delay)
            elif state == "ENDED" or cursor >= len(candles):
                async with shared_state_lock:
                    REPLAY_SESSIONS[session_id]["state"] = "ENDED"
                
                end_event = {
                    "type": "replay_state",
                    "session_id": session_id,
                    "state": "ENDED",
                    "speed": speed,
                    "cursor_t": REPLAY_SESSIONS[session_id]["to_t"]
                }
                await websocket.send_text(json.dumps(end_event))
                await asyncio.sleep(1.0)
            else:
                # PAUSED / IDLE state
                await asyncio.sleep(0.5)

    except WebSocketDisconnect:
        pass
    finally:
        with suppress(Exception):
            receiver_task.cancel()

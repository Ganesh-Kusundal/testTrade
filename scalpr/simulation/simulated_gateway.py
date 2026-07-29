"""SimulatedGateway — paper/replay/backtest broker adapter.

Implements the SAME IBrokerGateway port as DhanGateway and routes every
call through the SAME MultiBucketRateLimiter code path (built from
PAPER_RATE_LIMITS — effectively zero-delay, so replay stays deterministic)
so paper and live execution differ only in the event source and clock.

Design rules (plan Task 6.2):
- All timestamps come from the injected IClock — never wall-clock.
- Deterministic IDs (monotonic counters) — never uuid/random.
- All money is Decimal.
- No hidden capital defaults: starting_capital is mandatory (fail-closed).
"""
from __future__ import annotations

import logging
import threading
from datetime import date
from decimal import Decimal
from typing import Any

from scalpr.brokers.broker_port import IBrokerGateway
from scalpr.brokers.rate_limit import (
    PAPER_RATE_LIMITS,
    MultiBucketRateLimiter,
    limiter_from_table,
)
from scalpr.domain.clock import IClock, WallClock
from scalpr.domain.contracts import Funds
from scalpr.domain.errors import RateLimitError
from scalpr.domain.fill import Fill
from scalpr.domain.instrument import Exchange
from scalpr.domain.order import Order, OrderSide, OrderState, OrderType
from scalpr.domain.position import Position
from scalpr.domain.values import DEFAULT_EXCHANGE, ZERO
from scalpr.simulation.fill_simulator import FillSimulator

logger = logging.getLogger(__name__)

# Same fail-fast budget philosophy as DhanHttpClient's orders bucket.
_ACQUIRE_TIMEOUT_S = 2.0


class SimulatedGateway(IBrokerGateway):
    """In-process broker for paper trading, replay, and backtests.

    Orders fill immediately and fully against the last known price
    (set via set_ltp/on_tick): MARKET through the FillSimulator slippage
    model, LIMIT at the limit price. Resting-order simulation is out of
    scope — the strategy pipeline treats every submission as terminal.
    """

    def __init__(
        self,
        starting_capital: Decimal,
        clock: IClock | None = None,
        limiter: MultiBucketRateLimiter | None = None,
        fill_simulator: FillSimulator | None = None,
    ) -> None:
        if not isinstance(starting_capital, Decimal):
            raise TypeError("starting_capital must be a Decimal — money is never float")
        if starting_capital <= 0:
            raise ValueError("starting_capital must be positive")
        self._starting_capital = starting_capital
        self._clock = clock or WallClock()
        self._limiter = limiter or limiter_from_table(PAPER_RATE_LIMITS)
        self._fill_simulator = fill_simulator or FillSimulator()
        self._connected = False
        self._lock = threading.Lock()
        self._seq = 0
        self._ltp: dict[str, Decimal] = {}
        self._orders: dict[str, Order] = {}
        self._fills: list[Fill] = []
        self._positions: dict[str, Position] = {}

    @property
    def connection(self) -> None:
        return None

    # ------------------------------------------------------------------
    # Market feed hooks (driven by the tick source)
    # ------------------------------------------------------------------

    def set_ltp(self, symbol: str, price: Decimal) -> None:
        """Update the simulated last traded price for a symbol."""
        if not isinstance(price, Decimal):
            raise TypeError("price must be a Decimal")
        with self._lock:
            self._ltp[symbol] = price

    def on_tick(self, tick: Any) -> None:
        """Convenience subscriber: feed ticks straight from the tick source."""
        self.set_ltp(tick.symbol, tick.ltp)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def connect(self) -> None:
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _acquire(self, bucket: str) -> None:
        """Same limiter discipline as the live adapter: fail fast, never hang."""
        if not self._limiter.acquire(bucket, timeout=_ACQUIRE_TIMEOUT_S):
            raise RateLimitError(
                f"Rate limit budget exhausted for simulated {bucket} call",
                retry_after_s=1.0,
            )

    def _next_id(self, prefix: str) -> str:
        self._seq += 1
        return f"{prefix}-{self._seq}"

    def _execution_price(self, order: Order) -> Decimal:
        last = self._ltp.get(order.symbol)
        if order.order_type == OrderType.MARKET:
            if last is None:
                raise ValueError(
                    f"No simulated LTP for {order.symbol} — feed set_ltp/on_tick first"
                )
            return self._fill_simulator.simulate_market_fill(order, last)
        # LIMIT / SL variants fill at their stated price in simulation.
        return order.price

    # ------------------------------------------------------------------
    # Orders
    # ------------------------------------------------------------------

    def place_order(self, order: Order) -> Fill:
        self._acquire("orders")
        with self._lock:
            price = self._execution_price(order)
            now = self._clock.now()
            broker_order_id = order.order_id or self._next_id("SIM-ORD")
            fill = Fill(
                fill_id=self._next_id("SIM-FILL"),
                order_id=broker_order_id,
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity,
                price=price,
                timestamp=now,
                exchange=order.exchange.value,
            )
            filled = Order(
                order_id=broker_order_id,
                symbol=order.symbol,
                exchange=order.exchange,
                side=order.side,
                order_type=order.order_type,
                quantity=order.quantity,
                price=order.price,
                trigger_price=order.trigger_price,
                state=OrderState.FILLED,
                filled_quantity=order.quantity,
                avg_price=price,
                timestamp=now,
                product_type=order.product_type,
                validity=order.validity,
                correlation_id=order.correlation_id,
            )
            self._orders[broker_order_id] = filled
            self._fills.append(fill)
            self._apply_fill(fill)
            self._ltp[order.symbol] = price
            logger.info("sim_fill: %s %s %s x%s @ %s",
                        broker_order_id, order.side.value, order.symbol,
                        order.quantity, price)
            return fill

    def modify_order(
        self,
        order_id: str,
        price: Decimal,
        quantity: int,
        trigger_price: Decimal | None = None,
    ) -> bool:
        self._acquire("orders")
        # Everything fills instantly — nothing modifiable remains.
        return False

    def cancel_order(self, order_id: str) -> bool:
        self._acquire("orders")
        # Everything fills instantly — nothing cancellable remains.
        return False

    def get_order_status(self, order_id: str) -> Order:
        with self._lock:
            if order_id not in self._orders:
                raise KeyError(f"Unknown simulated order: {order_id}")
            return self._orders[order_id]

    def get_orders(self) -> list[Order]:
        with self._lock:
            return list(self._orders.values())

    def get_tradebook(self) -> list[Fill]:
        with self._lock:
            return list(self._fills)

    # ------------------------------------------------------------------
    # Positions & funds
    # ------------------------------------------------------------------

    def _apply_fill(self, fill: Fill) -> None:
        """Update the per-symbol position via the domain's ONLY PnL path."""
        position = self._positions.get(fill.symbol) or Position(
            symbol=fill.symbol,
            exchange=Exchange(fill.exchange) if fill.exchange else Exchange.NSE,
        )
        signed = fill.quantity if fill.side == OrderSide.BUY else -fill.quantity
        self._positions[fill.symbol] = position.with_fill(signed, fill.price, fill.side)

    def get_positions(self) -> list[Position]:
        with self._lock:
            return [p for p in self._positions.values() if p.quantity != 0]

    def get_holdings(self) -> list[Position]:
        return []  # intraday simulator: no delivery holdings

    def get_margins(self) -> Funds:  # type: ignore[override]
        with self._lock:
            realised = sum(
                (p.realised_pnl for p in self._positions.values()), ZERO
            )
            used = sum(
                (p.notional_value() for p in self._positions.values()), ZERO
            )
            total = self._starting_capital + realised
            return Funds(
                available_margin=total - used,
                used_margin=used,
                total_balance=total,
                collateral=ZERO,
                realtime=False,
            )

    def get_fund_limits(self) -> Funds:  # type: ignore[override]
        return self.get_margins()

    def square_off_all(self) -> list[Fill]:
        with self._lock:
            open_positions = [p for p in self._positions.values() if p.quantity != 0]
        fills: list[Fill] = []
        for position in open_positions:
            side = OrderSide.SELL if position.quantity > 0 else OrderSide.BUY
            order = Order(
                order_id="",
                symbol=position.symbol,
                exchange=position.exchange,
                side=side,
                order_type=OrderType.MARKET,
                quantity=abs(position.quantity),
                state=OrderState.PENDING,
            )
            fills.append(self.place_order(order))
        return fills

    # ------------------------------------------------------------------
    # Market data
    # ------------------------------------------------------------------

    def get_ltp(self, symbol: str, exchange: str = DEFAULT_EXCHANGE) -> Decimal:
        self._acquire("quotes")
        with self._lock:
            if symbol not in self._ltp:
                raise ValueError(f"No simulated LTP for {symbol}")
            return self._ltp[symbol]

    def get_quote(self, symbol: str, exchange: str = DEFAULT_EXCHANGE) -> dict[str, Any]:
        self._acquire("quotes")
        with self._lock:
            if symbol not in self._ltp:
                raise ValueError(f"No simulated LTP for {symbol}")
            ltp = self._ltp[symbol]
        return {
            "ltp": ltp, "open": ltp, "high": ltp, "low": ltp,
            "close": ltp, "volume": 0, "change": ZERO,
            "change_percent": ZERO,
        }

    def get_ohlcv(
        self,
        symbol: str,
        exchange: str,
        timeframe: str,
        from_date: date,
        to_date: date,
    ) -> list[dict[str, Any]]:
        self._acquire("historical")
        return []  # historical data comes from EventStore replay, not the sim broker

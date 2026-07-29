"""5-day replay simulation: synthetic tick data → SimulatedGateway → strategy → invariants.

Self-contained, deterministic, no external files or credentials.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from scalpr.domain.clock import SimulatedClock
from scalpr.domain.instrument import Exchange
from scalpr.domain.order import Order, OrderSide, OrderState, OrderType
from scalpr.domain.tick import OHLCV, Tick
from scalpr.simulation.simulated_gateway import SimulatedGateway

SYMBOL = "RELIANCE"
START_CAPITAL = Decimal("1000000")
BASE_PRICE = Decimal("2500.00")

# Market hours: 9:15-15:30 IST = 3:45-10:00 UTC
SESSION_START = datetime(2026, 1, 5, 3, 45, tzinfo=timezone.utc)
TICK_INTERVAL_S = 60  # 1-minute bars
TICKS_PER_DAY = 376   # 9:15→15:30 = 375 min, +1 for inclusive end


# ── Synthetic data generation ─────────────────────────────────────────

def _generate_5day_ohlcv(seed: int = 42) -> list[OHLCV]:
    """Deterministic 5-day OHLCV sequence with intraday random walk."""
    rng = random.Random(seed)
    bars: list[OHLCV] = []

    for day in range(5):
        open_price = BASE_PRICE + Decimal(str(rng.uniform(-20, 20))).quantize(Decimal("0.05"))
        ts = SESSION_START + timedelta(days=day)
        price = open_price

        for _ in range(TICKS_PER_DAY):
            step = Decimal(str(rng.uniform(-3, 3))).quantize(Decimal("0.05"))
            close = (price + step).quantize(Decimal("0.05"))
            high = max(price, close) + Decimal(str(rng.uniform(0, 1))).quantize(Decimal("0.05"))
            low = min(price, close) - Decimal(str(rng.uniform(0, 1))).quantize(Decimal("0.05"))
            volume = rng.randint(100, 5000)

            bars.append(OHLCV(
                open=price,
                high=high,
                low=low,
                close=close,
                volume=volume,
                bar_open_time=ts,
                is_closed=True,
            ))
            price = close
            ts += timedelta(seconds=TICK_INTERVAL_S)

    return bars


def _bars_to_ticks(bars: list[OHLCV]) -> list[Tick]:
    """Convert OHLCV bars to midpoint ticks with bid/ask spread."""
    ticks: list[Tick] = []
    for bar in bars:
        spread = Decimal("0.10")
        ticks.append(Tick(
            symbol=SYMBOL,
            ltp=bar.close,
            bid=(bar.close - spread / 2).quantize(Decimal("0.05")),
            ask=(bar.close + spread / 2).quantize(Decimal("0.05")),
            delta_volume=bar.volume,
            cumulative_volume=bar.volume + (ticks[-1].cumulative_volume if ticks else 0),
            exchange_timestamp=bar.bar_open_time,
        ))
    return ticks


# ── Test strategy ─────────────────────────────────────────────────────

class _ReplayTestStrategy:
    """Minimal intraday strategy: buy at session open, sell at session close.

    Validates: order placement, fill, position tracking, and P&L across days.
    Session is 3:45-10:00 UTC (9:15-15:30 IST).
    """

    def __init__(self, gateway: SimulatedGateway, symbol: str) -> None:
        self.gateway = gateway
        self.symbol = symbol
        self.trades: list[str] = []
        self.errors: list[str] = []
        self._day: int | None = None

    def on_tick(self, tick: Tick) -> None:
        if tick.symbol != self.symbol:
            return
        self.gateway.set_ltp(self.symbol, tick.ltp)

    def on_bar(self, bar: OHLCV) -> None:
        t = bar.bar_open_time
        day = t.toordinal()
        first_of_day = t.hour == 3 and t.minute == 45
        last_of_day = t.hour == 10 and t.minute == 0

        if first_of_day:
            self._day = day
            self._open_long(bar)
        elif last_of_day:
            self._close_long(bar)
            self._day = None

    def _open_long(self, bar: OHLCV) -> None:
        try:
            order = Order(
                order_id=f"replay-{len(self.trades)}",
                symbol=self.symbol,
                exchange=Exchange.NSE,
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=75,
                price=bar.close,
                state=OrderState.PENDING,
            )
            self.gateway.place_order(order)
            self.trades.append(f"BUY@{bar.close}")
        except Exception as e:
            self.errors.append(f"open failed: {e}")

    def _close_long(self, bar: OHLCV) -> None:
        try:
            order = Order(
                order_id=f"replay-close-{len(self.trades)}",
                symbol=self.symbol,
                exchange=Exchange.NSE,
                side=OrderSide.SELL,
                order_type=OrderType.MARKET,
                quantity=75,
                price=bar.close,
                state=OrderState.PENDING,
            )
            self.gateway.place_order(order)
            self.trades.append(f"SELL@{bar.close}")
        except Exception as e:
            self.errors.append(f"close failed: {e}")


# ── Test class ────────────────────────────────────────────────────────

class Test5DayReplay:
    """End-to-end 5-day replay simulation."""

    def _replay(self, seed: int = 42) -> tuple[SimulatedGateway, _ReplayTestStrategy]:
        """Run full 5-day replay, return (gateway, strategy)."""
        bars = _generate_5day_ohlcv(seed=seed)
        ticks = _bars_to_ticks(bars)
        clock = SimulatedClock(SESSION_START)
        gateway = SimulatedGateway(starting_capital=START_CAPITAL, clock=clock)
        gateway.connect()
        gateway.set_ltp(SYMBOL, BASE_PRICE)
        strategy = _ReplayTestStrategy(gateway, SYMBOL)

        for bar, tick in zip(bars, ticks, strict=False):
            clock.set(bar.bar_open_time)
            strategy.on_tick(tick)
            strategy.on_bar(bar)

        return gateway, strategy

    def test_replay_runs_without_exceptions(self):
        _, strategy = self._replay()
        assert strategy.errors == [], f"Strategy errors: {strategy.errors}"

    def test_orders_fill_and_trades_execute(self):
        gateway, _strategy = self._replay()
        fills = gateway.get_tradebook()
        assert len(fills) == 10, f"Expected 10 fills (5 buy + 5 sell), got {len(fills)}"

    def test_positions_open_and_close_correctly(self):
        gateway, _strategy = self._replay()
        positions = gateway.get_positions()
        assert len(positions) == 0, f"Expected flat, got {positions}"

    def test_pnl_calculated_after_replay(self):
        gateway, _strategy = self._replay()
        margins = gateway.get_margins()
        assert isinstance(margins.total_balance, Decimal)
        assert margins.total_balance != START_CAPITAL, "P&L should change total balance"

    def test_no_unhandled_exceptions_across_five_days(self):
        _, strategy = self._replay()
        assert strategy.errors == [], f"Unhandled errors: {strategy.errors}"

    def test_deterministic_across_runs(self):
        def _run(seed: int) -> list[str]:
            _, s = self._replay(seed=seed)
            return s.trades
        assert _run(42) == _run(42), "Determinism broken"

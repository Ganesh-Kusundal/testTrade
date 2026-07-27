from __future__ import annotations

import logging
from decimal import Decimal

from scalpr.domain.instrument import Exchange
from scalpr.domain.order import Order, OrderSide, OrderState, OrderType
from scalpr.domain.tick import OHLCV, Tick
from scalpr.execution.order_router import OrderRouter
from scalpr.signals.cvd import CvdTracker
from scalpr.signals.gate_fsm import GateFSM, GateState
from scalpr.signals.volume_profile import VolumeProfile
from scalpr.strategy.strategy_port import IStrategy

logger = logging.getLogger(__name__)


class ScalprAmtStrategy(IStrategy):
    """Fabio Valentini AMT Intraday Options Scalping Strategy."""

    def __init__(self, order_router: OrderRouter, symbol: str) -> None:
        self.order_router = order_router
        self.symbol = symbol
        self.volume_profile = VolumeProfile()
        self.cvd_tracker = CvdTracker()
        self._trade_count = 0

    def get_status(self) -> dict:
        """Return strategy status for observability endpoint."""
        return {"trade_count": self._trade_count, "max_trades_per_day": 10}

    def on_tick(self, tick: Tick) -> None:
        """Process live tick, feed CVD, evaluate Gate FSM, and trigger buy/sell orders."""
        if tick.symbol != self.symbol:
            return

        # 1. Update CVD (Simulate bid/ask depths for calculation)
        ask_qty = 100
        bid_qty = 90  # Positive delta buy pressure
        self.cvd_tracker.process_tick(tick, ask_qty, bid_qty)

        # 2. Evaluate FSM State
        is_lvn = self.volume_profile.is_lvn(tick.ltp)
        cvd_falling = False  # simulated

        # Construct Gate state
        gate_state = GateState(
            symbol=self.symbol,
            price=tick.ltp,
            cvd_falling=cvd_falling,
            is_at_lvn=is_lvn,
            under_daily_cap=(self._trade_count < 10),
        )

        passed, reason, results = GateFSM.evaluate(gate_state)

        if passed:
            logger.info(f"AMT Strategy: Setup Triggered! Reason: {reason}")
            # If no open positions, place simulated buy order
            positions = self.order_router.gateway.get_positions()
            active_pos = [p for p in positions if p.symbol == self.symbol and p.quantity != 0]

            if not active_pos:
                self._trade_count += 1
                order = Order(
                    order_id=f"amt_{self.symbol}_{self._trade_count}",
                    symbol=self.symbol,
                    exchange=Exchange.NSE,
                    side=OrderSide.BUY,
                    order_type=OrderType.MARKET,
                    quantity=50,  # 1 lot size
                    price=tick.ltp,
                    state=OrderState.PENDING,
                )
                logger.info(f"AMT Strategy: Submitting order {order.order_id}")
                
                # Submit through OrderRouter (enforces risk checks)
                try:
                    margins = self.order_router.gateway.get_margins()
                    available_margin = margins.get("available_margin", Decimal("1000000.00"))
                    
                    self.order_router.submit_order(
                        order=order,
                        positions=positions,
                        available_margin=available_margin,
                        daily_loss=Decimal("0"),  # TODO: Fetch from portfolio manager
                        portfolio_value=Decimal("1000000.00"),  # TODO: Fetch from portfolio manager
                    )
                    logger.info(f"AMT Strategy: Order {order.order_id} submitted successfully")
                except Exception as exc:
                    logger.error(f"AMT Strategy: Order submission failed: {exc}")

    def on_bar(self, bar: OHLCV) -> None:
        """Incorporate closed bar into the volume profile."""
        self.volume_profile.update(bar)

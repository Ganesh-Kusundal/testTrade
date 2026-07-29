from __future__ import annotations

import logging
from typing import Any

from scalpr.domain.instrument import Exchange
from scalpr.domain.order import Order, OrderSide, OrderState, OrderType
from scalpr.domain.tick import OHLCV, Tick
from scalpr.domain.values import ZERO
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

        # Load quantities from env, with safe defaults
        import os

        self._ask_qty = int(os.environ.get("SCALPR_AMT_ASK_QTY", "100"))
        self._bid_qty = int(os.environ.get("SCALPR_AMT_BID_QTY", "90"))
        self._max_trades_per_day = int(os.environ.get("SCALPR_AMT_MAX_TRADES", "10"))

        # Validate bounds
        if self._ask_qty <= 0 or self._bid_qty <= 0:
            raise ValueError("SCALPR_AMT_ASK_QTY and SCALPR_AMT_BID_QTY must be positive")
        if self._ask_qty > 1000 or self._bid_qty > 1000:
            raise ValueError("SCALPR_AMT_ASK_QTY and SCALPR_AMT_BID_QTY must be <= 1000")

    def get_status(self) -> dict[str, Any]:
        """Return strategy status for observability endpoint."""
        return {
            "trade_count": self._trade_count,
            "max_trades_per_day": self._max_trades_per_day,
            "ask_qty": self._ask_qty,
            "bid_qty": self._bid_qty,
        }

    def on_tick(self, tick: Tick) -> None:
        """Process live tick, feed CVD, evaluate Gate FSM, and trigger buy/sell orders."""
        if tick.symbol != self.symbol:
            return

        # 1. Update CVD (Simulate bid/ask depths for calculation)
        self.cvd_tracker.process_tick(tick, self._ask_qty, self._bid_qty)

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

        passed, reason, _results = GateFSM.evaluate(gate_state)

        if passed:
            logger.info("AMT Strategy: Setup Triggered! Reason: %s", reason)
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
                    quantity=self._ask_qty,
                    price=tick.ltp,
                    state=OrderState.PENDING,
                )
                logger.info("AMT Strategy: Submitting order %s", order.order_id)

                # Submit through OrderRouter (enforces risk checks)
                try:
                    margins = self.order_router.gateway.get_margins()
                    available_margin = margins.available_margin
                    portfolio_value = margins.total_balance
                    if portfolio_value <= 0:
                        # Fail-closed: no trade without real risk data
                        logger.error("risk_inputs_unavailable — order blocked")
                        return
                    daily_loss = max(
                        ZERO,
                        -sum((p.realised_pnl + p.unrealised_pnl for p in positions), ZERO),
                    )

                    self.order_router.submit_order(
                        order=order,
                        positions=positions,
                        available_margin=available_margin,
                        daily_loss=daily_loss,
                        portfolio_value=portfolio_value,
                        ltp=tick.ltp,  # K-020: LTP for MARKET order notional
                    )
                    logger.info("AMT Strategy: Order %s submitted successfully", order.order_id)
                except Exception as exc:
                    logger.error("AMT Strategy: Order submission failed: %s", exc)

    def on_bar(self, bar: OHLCV) -> None:
        """Incorporate closed bar into the volume profile."""
        self.volume_profile.update(bar)

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from scalpr.adapters.dhan.client import DhanClient
from scalpr.domain.order import Order, OrderSide, OrderType
from scalpr.domain.position import PositionSide

logger = logging.getLogger(__name__)
IST = timezone(timedelta(hours=5, minutes=30))


class SessionGuard:
    """Tracks consecutive session losses and manages IST intraday square-off times."""

    def __init__(self, gateway: DhanClient, max_losses: int = 3) -> None:
        self._client = gateway
        self.max_losses = max_losses
        self.consecutive_losses = 0
        self.halted = False
        self._warned_nse = False
        self._warned_mcx = False
        self._squared_off_nse = False
        self._squared_off_mcx = False

    def record_pnl(self, pnl: Decimal) -> None:
        """Record trade PnL. Halts and squares off after 3 consecutive losses."""
        if pnl < 0:
            self.consecutive_losses += 1
            logger.warning("SessionGuard: Recorded loss. Consecutive losses: %s/%s", self.consecutive_losses, self.max_losses)
            if self.consecutive_losses >= self.max_losses:
                self.halted = True
                logger.critical("SessionGuard: 3 consecutive losses reached! Initiating square_off_all and halting trading.")
                self._square_off_all()
        else:
            self.consecutive_losses = 0

    def check_market_cutoff(self, current_time: datetime) -> bool:
        """Check current time against IST market boundaries. Squares off intraday positions."""
        ist_now = current_time.astimezone(IST)
        hour = ist_now.hour
        minute = ist_now.minute

        # 1. NSE Equity/FNO Cutoff (15:15 IST)
        # Warning at 15:00-15:14 IST (15 minutes prior to cutoff)
        if hour == 15 and 0 <= minute < 15 and not self._warned_nse:
            logger.warning("SessionGuard Alert: NSE Intraday square-off in 15 minutes!")
            self._warned_nse = True

        # Square-off at 15:15+ IST
        if hour == 15 and minute >= 15 and not self._squared_off_nse:
            self._squared_off_nse = True
            logger.critical("SessionGuard Cutoff: NSE Intraday square-off time reached. Squaring off.")
            self._square_off_all()
            self.halted = True
            return True

        # 2. MCX Commodity Cutoff (23:15 IST)
        # Warning at 23:00-23:14 IST (15 minutes prior to cutoff)
        if hour == 23 and 0 <= minute < 15 and not self._warned_mcx:
            logger.warning("SessionGuard Alert: MCX Intraday square-off in 15 minutes!")
            self._warned_mcx = True

        # Square-off at 23:15+ IST
        if hour == 23 and minute >= 15 and not self._squared_off_mcx:
            self._squared_off_mcx = True
            logger.critical("SessionGuard Cutoff: MCX Intraday square-off time reached. Squaring off.")
            self._square_off_all()
            self.halted = True
            return True

        return False

    def _square_off_all(self) -> None:
        positions = self._client.get_positions()
        for pos in positions:
            if pos.quantity != 0:
                try:
                    side = OrderSide.SELL if pos.position_side == PositionSide.LONG else OrderSide.BUY
                    self._client.place_order(Order(
                        order_id="",
                        symbol=pos.symbol,
                        exchange=pos.exchange,
                        side=side,
                        order_type=pos.order_type if hasattr(pos, 'order_type') else None,
                        quantity=abs(pos.quantity),
                        price=pos.avg_price,
                    ))
                except Exception as exc:
                    logger.error("square_off_failed: symbol=%s error=%s", pos.symbol, exc)

    def reset_guard(self) -> None:
        """Reset the loss counters and halt state (requires manual operator action)."""
        self.consecutive_losses = 0
        self.halted = False
        self._warned_nse = False
        self._warned_mcx = False
        self._squared_off_nse = False
        self._squared_off_mcx = False
        logger.info("SessionGuard has been manually reset.")

from __future__ import annotations

import threading
from decimal import Decimal
from typing import Any

from scalpr.domain.fill import Fill
from scalpr.domain.position import Position
from scalpr.domain.tick import Tick
from scalpr.domain.values import ZERO


class PortfolioManager:
    """Manages aggregate portfolio state, marks-to-market positions, and tracks session PnL."""

    def __init__(self) -> None:
        self.positions: dict[str, Position] = {}
        self.peak_equity: Decimal = ZERO
        self._lock = threading.RLock()

    def update_position_from_fill(self, fill: Fill, exchange: Any) -> Position:
        """Apply a new fill transaction to update position averages and realized pnl."""
        with self._lock:
            symbol = fill.symbol
            pos = self.positions.get(symbol)
            if pos is None:
                # Initialize flat position
                pos = Position(
                    symbol=symbol,
                    exchange=exchange,
                    quantity=0,
                    avg_price=ZERO,
                    ltp=fill.price,
                    unrealised_pnl=ZERO,
                    realised_pnl=ZERO,
                )

            # signed quantity delta: BUY is positive, SELL is negative
            signed_qty = fill.quantity if fill.side.value == "BUY" else -fill.quantity
            updated = pos.with_fill(signed_qty, fill.price, fill.side)
            self.positions[symbol] = updated

            # Recalculate equity metrics
            self._update_peak_equity()
            return updated

    def update_ltp(self, tick: Tick) -> None:
        """Mark positions to market on new price ticks."""
        with self._lock:
            symbol = tick.symbol
            pos = self.positions.get(symbol)
            if pos:
                self.positions[symbol] = pos.with_ltp(tick.ltp)
                self._update_peak_equity()

    @property
    def total_realised_pnl(self) -> Decimal:
        with self._lock:
            return sum((pos.realised_pnl for pos in self.positions.values()), ZERO)

    @property
    def total_unrealised_pnl(self) -> Decimal:
        with self._lock:
            return sum((pos.unrealised_pnl for pos in self.positions.values()), ZERO)

    @property
    def total_pnl(self) -> Decimal:
        return self.total_realised_pnl + self.total_unrealised_pnl

    def _update_peak_equity(self) -> None:
        total_pnl = self.total_pnl
        if total_pnl > self.peak_equity:
            self.peak_equity = total_pnl

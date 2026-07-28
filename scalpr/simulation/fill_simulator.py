from __future__ import annotations

from decimal import Decimal

from scalpr.domain.order import Order, OrderSide, OrderType
from scalpr.domain.tick import OHLCV


class FillSimulator:
    """Simulates realistic limit and market order executions under slippage and cost models."""

    def __init__(self, slippage_ticks: int = 1, tick_size: Decimal = Decimal("0.05")) -> None:
        self.slippage_ticks = slippage_ticks
        self.tick_size = tick_size

    def simulate_market_fill(self, order: Order, last_price: Decimal) -> Decimal:
        """Calculate market order fill price incorporating slippage."""
        slippage = self.tick_size * Decimal(self.slippage_ticks)
        if order.side == OrderSide.BUY:
            return last_price + slippage
        else:
            return last_price - slippage

    def check_limit_fill(self, order: Order, bar: OHLCV) -> Decimal | None:
        """Check if a limit order would be filled by the OHLCV bar."""
        if order.order_type != OrderType.LIMIT:
            return None

        # Buy limit fills if low is below or equal to limit price
        if order.side == OrderSide.BUY:
            if bar.low <= order.price:
                return order.price
        # Sell limit fills if high is above or equal to limit price
        elif order.side == OrderSide.SELL and bar.high >= order.price:
            return order.price

        return None

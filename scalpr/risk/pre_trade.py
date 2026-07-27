from __future__ import annotations

from decimal import Decimal

from scalpr.domain.order import Order, OrderSide
from scalpr.domain.position import Position, PositionSide


class PreTradeRiskGate:
    """Pre-trade risk gateway that validates order submission against account limits."""

    def __init__(
        self,
        portfolio_value: Decimal = Decimal("1000000.00"),
        max_open_positions: int = 5,
        max_concentration_pct: float = 0.20,      # 20% of portfolio max per instrument
        max_capital_risk_pct: float = 0.01,       # 1% risk per trade
        margin_buffer_factor: float = 1.20,       # 1.2x margin buffer
        halted: bool = False,
    ) -> None:
        self.portfolio_value = portfolio_value
        self.max_open_positions = max_open_positions
        self.max_concentration = Decimal(str(max_concentration_pct))
        self.max_capital_risk = Decimal(str(max_capital_risk_pct))
        self.margin_buffer_factor = Decimal(str(margin_buffer_factor))
        self.halted = halted

    def check_order(
        self,
        order: Order,
        positions: list[Position],
        available_margin: Decimal,
        required_margin: Decimal,
        daily_loss: Decimal,
    ) -> tuple[bool, str]:
        """Check order. Returns (allowed: bool, reason: str)."""
        if self.halted:
            return False, "Trading is halted globally"

        # Check if the order is reducing or closing an existing position
        pos_map = {p.symbol: p for p in positions if p.quantity != 0}
        existing_pos = pos_map.get(order.symbol)

        is_reducing = False
        if existing_pos:
            if (existing_pos.position_side == PositionSide.LONG and order.side == OrderSide.SELL) or \
               (existing_pos.position_side == PositionSide.SHORT and order.side == OrderSide.BUY):
                is_reducing = True

        # If reducing, bypass some checks (we should always allow position reduction for safety)
        if is_reducing:
            return True, "Allowed: Order reduces existing exposure"

        # 1. Daily loss limit not breached (e.g. daily loss max 3%)
        if daily_loss > self.portfolio_value * Decimal("0.03"):
            return False, "Daily loss limit breached"

        # 2. Max open positions check
        active_positions_count = len(pos_map)
        if active_positions_count >= self.max_open_positions:
            return False, f"Max open positions ({self.max_open_positions}) reached"

        # 3. Capital at risk per trade <= 1%
        order_notional = order.price * Decimal(order.quantity) if order.price > 0 else Decimal(order.quantity) * Decimal("2500.00")
        # Let's say risk = 1% of portfolio for simplicity if SL distance is not given, or if risk is calculated
        if order_notional > self.portfolio_value * self.max_capital_risk:
            return False, f"Order notional ({order_notional}) exceeds max capital risk per trade ({self.portfolio_value * self.max_capital_risk})"

        # 4. Instrument concentration <= 20% of portfolio
        current_notional = Decimal("0")
        if existing_pos:
            current_notional = Decimal(abs(existing_pos.quantity)) * existing_pos.avg_price

        total_notional = current_notional + order_notional
        concentration_limit = self.portfolio_value * self.max_concentration
        if total_notional > concentration_limit:
            return False, f"Exceeds max concentration limit of {concentration_limit} for {order.symbol}"

        # 5. Available margin >= required margin * 1.2 buffer
        if available_margin < required_margin * self.margin_buffer_factor:
            return False, f"Insufficient margin: Available {available_margin} < Required {required_margin * self.margin_buffer_factor}"

        return True, "Passed all pre-trade risk checks"

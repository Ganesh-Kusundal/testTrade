from __future__ import annotations

import math
from decimal import Decimal


class AtrPositionSizer:
    """ATR-based fixed risk position sizer that aligns quantity to contract lot sizes."""

    def __init__(self, max_quantity_cap: int = 10000) -> None:
        self.max_quantity_cap = max_quantity_cap

    def calculate_quantity(
        self,
        portfolio_value: Decimal,
        atr: Decimal,
        multiplier: Decimal,
        lot_size: int,
    ) -> int:
        """Calculate quantity: floor(risk_amount / (atr * multiplier * lot_size)) * lot_size."""
        if atr <= 0 or multiplier <= 0 or lot_size <= 0:
            return 0

        # Risk amount = 1% of portfolio value
        risk_amount = portfolio_value * Decimal("0.01")

        # Risk per lot = atr * multiplier * lot_size
        risk_per_lot = atr * multiplier * Decimal(lot_size)

        if risk_per_lot <= 0:
            return 0

        # Number of lots to trade
        lots = math.floor(float(risk_amount / risk_per_lot))
        quantity = lots * lot_size

        # Cap it at max_quantity_cap
        if quantity > self.max_quantity_cap:
            # Align cap to lot size
            capped_lots = self.max_quantity_cap // lot_size
            quantity = capped_lots * lot_size

        return int(quantity)

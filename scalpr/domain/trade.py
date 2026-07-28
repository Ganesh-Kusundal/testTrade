from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from scalpr.domain.order import OrderSide


@dataclass(slots=True, frozen=True)
class Trade:
    """Completed round-trip: entry/exit fill references plus realized PnL."""
    trade_id: str
    symbol: str
    side: OrderSide  # side of the ENTRY fill
    quantity: int
    entry_fill_id: str
    exit_fill_id: str
    entry_price: Decimal
    exit_price: Decimal
    realized_pnl: Decimal
    opened_at: datetime
    closed_at: datetime

    def __post_init__(self) -> None:
        for name in ("entry_price", "exit_price", "realized_pnl"):
            if not isinstance(getattr(self, name), Decimal):
                raise TypeError(f"{name} must be a Decimal")
        if not isinstance(self.quantity, int) or self.quantity <= 0:
            raise ValueError("quantity must be a positive integer")
        if self.closed_at < self.opened_at:
            raise ValueError("closed_at cannot precede opened_at")

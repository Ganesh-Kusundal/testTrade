from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from scalpr.domain.order import OrderSide


@dataclass(slots=True, frozen=True)
class Fill:
    """Execution fill details."""
    fill_id: str
    order_id: str
    symbol: str
    side: OrderSide
    quantity: int
    price: Decimal
    timestamp: datetime | None = None
    exchange: str = ""  # "" = unknown (broker response lacked segment)

    def __post_init__(self) -> None:
        if not isinstance(self.price, Decimal):
            raise TypeError("price must be Decimal")
        if not isinstance(self.quantity, int):
            raise TypeError("quantity must be an integer")


@dataclass(slots=True, frozen=True)
class PartialFill:
    """Partial execution fill details."""
    fill_id: str
    order_id: str
    symbol: str
    side: OrderSide
    quantity: int
    price: Decimal
    timestamp: datetime | None = None
    exchange: str = ""  # "" = unknown (broker response lacked segment)

    def __post_init__(self) -> None:
        if not isinstance(self.price, Decimal):
            raise TypeError("price must be Decimal")
        if not isinstance(self.quantity, int):
            raise TypeError("quantity must be an integer")

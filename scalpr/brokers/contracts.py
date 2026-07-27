"""Canonical contract models for broker-agnostic data exchange.

These models define the standard return types for all gateway operations,
ensuring no broker-specific fields leak into application code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from scalpr.domain.order import OrderSide


@dataclass(frozen=True)
class Quote:
    """Canonical market quote model.

    Returned by Gateway.quote() and Gateway.ltp().
    """

    symbol: str
    exchange: str
    ltp: Decimal
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    change: Decimal = Decimal("0")
    change_percent: Decimal = Decimal("0")
    timestamp: datetime | None = None


@dataclass(frozen=True)
class DepthLevel:
    """Single price level in market depth."""

    price: Decimal
    quantity: int
    orders: int = 1


@dataclass(frozen=True)
class MarketDepth:
    """Canonical market depth model with bid/ask levels.

    Returned by Gateway.depth().
    """

    symbol: str
    exchange: str
    bid_levels: list[DepthLevel]
    ask_levels: list[DepthLevel]
    timestamp: datetime | None = None


@dataclass(frozen=True)
class Holding:
    """Canonical holdings model for long-term delivery positions.

    Returned by Gateway.holdings().
    """

    symbol: str
    exchange: str
    quantity: int
    average_price: Decimal
    current_price: Decimal
    pnl: Decimal = Decimal("0")
    pnl_percent: Decimal = Decimal("0")


@dataclass(frozen=True)
class Funds:
    """Canonical funds and margin model.

    Returned by Gateway.funds().
    """

    available_margin: Decimal
    used_margin: Decimal
    total_balance: Decimal
    collateral: Decimal = Decimal("0")
    realtime: bool = True


@dataclass(frozen=True)
class Trade:
    """Canonical trade/execution fill model.

    Returned by Gateway.trades().
    """

    trade_id: str
    order_id: str
    symbol: str
    exchange: str
    side: OrderSide
    quantity: int
    price: Decimal
    timestamp: datetime | None = None

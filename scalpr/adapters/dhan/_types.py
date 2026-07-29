from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class DhanAuthRequest:
    client_id: str
    totp: str


@dataclass(frozen=True)
class DhanAuthResponse:
    access_token: str
    expires_at: str
    token_type: str


@dataclass(frozen=True)
class DhanOrderRequest:
    correlation_id: str
    exchange: str
    security_id: str
    transaction_type: str
    quantity: int
    price: float
    order_type: str
    validity: str = "DAY"
    product_type: str = "INTRADAY"
    trigger_price: float = 0.0
    disclosed_quantity: int = 0
    after_market: bool = False
    amo_time: str = "OPEN"
    bo_profit_value: float | None = None
    bo_stop_loss_value: float | None = None
    tag: str | None = None
    should_slice: bool = False


@dataclass(frozen=True)
class DhanOrderResponse:
    order_id: str
    status: str
    exchange_order_id: str | None = None


@dataclass(frozen=True)
class DhanSliceOrderResponse:
    order_ids: list[str]


@dataclass(frozen=True)
class DhanKillSwitchRequest:
    action: str  # ACTIVATE | DEACTIVATE


@dataclass(frozen=True)
class DhanKillSwitchResponse:
    kill_switch_status: str


@dataclass(frozen=True)
class DhanQuoteRequest:
    security_ids: list[str]
    exchange: str


@dataclass(frozen=True)
class DhanQuoteResponse:
    security_id: str
    last_traded_price: float
    volume: int = 0
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    change: float = 0.0
    change_percent: float = 0.0
    bid: float = 0.0
    ask: float = 0.0
    bid_quantity: int = 0
    ask_quantity: int = 0


@dataclass(frozen=True)
class DhanPositionResponse:
    security_id: str
    exchange: str
    quantity: int
    average_price: float
    buy_qty: int = 0
    buy_avg: float = 0.0
    sell_qty: int = 0
    sell_avg: float = 0.0
    net_qty: int = 0
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    product_type: str = "INTRADAY"


@dataclass(frozen=True)
class DhanErrorResponse:
    code: str
    message: str


# ── Market Depth ─────────────────────────────────────────────────────


@dataclass(frozen=True)
class MarketDepthLevel:
    bid_price: float
    bid_qty: int
    ask_price: float
    ask_qty: int
    bid_orders: int
    ask_orders: int


@dataclass(frozen=True)
class MarketDepthSnapshot:
    security_id: str
    exchange: str
    timestamp: datetime
    levels: list[MarketDepthLevel]


@dataclass(frozen=True)
class FullDepthData:
    snapshot: MarketDepthSnapshot
    depth_level: int  # 20 or 200

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal


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
    price: Decimal
    order_type: str
    validity: str = "DAY"
    product_type: str = "INTRADAY"
    trigger_price: Decimal = field(default_factory=lambda: Decimal("0"))
    disclosed_quantity: int = 0
    after_market: bool = False
    amo_time: str = "OPEN"
    bo_profit_value: Decimal | None = None
    bo_stop_loss_value: Decimal | None = None
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
    last_traded_price: Decimal
    volume: int = 0
    open: Decimal = field(default_factory=lambda: Decimal("0"))
    high: Decimal = field(default_factory=lambda: Decimal("0"))
    low: Decimal = field(default_factory=lambda: Decimal("0"))
    close: Decimal = field(default_factory=lambda: Decimal("0"))
    change: Decimal = field(default_factory=lambda: Decimal("0"))
    change_percent: Decimal = field(default_factory=lambda: Decimal("0"))
    bid: Decimal = field(default_factory=lambda: Decimal("0"))
    ask: Decimal = field(default_factory=lambda: Decimal("0"))
    bid_quantity: int = 0
    ask_quantity: int = 0


@dataclass(frozen=True)
class DhanPositionResponse:
    security_id: str
    exchange: str
    quantity: int
    average_price: Decimal
    buy_qty: int = 0
    buy_avg: Decimal = field(default_factory=lambda: Decimal("0"))
    sell_qty: int = 0
    sell_avg: Decimal = field(default_factory=lambda: Decimal("0"))
    net_qty: int = 0
    realized_pnl: Decimal = field(default_factory=lambda: Decimal("0"))
    unrealized_pnl: Decimal = field(default_factory=lambda: Decimal("0"))
    product_type: str = "INTRADAY"


@dataclass(frozen=True)
class DhanErrorResponse:
    code: str
    message: str


# ── Market Depth ─────────────────────────────────────────────────────


@dataclass(frozen=True)
class MarketDepthLevel:
    bid_price: Decimal
    bid_qty: int
    ask_price: Decimal
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


# ── Unified error hierarchy (REF-01) ────────────────────────────────
# All Dhan-specific exceptions inherit from DhanError.
# _auth.py and _http.py import these instead of defining their own.

class DhanError(Exception):
    """Base for all Dhan adapter errors."""


class DhanAuthError(DhanError):
    """Authentication failed or token expired."""


class DhanTokenExpired(DhanAuthError):
    """Raised when the token has expired and refresh was requested."""


class DhanTokenRefreshThrottled(DhanAuthError):
    """Raised when TOTP generation is blocked by cooldown."""

    def __init__(self, message: str, *, remaining_seconds: float = 0.0) -> None:
        super().__init__(message)
        self.remaining_seconds = remaining_seconds


class DhanHttpError(DhanError):
    """Base for all Dhan HTTP transport errors."""


class RateLimitTimeout(DhanHttpError):
    """Rate limiter could not acquire a token within the timeout."""


class DhanRequestError(DhanHttpError):
    """4xx response from the API (excluding 401 and 429)."""

    def __init__(self, status: int, body: str, *args) -> None:
        self.status = status
        self.body = body
        super().__init__(f"HTTP {status}: {body[:200]}", *args)


class DhanServerError(DhanHttpError):
    """5xx response after exhausting retries."""

    def __init__(self, status: int, body: str, *args) -> None:
        self.status = status
        self.body = body
        super().__init__(f"HTTP {status}: {body[:200]}", *args)

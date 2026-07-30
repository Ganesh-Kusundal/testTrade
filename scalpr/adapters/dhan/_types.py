from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class DhanAuthResponse:
    access_token: str
    expires_at: str
    token_type: str


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

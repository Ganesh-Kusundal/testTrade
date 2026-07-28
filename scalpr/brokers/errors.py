"""Broker-agnostic error types shared by all adapters.

The API layer catches these to translate throttling into HTTP 503 +
Retry-After without importing any broker-specific package.
"""
from __future__ import annotations

from dataclasses import dataclass


# ── Domain error hierarchy ────────────────────────────────────────────────

class TradingError(Exception):
    """Base class for all domain-level trading errors."""


class AuthenticationError(TradingError):
    """Authentication failed or token expired."""


class InstrumentNotFound(TradingError):
    """Symbol could not be resolved in the instrument master."""


class AmbiguousInstrument(TradingError):
    """Symbol matches multiple instruments — more info required."""


class InvalidInstrument(TradingError):
    """Instrument definition is invalid (e.g. OPTIONS without strike)."""


class InvalidOrder(TradingError):
    """Order request fails validation (tick alignment, lot size, etc.)."""


class InsufficientMargin(TradingError):
    """Account does not have enough margin for the requested order."""


class RateLimitExceeded(TradingError):
    """Rate limit budget exhausted — the caller must back off."""

    def __init__(self, message: str = "", retry_after_s: float = 1.0) -> None:
        super().__init__(message)
        self.retry_after_s = retry_after_s


class ProviderUnavailable(TradingError):
    """Broker API or WebSocket connection is unreachable."""


class SubscriptionError(TradingError):
    """Market-feed subscription failed or was rejected."""


# ── Provider error metadata ───────────────────────────────────────────────

@dataclass(frozen=True)
class ProviderErrorInfo:
    """Retained metadata from a provider error for diagnostics."""
    provider: str
    code: str | None
    message: str
    request_id: str | None = None


# Backward-compatible alias
RateLimitError = RateLimitExceeded

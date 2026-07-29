"""Broker-agnostic error types shared by all adapters.

The API layer catches these to translate throttling into HTTP 503 +
Retry-After without importing any broker-specific package.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

# ── Domain error hierarchy ────────────────────────────────────────────────


class TradingError(Exception):
    """Base class for all domain-level trading errors.

    Attributes:
        message: Human-readable error description
        correlation_id: Request/order correlation ID for tracing
        context: Additional structured context for debugging
        timestamp: When the error occurred
    """

    def __init__(
        self,
        message: str = "",
        correlation_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.correlation_id = correlation_id or self._generate_correlation_id()
        self.context = context or {}
        self.timestamp = datetime.now(timezone.utc)
        super().__init__(message)

    @staticmethod
    def _generate_correlation_id() -> str:
        """Generate a short correlation ID for tracing."""
        return str(uuid.uuid4())[:8]

    def to_dict(self) -> dict[str, Any]:
        """Structured error representation for logging/API responses."""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "correlation_id": self.correlation_id,
            "context": self.context,
            "timestamp": self.timestamp.isoformat(),
        }

    def __str__(self) -> str:
        """User-friendly error with correlation ID."""
        return f"[{self.correlation_id}] {self.message}"


class AuthenticationError(TradingError):
    """Authentication failed or token expired."""


class InstrumentNotFound(TradingError):
    """Symbol could not be resolved in the instrument master."""


class AmbiguousInstrument(TradingError):
    """Symbol matches multiple instruments — more info required."""


class InvalidInstrument(TradingError):
    """Instrument definition is invalid (e.g. OPTIONS without strike)."""


class OptionChainNotSupported(TradingError):
    """Option chain is not available for this instrument."""


class InvalidOrder(TradingError):
    """Order request fails validation (tick alignment, lot size, etc.)."""


class InsufficientMargin(TradingError):
    """Account does not have enough margin for the requested order."""


class RateLimitExceeded(TradingError):
    """Rate limit budget exhausted — the caller must back off."""

    def __init__(
        self,
        message: str = "",
        retry_after_s: float = 1.0,
        correlation_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, correlation_id=correlation_id, context=context)
        self.retry_after_s = retry_after_s


class MarketDataError(TradingError):
    """Market data fetch failure (HTTP error, timeout, bad payload)."""


class OrderError(TradingError):
    """Order placement/modification/cancellation failure."""


class ProviderUnavailable(TradingError):
    """Broker API or WebSocket connection is unreachable."""


class SubscriptionError(TradingError):
    """Market-feed subscription failed or was rejected."""


class ConfigurationError(TradingError):
    """Missing or invalid configuration."""


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


# ── Execution-layer exceptions ──────────────────────────────────────────────


class RiskCheckFailed(TradingError):
    """Pre-trade risk check failed."""


class CircuitBreakerTripped(TradingError):
    """Circuit breaker prevented order submission."""


class PersistenceError(TradingError):
    """Order persistence failed."""


class OrderRateLimitExceeded(TradingError):
    """Order submission rate limit exceeded."""

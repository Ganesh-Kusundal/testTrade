"""Broker-agnostic error types — re-exported from :mod:`scalpr.domain.errors`.

This module exists for backward compatibility during the migration from
``scalpr.brokers.*`` to ``scalpr.domain.*``. All error types are defined in
:mod:`scalpr.domain.errors`. Importing from here still works but new code
should import from ``scalpr.domain.errors`` directly.
"""
from __future__ import annotations

# ruff: noqa: F401 — re-export all error types for backward compat
from scalpr.domain.errors import (
    AmbiguousInstrument,
    AuthenticationError,
    CircuitBreakerTripped,
    ConfigurationError,
    InstrumentNotFound,
    InsufficientMargin,
    InvalidInstrument,
    InvalidOrder,
    MarketDataError,
    OptionChainNotSupported,
    OrderError,
    OrderRateLimitExceeded,
    PersistenceError,
    ProviderErrorInfo,
    ProviderUnavailable,
    RateLimitError,
    RateLimitExceeded,
    RiskCheckFailed,
    SubscriptionError,
    TokenRefreshThrottled,
    TradingError,
)

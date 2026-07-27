"""Dhan broker exceptions.

All exceptions inherit from BrokerError for consistent error handling.
"""

from __future__ import annotations


class BrokerError(Exception):
    """Base exception for all broker errors."""
    pass


class InstrumentNotFoundError(BrokerError):
    """Instrument not found in resolver cache."""
    pass


class MarketDataError(BrokerError):
    """Market data fetch failure."""
    pass


class OrderError(BrokerError):
    """Order placement/modification/cancellation failure."""
    pass


class AuthenticationError(BrokerError):
    """Token expired or rejected."""
    pass


class ConfigurationError(BrokerError):
    """Missing or invalid configuration."""
    pass


class RateLimitError(BrokerError):
    """Rate limit exceeded."""
    pass

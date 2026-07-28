"""Dhan broker exceptions — unified under the broker-agnostic hierarchy.

Every Dhan-specific exception is a subclass of the corresponding
broker-agnostic base in ``scalpr.brokers.errors``, so callers can
catch either the Dhan-specific or the generic form.

Backward-compatible aliases preserve the old short names so existing
imports (e.g. from scalpr.brokers.dhan.exceptions import BrokerError)
continue to work for one release cycle.
"""
from __future__ import annotations

from scalpr.brokers.errors import AuthenticationError as _BaseAuthenticationError
from scalpr.brokers.errors import InstrumentNotFound as _BaseInstrumentNotFound
from scalpr.brokers.errors import MarketDataError as _BaseMarketDataError
from scalpr.brokers.errors import OrderError as _BaseOrderError
from scalpr.brokers.errors import RateLimitExceeded as _BaseRateLimitExceeded
from scalpr.brokers.errors import TradingError

# ── Dhan root ────────────────────────────────────────────────────────────────


class BrokerError(TradingError):
    """Base exception for all Dhan broker errors.

    Inherits from the broker-agnostic TradingError so that
    except TradingError catches Dhan errors as well.
    """


# ── Dhan-specific exceptions ─────────────────────────────────────────────────
# Each Dhan exception uses multiple inheritance:
#   1. The broker-agnostic base (for generic catching)
#   2. BrokerError (for backward-compatible Dhan-specific catching)


class DhanInstrumentNotFoundError(_BaseInstrumentNotFound, BrokerError):
    """Instrument not found in Dhan resolver cache."""


class DhanMarketDataError(_BaseMarketDataError, BrokerError):
    """Dhan market data fetch failure."""


class DhanOrderError(_BaseOrderError, BrokerError):
    """Dhan order placement/modification/cancellation failure."""


class DhanAuthenticationError(_BaseAuthenticationError, BrokerError):
    """Dhan token expired or rejected."""


class DhanConfigurationError(BrokerError):
    """Missing or invalid Dhan configuration."""


class DhanRateLimitError(_BaseRateLimitExceeded, BrokerError):
    """Dhan rate limit exceeded."""


# ── Backward-compatible aliases (old short names) ────────────────────────────

InstrumentNotFoundError = DhanInstrumentNotFoundError
MarketDataError = DhanMarketDataError
OrderError = DhanOrderError
AuthenticationError = DhanAuthenticationError
ConfigurationError = DhanConfigurationError
RateLimitError = DhanRateLimitError

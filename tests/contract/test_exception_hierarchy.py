"""Contract tests for the unified exception hierarchy (REF-002).

Verifies that every Dhan-specific exception is a proper subclass of the
corresponding broker-agnostic base in ``scalpr.brokers.errors``.
"""
import pytest


class TestExceptionHierarchy:
    """Dhan exceptions must extend broker-agnostic bases."""

    def test_dhan_auth_is_subclass_of_broker_agnostic(self):
        from scalpr.brokers.dhan.exceptions import DhanAuthenticationError
        from scalpr.brokers.errors import AuthenticationError

        assert issubclass(DhanAuthenticationError, AuthenticationError)

    def test_dhan_instrument_not_found_is_subclass(self):
        from scalpr.brokers.dhan.exceptions import DhanInstrumentNotFoundError
        from scalpr.brokers.errors import InstrumentNotFound

        assert issubclass(DhanInstrumentNotFoundError, InstrumentNotFound)

    def test_dhan_market_data_error_is_subclass(self):
        from scalpr.brokers.dhan.exceptions import DhanMarketDataError
        from scalpr.brokers.errors import MarketDataError

        assert issubclass(DhanMarketDataError, MarketDataError)

    def test_dhan_order_error_is_subclass(self):
        from scalpr.brokers.dhan.exceptions import DhanOrderError
        from scalpr.brokers.errors import OrderError

        assert issubclass(DhanOrderError, OrderError)

    def test_dhan_rate_limit_is_subclass(self):
        from scalpr.brokers.dhan.exceptions import DhanRateLimitError
        from scalpr.brokers.errors import RateLimitExceeded

        assert issubclass(DhanRateLimitError, RateLimitExceeded)

    def test_totp_rate_limit_is_token_refresh_throttled(self):
        """TOTP cooldown is part of the hierarchy — no RuntimeError outlier."""
        from scalpr.brokers.dhan._totp_cooldown import TotpRateLimitError
        from scalpr.brokers.errors import (
            AuthenticationError,
            TokenRefreshThrottled,
            TradingError,
        )

        assert issubclass(TotpRateLimitError, TokenRefreshThrottled)
        assert issubclass(TotpRateLimitError, AuthenticationError)
        assert issubclass(TotpRateLimitError, TradingError)

        exc = TotpRateLimitError("cooldown", remaining_seconds=90.0)
        assert exc.remaining_seconds == 90.0

    def test_broker_error_is_subclass_of_trading_error(self):
        from scalpr.brokers.dhan.exceptions import BrokerError
        from scalpr.brokers.errors import TradingError

        assert issubclass(BrokerError, TradingError)

    def test_dhan_configuration_error_is_subclass_of_trading_error(self):
        from scalpr.brokers.dhan.exceptions import DhanConfigurationError
        from scalpr.brokers.errors import TradingError

        assert issubclass(DhanConfigurationError, TradingError)

    def test_backward_compat_aliases_resolve(self):
        """Old short names must still be importable and point to Dhan classes."""
        from scalpr.brokers.dhan.exceptions import (
            AuthenticationError,
            BrokerError,
            ConfigurationError,
            InstrumentNotFoundError,
            MarketDataError,
            OrderError,
            RateLimitError,
        )

        assert AuthenticationError.__name__ == "DhanAuthenticationError"
        assert InstrumentNotFoundError.__name__ == "DhanInstrumentNotFoundError"
        assert MarketDataError.__name__ == "DhanMarketDataError"
        assert OrderError.__name__ == "DhanOrderError"
        assert RateLimitError.__name__ == "DhanRateLimitError"
        assert ConfigurationError.__name__ == "DhanConfigurationError"
        assert BrokerError.__name__ == "BrokerError"

    def test_catching_trading_error_catches_dhan_errors(self):
        """except TradingError must catch all Dhan exceptions."""
        from scalpr.brokers.dhan.exceptions import (
            DhanAuthenticationError,
            DhanInstrumentNotFoundError,
            DhanOrderError,
            DhanRateLimitError,
        )
        from scalpr.brokers.errors import TradingError

        for exc_cls in (
            DhanAuthenticationError,
            DhanInstrumentNotFoundError,
            DhanOrderError,
            DhanRateLimitError,
        ):
            with pytest.raises(TradingError):
                raise exc_cls("test")

    def test_catching_broker_error_still_works(self):
        """except BrokerError must still catch all Dhan-specific exceptions."""
        from scalpr.brokers.dhan.exceptions import (
            BrokerError,
            DhanAuthenticationError,
            DhanConfigurationError,
            DhanInstrumentNotFoundError,
            DhanMarketDataError,
            DhanOrderError,
            DhanRateLimitError,
        )

        for exc_cls in (
            DhanAuthenticationError,
            DhanInstrumentNotFoundError,
            DhanMarketDataError,
            DhanOrderError,
            DhanConfigurationError,
            DhanRateLimitError,
        ):
            with pytest.raises(BrokerError):
                raise exc_cls("test")

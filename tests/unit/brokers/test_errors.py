"""Tests for domain error hierarchy."""
import pytest

from scalpr.brokers.errors import (
    AmbiguousInstrument,
    AuthenticationError,
    InstrumentNotFound,
    InsufficientMargin,
    InvalidInstrument,
    InvalidOrder,
    ProviderErrorInfo,
    ProviderUnavailable,
    RateLimitExceeded,
    SubscriptionError,
    TradingError,
)


class TestTradingErrorHierarchy:
    """All trading errors derive from TradingError."""

    def test_authentication_error_is_trading_error(self):
        with pytest.raises(TradingError):
            raise AuthenticationError("Invalid token")

    def test_instrument_not_found_is_trading_error(self):
        with pytest.raises(TradingError):
            raise InstrumentNotFound("TCS not found")

    def test_ambiguous_instrument_is_trading_error(self):
        with pytest.raises(TradingError):
            raise AmbiguousInstrument("Multiple TCS found")

    def test_invalid_instrument_is_trading_error(self):
        with pytest.raises(TradingError):
            raise InvalidInstrument("Invalid instrument")

    def test_invalid_order_is_trading_error(self):
        with pytest.raises(TradingError):
            raise InvalidOrder("Invalid order")

    def test_insufficient_margin_is_trading_error(self):
        with pytest.raises(TradingError):
            raise InsufficientMargin("Insufficient margin")

    def test_rate_limit_exceeded_is_trading_error(self):
        with pytest.raises(TradingError):
            raise RateLimitExceeded("Rate limit exceeded")

    def test_provider_unavailable_is_trading_error(self):
        with pytest.raises(TradingError):
            raise ProviderUnavailable("Provider unavailable")

    def test_subscription_error_is_trading_error(self):
        with pytest.raises(TradingError):
            raise SubscriptionError("Subscription error")


class TestRateLimitExceeded:
    """RateLimitExceeded has retry_after_s attribute."""

    def test_default_retry_after(self):
        err = RateLimitExceeded("Rate limited")
        assert err.retry_after_s == 1.0

    def test_custom_retry_after(self):
        err = RateLimitExceeded("Rate limited", retry_after_s=5.0)
        assert err.retry_after_s == 5.0

    def test_message_preserved(self):
        err = RateLimitExceeded("Custom message")
        assert str(err) == "Custom message"


class TestProviderErrorInfo:
    """ProviderErrorInfo is a frozen dataclass."""

    def test_creation(self):
        info = ProviderErrorInfo(
            provider="dhan",
            code="429",
            message="Rate limit exceeded",
            request_id="req-123",
        )
        assert info.provider == "dhan"
        assert info.code == "429"
        assert info.message == "Rate limit exceeded"
        assert info.request_id == "req-123"

    def test_optional_request_id(self):
        info = ProviderErrorInfo(
            provider="dhan",
            code="500",
            message="Internal error",
        )
        assert info.request_id is None

    def test_frozen(self):
        info = ProviderErrorInfo(
            provider="dhan",
            code="429",
            message="Rate limit",
        )
        with pytest.raises(AttributeError):
            info.provider = "other"

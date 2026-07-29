"""Tests for enhanced exception hierarchy with correlation IDs."""
import json
from datetime import datetime

from scalpr.brokers.errors import (
    AuthenticationError,
    CircuitBreakerTripped,
    ConfigurationError,
    InstrumentNotFound,
    OrderRateLimitExceeded,
    PersistenceError,
    RateLimitExceeded,
    RiskCheckFailed,
    TradingError,
)


class TestTradingErrorCorrelationId:
    """TradingError has correlation_id for tracing."""

    def test_auto_generates_correlation_id(self):
        err = TradingError("Test error")
        assert err.correlation_id is not None
        assert len(err.correlation_id) == 8  # UUID prefix

    def test_accepts_custom_correlation_id(self):
        err = TradingError("Test error", correlation_id="custom12")
        assert err.correlation_id == "custom12"

    def test_correlation_id_in_str(self):
        err = TradingError("Test error", correlation_id="abc12345")
        assert "[abc12345]" in str(err)
        assert "Test error" in str(err)


class TestTradingErrorContext:
    """TradingError has structured context for debugging."""

    def test_empty_context_by_default(self):
        err = TradingError("Test error")
        assert err.context == {}

    def test_accepts_context(self):
        ctx = {"symbol": "TCS", "order_id": "123"}
        err = TradingError("Test error", context=ctx)
        assert err.context == ctx
        assert err.context["symbol"] == "TCS"

    def test_timestamp_auto_set(self):
        err = TradingError("Test error")
        assert err.timestamp is not None
        assert isinstance(err.timestamp, datetime)


class TestTradingErrorToDict:
    """TradingError.to_dict() provides structured error representation."""

    def test_to_dict_contains_all_fields(self):
        err = TradingError(
            "Test error",
            correlation_id="abc12345",
            context={"symbol": "TCS"},
        )
        d = err.to_dict()

        assert d["error"] == "TradingError"
        assert d["message"] == "Test error"
        assert d["correlation_id"] == "abc12345"
        assert d["context"] == {"symbol": "TCS"}
        assert "timestamp" in d

    def test_to_dict_serializable(self):
        err = TradingError("Test error", context={"key": "value"})
        d = err.to_dict()
        # Should be JSON serializable
        json_str = json.dumps(d, default=str)
        assert "Test error" in json_str


class TestSubclassInheritance:
    """All subclasses inherit correlation_id behavior."""

    def test_authentication_error_has_correlation_id(self):
        err = AuthenticationError("Invalid token", correlation_id="auth1234")
        assert err.correlation_id == "auth1234"
        assert isinstance(err, TradingError)

    def test_instrument_not_found_has_context(self):
        err = InstrumentNotFound(
            "TCS not found",
            context={"symbol": "TCS", "exchange": "NSE"},
        )
        assert err.context["symbol"] == "TCS"

    def test_rate_limit_exceeded_preserves_retry_after(self):
        err = RateLimitExceeded(
            "Rate limited",
            retry_after_s=5.0,
            correlation_id="rate1234",
        )
        assert err.retry_after_s == 5.0
        assert err.correlation_id == "rate1234"


class TestExecutionLayerExceptions:
    """Execution-layer exceptions inherit from TradingError."""

    def test_risk_check_failed_is_trading_error(self):
        err = RiskCheckFailed("Risk check failed")
        assert isinstance(err, TradingError)
        assert err.correlation_id is not None

    def test_circuit_breaker_tripped_has_context(self):
        err = CircuitBreakerTripped(
            "Circuit breaker tripped",
            context={"daily_loss": "10000", "portfolio_value": "100000"},
        )
        assert err.context["daily_loss"] == "10000"

    def test_persistence_error_is_trading_error(self):
        err = PersistenceError("Persistence failed")
        assert isinstance(err, TradingError)

    def test_order_rate_limit_exceeded_is_trading_error(self):
        err = OrderRateLimitExceeded("Rate limit exceeded")
        assert isinstance(err, TradingError)

    def test_configuration_error_is_trading_error(self):
        err = ConfigurationError("Missing config")
        assert isinstance(err, TradingError)


class TestErrorFormatter:
    """ErrorFormatter provides consistent formatting."""

    def test_for_log_returns_dict(self):
        from scalpr.observability.error_formatter import ErrorFormatter

        err = TradingError("Test error", correlation_id="abc12345")
        result = ErrorFormatter.for_log(err)

        assert isinstance(result, dict)
        assert result["error"] == "TradingError"
        assert result["correlation_id"] == "abc12345"

    def test_for_api_returns_structured_response(self):
        from scalpr.observability.error_formatter import ErrorFormatter

        err = TradingError("Test error", correlation_id="abc12345")
        result = ErrorFormatter.for_api(err)

        assert "code" in result
        assert "message" in result
        assert "correlation_id" in result
        assert result["correlation_id"] == "abc12345"

    def test_for_user_returns_string(self):
        from scalpr.observability.error_formatter import ErrorFormatter

        err = TradingError("Test error", correlation_id="abc12345")
        result = ErrorFormatter.for_user(err)

        assert isinstance(result, str)
        assert "[abc12345]" in result
        assert "Test error" in result

    def test_handles_generic_exception(self):
        from scalpr.observability.error_formatter import ErrorFormatter

        err = ValueError("Generic error")
        result = ErrorFormatter.for_api(err)

        assert result["code"] == "InternalError"
        assert "unexpected" in result["message"].lower()

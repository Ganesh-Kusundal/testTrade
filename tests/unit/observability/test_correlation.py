"""Tests for correlation ID context management and logging framework."""
import json
import logging

from scalpr.observability.correlation import (
    CorrelationIdFilter,
    correlation_context,
    get_correlation_id,
    get_request_id,
    request_context,
    set_correlation_id,
    set_request_id,
)
from scalpr.observability.logging import (
    DevelopmentFormatter,
    JsonFormatter,
    VerboseControlFilter,
)


class TestCorrelationIdContext:
    """Correlation ID context management."""

    def test_set_and_get_correlation_id(self):
        cid = set_correlation_id("test1234")
        assert cid == "test1234"
        assert get_correlation_id() == "test1234"

    def test_auto_generates_if_none(self):
        cid = set_correlation_id()
        assert cid is not None
        assert len(cid) == 8

    def test_set_and_get_request_id(self):
        rid = set_request_id("req12345")
        assert rid == "req12345"
        assert get_request_id() == "req12345"


class TestCorrelationContextManager:
    """correlation_context() context manager."""

    def test_sets_correlation_id_in_context(self):
        with correlation_context("abc12345") as cid:
            assert cid == "abc12345"
            assert get_correlation_id() == "abc12345"

    def test_restores_previous_value(self):
        set_correlation_id("original")
        with correlation_context("temporary"):
            assert get_correlation_id() == "temporary"
        assert get_correlation_id() == "original"

    def test_auto_generates_if_none(self):
        with correlation_context() as cid:
            assert cid is not None
            assert len(cid) == 8


class TestRequestContextManager:
    """request_context() context manager."""

    def test_sets_request_id_in_context(self):
        with request_context("req12345") as rid:
            assert rid == "req12345"
            assert get_request_id() == "req12345"

    def test_restores_previous_value(self):
        set_request_id("original")
        with request_context("temporary"):
            assert get_request_id() == "temporary"
        assert get_request_id() == "original"


class TestCorrelationIdFilter:
    """CorrelationIdFilter injects IDs into log records."""

    def test_injects_correlation_id(self):
        filter = CorrelationIdFilter()
        set_correlation_id("abc12345")

        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="test", args=(), exc_info=None,
        )
        filter.filter(record)

        assert record.correlation_id == "abc12345"

    def test_injects_request_id(self):
        filter = CorrelationIdFilter()
        set_request_id("req12345")

        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="test", args=(), exc_info=None,
        )
        filter.filter(record)

        assert record.request_id == "req12345"

    def test_defaults_to_none_when_empty(self):
        """When context is empty string, filter returns 'none'."""
        from scalpr.observability.correlation import current_correlation_id, current_request_id
        filter = CorrelationIdFilter()
        # Reset context vars to empty
        current_correlation_id.set("")
        current_request_id.set("")

        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="test", args=(), exc_info=None,
        )
        filter.filter(record)

        assert record.correlation_id == "none"
        assert record.request_id == "none"


class TestVerboseControlFilter:
    """VerboseControlFilter controls high-volume logger output."""

    def test_allows_warnings_always(self):
        filter = VerboseControlFilter(verbose=False)

        record = logging.LogRecord(
            name="scalpr.adapters.dhan._market_data_client",
            level=logging.WARNING, pathname="", lineno=0,
            msg="test", args=(), exc_info=None,
        )

        assert filter.filter(record) is True

    def test_suppresses_info_in_non_verbose(self):
        filter = VerboseControlFilter(verbose=False)

        record = logging.LogRecord(
            name="scalpr.adapters.dhan._market_data_client",
            level=logging.INFO, pathname="", lineno=0,
            msg="test", args=(), exc_info=None,
        )

        assert filter.filter(record) is False

    def test_allows_info_in_verbose_mode(self):
        filter = VerboseControlFilter(verbose=True)

        record = logging.LogRecord(
            name="scalpr.adapters.dhan._market_data_client",
            level=logging.INFO, pathname="", lineno=0,
            msg="test", args=(), exc_info=None,
        )

        assert filter.filter(record) is True

    def test_allows_non_verbose_logger(self):
        filter = VerboseControlFilter(verbose=False)

        record = logging.LogRecord(
            name="scalpr.execution.order_router",  # Not in VERBOSE_LOGGERS
            level=logging.INFO, pathname="", lineno=0,
            msg="test", args=(), exc_info=None,
        )

        assert filter.filter(record) is True


class TestJsonFormatter:
    """JsonFormatter outputs structured JSON with correlation IDs."""

    def test_includes_correlation_id(self):
        formatter = JsonFormatter()
        set_correlation_id("abc12345")

        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="test message", args=(), exc_info=None,
        )
        record.correlation_id = "abc12345"
        record.request_id = "req12345"

        output = formatter.format(record)
        log_entry = json.loads(output)

        assert log_entry["correlation_id"] == "abc12345"
        assert log_entry["request_id"] == "req12345"
        assert log_entry["message"] == "test message"

    def test_includes_context(self):
        formatter = JsonFormatter()

        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="test", args=(), exc_info=None,
        )
        record.correlation_id = "none"
        record.request_id = "none"
        record.context = {"symbol": "TCS", "order_id": "123"}

        output = formatter.format(record)
        log_entry = json.loads(output)

        assert log_entry["context"]["symbol"] == "TCS"


class TestDevelopmentFormatter:
    """DevelopmentFormatter includes correlation_id in output."""

    def test_includes_correlation_id(self):
        formatter = DevelopmentFormatter()

        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="test message", args=(), exc_info=None,
        )
        record.correlation_id = "abc12345"

        output = formatter.format(record)

        assert "[abc12345]" in output
        assert "test message" in output

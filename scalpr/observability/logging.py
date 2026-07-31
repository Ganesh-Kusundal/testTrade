"""Structured logging configuration for SCALPR trading platform.

Provides environment-aware logging with:
- JSON formatting for production (structured logs with correlation IDs)
- Human-readable formatting for development
- Verbose/non-verbose mode control for high-volume loggers
- Automatic correlation ID injection via CorrelationIdFilter
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, ClassVar

from scalpr.domain.errors import TradingError
from scalpr.observability.correlation import CorrelationIdFilter


class JsonFormatter(logging.Formatter):
    """Production JSON log formatter with correlation IDs.

    Outputs structured JSON log entries suitable for log aggregation
    systems (ELK, CloudWatch, etc.). Includes correlation_id and
    request_id for request tracing.

    Attributes set on LogRecord:
        correlation_id: From CorrelationIdFilter
        request_id: From CorrelationIdFilter
        context: Optional structured context dict
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "service": "scalpr",
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": getattr(record, "correlation_id", "none"),
            "request_id": getattr(record, "request_id", "none"),
        }

        # Add structured context if present (from extra={})
        if hasattr(record, "context"):
            log_entry["context"] = record.context

        # Add exception info with structured error format
        if record.exc_info and record.exc_info[0] is not None:
            error = record.exc_info[1]
            if isinstance(error, TradingError):
                log_entry["error"] = error.to_dict()
            else:
                log_entry["error"] = {
                    "type": type(error).__name__,
                    "message": str(error),
                }
            # Include traceback for errors
            if record.exc_info[0] is not None:
                log_entry["traceback"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str)


class VerboseControlFilter(logging.Filter):
    """Control log verbosity based on verbose mode.

    In non-verbose mode, suppresses DEBUG and INFO messages from
    high-volume loggers (market data, WebSocket, scanner, strategy).
    WARNING and above always pass through.

    Args:
        verbose: If True, show all messages. If False, suppress
                 high-volume loggers to WARNING+ only.
    """

    # Loggers that produce high-volume output
    VERBOSE_LOGGERS: ClassVar[set[str]] = {
        "scalpr.adapters.dhan._market_data_client",
        "scalpr.adapters.dhan._ws",
        "scalpr.scanner",
        "scalpr.strategy",
    }

    def __init__(self, verbose: bool = False) -> None:
        super().__init__()
        self.verbose = verbose

    def filter(self, record: logging.LogRecord) -> bool:
        # Always show WARNING+ regardless of verbose mode
        if record.levelno >= logging.WARNING:
            return True

        # In non-verbose mode, suppress DEBUG/INFO from verbose loggers
        return not (not self.verbose and record.name in self.VERBOSE_LOGGERS)


class DevelopmentFormatter(logging.Formatter):
    """Human-readable log formatter for development.

    Includes correlation_id in output for tracing.
    Format: TIMESTAMP | LEVEL | LOGGER | [CORRELATION_ID] MESSAGE
    """

    def __init__(self) -> None:
        super().__init__(
            "%(asctime)s | %(levelname)-8s | %(name)s | [%(correlation_id)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )


def setup_logging(
    environment: str = "development",
    verbose: bool = False,
    correlation_ids: bool = True,
) -> None:
    """Configure logging with verbose control and correlation IDs.

    Args:
        environment: "development" (human-readable) or "production" (JSON)
        verbose: If True, show DEBUG/INFO from all loggers. If False,
                 suppress high-volume loggers to WARNING+ only.
        correlation_ids: If True, inject correlation IDs into all log records.

    Usage::

        # Development with verbose output
        setup_logging(environment="development", verbose=True)

        # Production with JSON logs and correlation IDs
        setup_logging(environment="production", verbose=False, correlation_ids=True)

        # Quiet mode (only warnings and errors from high-volume loggers)
        setup_logging(environment="development", verbose=False)
    """
    # Select formatter based on environment
    formatter: logging.Formatter
    formatter = JsonFormatter() if environment == "production" else DevelopmentFormatter()

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if environment == "development" else logging.INFO)

    # Clear existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Create and configure handler
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    # Add correlation ID filter if enabled
    if correlation_ids:
        handler.addFilter(CorrelationIdFilter())

    # Add verbose control filter
    handler.addFilter(VerboseControlFilter(verbose=verbose))

    root_logger.addHandler(handler)

    # Suppress noisy third-party loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("websockets").setLevel(logging.WARNING)

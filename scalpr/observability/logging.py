"""Structured logging configuration for SCALPR trading platform."""

import json
import logging
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):
    """JSON log formatter for production observability."""

    def format(self, record):
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "service": "scalpr",
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add trace_id if present
        if hasattr(record, "trace_id"):
            log_entry["trace_id"] = record.trace_id

        # Add exception info if present
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["error"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)


def setup_logging(environment: str = "development") -> None:
    """Configure logging based on environment.

    Args:
        environment: "development" for human-readable logs, "production" for JSON
    """
    # Create appropriate formatter
    if environment == "production":
        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if environment == "development" else logging.INFO)

    # Update all existing handlers
    for handler in root_logger.handlers:
        handler.setFormatter(formatter)

    # If no handlers exist, add a StreamHandler
    if not root_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)

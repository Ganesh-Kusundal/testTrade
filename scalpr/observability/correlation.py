"""Correlation ID context management for request tracing.

Provides async-safe correlation ID propagation through contextvars,
automatic injection into log records, and context managers for
scoped operations.
"""
from __future__ import annotations

import logging
import uuid
from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar

# Global context variables for correlation (async-safe)
current_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="")
current_request_id: ContextVar[str] = ContextVar("request_id", default="")


class CorrelationIdFilter(logging.Filter):
    """Inject correlation_id and request_id into all log records automatically.

    Add this filter to handlers or loggers to ensure every log record
    has correlation_id and request_id attributes for structured logging.

    Usage::

        handler = logging.StreamHandler()
        handler.addFilter(CorrelationIdFilter())
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = current_correlation_id.get() or "none"
        record.request_id = current_request_id.get() or "none"
        return True


def set_correlation_id(correlation_id: str | None = None) -> str:
    """Set correlation ID for current context.

    Args:
        correlation_id: ID to set. If None, generates a new one.

    Returns:
        The correlation ID that was set.
    """
    cid = correlation_id or str(uuid.uuid4())[:8]
    current_correlation_id.set(cid)
    return cid


def get_correlation_id() -> str:
    """Get current correlation ID.

    Returns:
        Current correlation ID or empty string if not set.
    """
    return current_correlation_id.get()


def set_request_id(request_id: str | None = None) -> str:
    """Set request ID for current HTTP request context.

    Args:
        request_id: ID to set. If None, generates a new one.

    Returns:
        The request ID that was set.
    """
    rid = request_id or str(uuid.uuid4())[:8]
    current_request_id.set(rid)
    return rid


def get_request_id() -> str:
    """Get current request ID.

    Returns:
        Current request ID or empty string if not set.
    """
    return current_request_id.get()


@contextmanager
def correlation_context(
    correlation_id: str | None = None,
) -> Generator[str, None, None]:
    """Context manager for correlation-scoped operations.

    Sets a correlation ID for the duration of the context, then
    restores the previous value. Useful for tracing request flows.

    Usage::

        with correlation_context("abc12345") as cid:
            logger.info("Processing request")  # Will include correlation_id=abc12345
            # ... process request ...

    Args:
        correlation_id: ID to use. If None, generates a new one.

    Yields:
        The correlation ID in use.
    """
    cid = correlation_id or str(uuid.uuid4())[:8]
    token = current_correlation_id.set(cid)
    try:
        yield cid
    finally:
        current_correlation_id.reset(token)


@contextmanager
def request_context(
    request_id: str | None = None,
) -> Generator[str, None, None]:
    """Context manager for request-scoped operations.

    Sets a request ID for the duration of the context, then
    restores the previous value.

    Usage::

        with request_context() as rid:
            logger.info("Handling HTTP request")  # Will include request_id
            # ... handle request ...

    Args:
        request_id: ID to use. If None, generates a new one.

    Yields:
        The request ID in use.
    """
    rid = request_id or str(uuid.uuid4())[:8]
    token = current_request_id.set(rid)
    try:
        yield rid
    finally:
        current_request_id.reset(token)

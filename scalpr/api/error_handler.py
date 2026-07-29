"""API error handler for FastAPI.

Converts TradingError exceptions to structured JSON responses with
appropriate HTTP status codes. Includes correlation_id for client-side
tracing.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse

from scalpr.brokers.errors import (
    AuthenticationError,
    CircuitBreakerTripped,
    ConfigurationError,
    InstrumentNotFound,
    InsufficientMargin,
    OrderRateLimitExceeded,
    PersistenceError,
    ProviderUnavailable,
    RateLimitExceeded,
    RiskCheckFailed,
    TradingError,
)
from scalpr.observability.error_formatter import ErrorFormatter

logger = logging.getLogger(__name__)


def _status_code_for(error: TradingError) -> int:
    """Map TradingError subclass to HTTP status code.

    Args:
        error: The TradingError to map.

    Returns:
        Appropriate HTTP status code.
    """
    # Authentication errors → 401
    if isinstance(error, AuthenticationError):
        return 401

    # Configuration errors → 400
    if isinstance(error, ConfigurationError):
        return 400

    # Not found errors → 404
    if isinstance(error, InstrumentNotFound):
        return 404

    # Risk/rejection errors → 400
    if isinstance(error, (InsufficientMargin, RiskCheckFailed)):
        return 400

    # Rate limit errors → 429
    if isinstance(error, (RateLimitExceeded, OrderRateLimitExceeded)):
        return 429

    # System errors → 503
    if isinstance(error, (ProviderUnavailable, CircuitBreakerTripped, PersistenceError)):
        return 503

    # Default for other TradingErrors
    return 400


async def trading_error_handler(request: Request, exc: TradingError) -> JSONResponse:
    """Convert TradingError to structured JSON API response.

    Args:
        request: The FastAPI request that caused the error.
        exc: The TradingError exception.

    Returns:
        JSONResponse with error details and correlation_id.
    """
    status_code = _status_code_for(exc)
    content = ErrorFormatter.for_api(exc)

    # Log the error with structured context
    logger.error(
        "API error: %s",
        exc.message,
        extra={
            "context": {
                "status_code": status_code,
                "path": request.url.path,
                "method": request.method,
                **exc.context,
            }
        },
        exc_info=True,
    )

    return JSONResponse(
        status_code=status_code,
        content=content,
        headers={"X-Correlation-ID": exc.correlation_id},
    )


async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions with generic error response.

    Hides internal error details from API clients while logging
    the full exception for debugging.

    Args:
        request: The FastAPI request that caused the error.
        exc: The exception.

    Returns:
        JSONResponse with generic error message.
    """
    # Log the full exception for debugging
    logger.exception(
        "Unexpected error in API: %s",
        exc,
        extra={"context": {"path": request.url.path, "method": request.method}},
    )

    return JSONResponse(
        status_code=500,
        content={
            "code": "InternalError",
            "message": "An unexpected error occurred",
        },
    )


def register_exception_handlers(app: Any) -> None:
    """Register exception handlers on a FastAPI app.

    Args:
        app: FastAPI application instance.
    """
    app.add_exception_handler(TradingError, trading_error_handler)
    app.add_exception_handler(Exception, generic_error_handler)

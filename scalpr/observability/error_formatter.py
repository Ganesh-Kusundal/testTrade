"""Structured error formatting for different output contexts.

Provides consistent error formatting for logs, API responses, and
user-facing messages. Integrates with TradingError's structured
attributes (correlation_id, context, timestamp).
"""
from __future__ import annotations

from typing import Any

from scalpr.domain.errors import TradingError


class ErrorFormatter:
    """Format exceptions for different contexts (logs, API, user-facing).

    All methods handle both TradingError (with structured attributes)
    and generic exceptions gracefully.

    Usage::

        try:
            # ... trading operation ...
        except TradingError as e:
            # For structured logging
            logger.error("Operation failed", extra=ErrorFormatter.for_log(e))

            # For API response
            return JSONResponse(
                status_code=400,
                content=ErrorFormatter.for_api(e),
            )

            # For user display
            print(ErrorFormatter.for_user(e))
    """

    @staticmethod
    def for_log(error: Exception) -> dict[str, Any]:
        """Structured dict for JSON logging.

        Returns a dict suitable for structured log output. Includes
        correlation_id, context, and timestamp for TradingError.

        Args:
            error: The exception to format.

        Returns:
            Dict with error details for logging.
        """
        if isinstance(error, TradingError):
            return error.to_dict()

        # Generic exception — minimal structure
        return {
            "error": type(error).__name__,
            "message": str(error),
        }

    @staticmethod
    def for_api(error: Exception) -> dict[str, Any]:
        """API response format.

        Returns a dict suitable for JSON API responses. Includes
        error code (class name), message, and correlation_id for
        client-side tracing.

        Args:
            error: The exception to format.

        Returns:
            Dict with error details for API response.
        """
        if isinstance(error, TradingError):
            return {
                "code": error.__class__.__name__,
                "message": error.message,
                "correlation_id": error.correlation_id,
            }

        # Generic exception — hide details from API clients
        return {
            "code": "InternalError",
            "message": "An unexpected error occurred",
        }

    @staticmethod
    def for_user(error: Exception) -> str:
        """Human-readable one-liner.

        Returns a concise error string with correlation_id for
        support tracing. Suitable for CLI output, notifications,
        and error dialogs.

        Args:
            error: The exception to format.

        Returns:
            User-friendly error string.
        """
        if isinstance(error, TradingError):
            return f"[{error.correlation_id}] {error.message}"

        # Generic exception — just the message
        return str(error)

    @staticmethod
    def for_exception_chain(error: Exception) -> list[dict[str, Any]]:
        """Format exception chain for debugging.

        Walks the __cause__ chain and returns a list of error dicts,
        useful for debugging and detailed error reports.

        Args:
            error: The exception to format.

        Returns:
            List of error dicts from most recent to root cause.
        """
        chain: list[dict[str, Any]] = []
        current: BaseException | None = error

        while current is not None:
            if isinstance(current, TradingError):
                chain.append(current.to_dict())
            else:
                chain.append({
                    "error": type(current).__name__,
                    "message": str(current),
                })
            current = current.__cause__

        return chain

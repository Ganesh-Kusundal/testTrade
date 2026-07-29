"""Contract: only TradingError subclasses escape the Gateway facade.

This is the invariant that the 2026-07 TOTP cooldown crash violated —
``TotpRateLimitError(RuntimeError)`` escaped ``Gateway.__init__`` untyped.
Any auth/connection failure must surface as a ``TradingError`` (with
correlation_id and context) so callers have exactly one error family
to handle.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from scalpr.brokers.errors import TokenRefreshThrottled, TradingError

_CONFIG = {"client_id": "CID", "access_token": "tok"}


def _gateway_with_connect_raising(exc: BaseException) -> None:
    """Construct Gateway(auto_connect=True) with connect() raising exc."""
    from scalpr.brokers.gateway.facade import Gateway

    with patch(
        "scalpr.brokers.dhan.connection.DhanConnection.connect",
        side_effect=exc,
    ):
        Gateway(broker="dhan", config=_CONFIG, auto_connect=True)


class TestGatewayErrorInvariant:
    """Gateway() must never leak a non-TradingError, whatever connect() raises."""

    @pytest.mark.parametrize(
        "raised",
        [
            RuntimeError("untyped failure"),
            ValueError("bad payload"),
            ConnectionError("socket reset"),
            OSError("network down"),
        ],
        ids=["runtime", "value", "connection", "os"],
    )
    def test_untyped_connect_failures_are_wrapped(self, raised: BaseException) -> None:
        with pytest.raises(TradingError) as exc_info:
            _gateway_with_connect_raising(raised)
        assert exc_info.value.context.get("broker") == "dhan"

    def test_totp_cooldown_surfaces_typed_with_wait_guidance(self) -> None:
        """Regression for the 2026-07 crash: cooldown during connect must
        surface as TradingError with remaining_seconds context, not escape
        as an untyped RuntimeError."""
        from scalpr.brokers.dhan._totp_cooldown import TotpRateLimitError

        with pytest.raises(TradingError) as exc_info:
            _gateway_with_connect_raising(
                TotpRateLimitError("cooldown active", remaining_seconds=108.0)
            )

        assert exc_info.value.context.get("reason") == "totp_cooldown"
        assert exc_info.value.context.get("remaining_seconds") == 108.0

    def test_token_refresh_throttled_is_trading_error(self) -> None:
        """The broker-agnostic throttle type is itself a TradingError, so
        even an unwrapped escape stays inside the single error family."""
        assert issubclass(TokenRefreshThrottled, TradingError)

    def test_typed_trading_errors_pass_through_unwrapped(self) -> None:
        """Existing TradingErrors keep their type (and correlation_id)."""
        from scalpr.brokers.errors import AuthenticationError

        original = AuthenticationError("token rejected")
        with pytest.raises(AuthenticationError) as exc_info:
            _gateway_with_connect_raising(original)
        assert exc_info.value is original

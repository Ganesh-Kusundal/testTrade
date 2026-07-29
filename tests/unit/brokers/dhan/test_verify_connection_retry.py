"""_verify_connection retry policy — 401 always forces token regeneration.

A 401 from Dhan means the token was rejected, even if its JWT locally
looks fresh. The retry policy therefore forces a token regeneration on
each 401 rather than reusing the same token, because reusing an already-
rejected token cannot succeed.

Cooldown waiting is owned by auth.py (ensure_fresh_token with
wait_for_cooldown=True) — _verify_connection never sleeps itself.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from scalpr.brokers.dhan._totp_cooldown import TotpRateLimitError
from scalpr.brokers.dhan.connection import DhanConnection
from scalpr.brokers.dhan.exceptions import AuthenticationError


@pytest.fixture
def connection() -> DhanConnection:
    conn = DhanConnection({"client_id": "CID", "access_token": "tok-fresh"})
    conn._client = MagicMock()
    conn._client.access_token = "tok-fresh"
    return conn


class TestVerifyRetryFreshToken:
    """Fresh token + 401 → force regenerate and retry with new token."""

    def test_force_mints_on_401(self, connection: DhanConnection) -> None:
        connection._client.get.side_effect = [
            AuthenticationError("401 on GET /profile"),
            {"dataPlan": "active", "dataValidity": "2026-07-30", "activeSegment": []},
        ]
        with patch(
            "scalpr.brokers.dhan.connection.ensure_fresh_token",
            return_value="tok-new",
        ) as mint:
            connection._verify_connection()

        mint.assert_called_with(force=True, wait_for_cooldown=True)
        connection._client.update_token.assert_called_with("tok-new")
        assert connection._client.get.call_count == 2

    def test_never_reuses_rejected_token(self, connection: DhanConnection) -> None:
        connection._client.get.side_effect = AuthenticationError("401")
        with (
            patch(
                "scalpr.brokers.dhan.connection.ensure_fresh_token",
                return_value="tok-new",
            ) as mint,
            pytest.raises(AuthenticationError),
        ):
            connection._verify_connection()

        # Retries happen on attempts 1 and 2; attempt 3 raises directly.
        assert mint.call_count == 2
        assert all(call.kwargs.get("force") is True for call in mint.call_args_list)
        assert connection._client.get.call_count == 3


class TestVerifyRetryExhaustion:
    def test_raises_after_all_attempts(self, connection: DhanConnection) -> None:
        connection._client.get.side_effect = AuthenticationError("401")
        with (
            patch(
                "scalpr.brokers.dhan.connection.ensure_fresh_token",
                return_value="tok-new",
            ),
            pytest.raises(AuthenticationError),
        ):
            connection._verify_connection()

        assert connection._client.get.call_count == 3


class TestVerifyCooldownAwareRetry:
    """Cooldown handling delegates to ensure_fresh_token — no local sleeps."""

    def test_cooldown_during_verify_delegates_to_auth_layer(
        self, connection: DhanConnection
    ) -> None:
        """TotpRateLimitError from /profile is an AuthenticationError —
        retried through the same single handler, which asks auth.py to
        wait out the cooldown."""
        connection._client.get.side_effect = [
            TotpRateLimitError("cooldown active", remaining_seconds=90.0),
            {"dataPlan": "active", "dataValidity": "2026-07-30", "activeSegment": []},
        ]

        with (
            patch(
                "scalpr.brokers.dhan.connection.ensure_fresh_token",
                return_value="tok-new",
            ) as mint,
            patch("time.sleep") as mock_sleep,
        ):
            connection._verify_connection()

        # No sleeping in _verify_connection — auth.py owns the wait.
        mock_sleep.assert_not_called()
        mint.assert_called_once_with(force=True, wait_for_cooldown=True)
        connection._client.update_token.assert_called_with("tok-new")

    def test_raises_totp_rate_limit_after_all_attempts(
        self, connection: DhanConnection
    ) -> None:
        connection._client.get.side_effect = TotpRateLimitError(
            "cooldown", remaining_seconds=120.0
        )

        with (
            patch(
                "scalpr.brokers.dhan.connection.ensure_fresh_token",
                return_value="tok-new",
            ),
            pytest.raises(TotpRateLimitError, match="cooldown"),
        ):
            connection._verify_connection()

        # 3 attempts: 1st and 2nd fail + remint; 3rd fails and raises.
        assert connection._client.get.call_count == 3

    def test_persistent_cooldown_from_refresh_propagates_typed(
        self, connection: DhanConnection
    ) -> None:
        """If ensure_fresh_token itself is still throttled after waiting,
        the typed error escapes (it is an AuthenticationError, so connect()
        and the Gateway facade surface it with remaining_seconds)."""
        connection._client.get.side_effect = AuthenticationError("401")

        with (
            patch(
                "scalpr.brokers.dhan.connection.ensure_fresh_token",
                side_effect=TotpRateLimitError("cooldown", remaining_seconds=90.0),
            ) as mint,
            pytest.raises(TotpRateLimitError, match="cooldown") as exc_info,
        ):
            connection._verify_connection()

        mint.assert_called_once_with(force=True, wait_for_cooldown=True)
        assert exc_info.value.remaining_seconds == 90.0

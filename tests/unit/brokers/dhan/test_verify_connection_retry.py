"""_verify_connection retry policy — never burn a TOTP mint on a fresh token.

A 401 on a freshly minted token is Dhan's server-side activation delay,
not staleness. The retry must reuse the SAME token. Minting is allowed
only when the current token is actually stale/expiring (K-027).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from scalpr.brokers.dhan.connection import DhanConnection
from scalpr.brokers.dhan.exceptions import AuthenticationError


@pytest.fixture
def connection() -> DhanConnection:
    conn = DhanConnection({"client_id": "CID", "access_token": "tok-fresh"})
    conn._client = MagicMock()
    conn._client.access_token = "tok-fresh"
    return conn


class TestVerifyRetryFreshToken:
    """Fresh token + 401 → retry same token, zero mints."""

    def test_retries_same_token_without_minting(self, connection: DhanConnection) -> None:
        connection._client.get.side_effect = [
            AuthenticationError("401 on GET /profile"),
            {"dataPlan": "active", "dataValidity": "2026-07-30", "activeSegment": []},
        ]
        with (
            patch("scalpr.brokers.dhan.connection.ensure_fresh_token") as mint,
            patch("scalpr.brokers.dhan.connection.is_token_fresh", return_value=True),
            patch("time.sleep"),
        ):
            connection._verify_connection()

        mint.assert_not_called()
        connection._client.update_token.assert_not_called()
        assert connection._client.get.call_count == 2

    def test_never_force_mints(self, connection: DhanConnection) -> None:
        connection._client.get.side_effect = AuthenticationError("401")
        with (
            patch("scalpr.brokers.dhan.connection.ensure_fresh_token") as mint,
            patch("scalpr.brokers.dhan.connection.is_token_fresh", return_value=True),
            patch("time.sleep"),
            pytest.raises(AuthenticationError),
        ):
            connection._verify_connection()

        for call in mint.call_args_list:
            assert call.kwargs.get("force") is not True, "force-mint burns TOTP attempts"


class TestVerifyRetryStaleToken:
    """Stale token + 401 → one non-forced refresh, retry with new token."""

    def test_refreshes_without_force_when_token_stale(self, connection: DhanConnection) -> None:
        connection._client.get.side_effect = [
            AuthenticationError("401 on GET /profile"),
            {"dataPlan": "active", "dataValidity": "2026-07-30", "activeSegment": []},
        ]
        with (
            patch(
                "scalpr.brokers.dhan.connection.ensure_fresh_token",
                return_value="tok-new",
            ) as mint,
            patch("scalpr.brokers.dhan.connection.is_token_fresh", return_value=False),
            patch("time.sleep"),
        ):
            connection._verify_connection()

        mint.assert_called_once_with()
        connection._client.update_token.assert_called_once_with("tok-new")


class TestVerifyRetryExhaustion:
    def test_raises_after_all_attempts(self, connection: DhanConnection) -> None:
        connection._client.get.side_effect = AuthenticationError("401")
        with (
            patch("scalpr.brokers.dhan.connection.ensure_fresh_token"),
            patch("scalpr.brokers.dhan.connection.is_token_fresh", return_value=True),
            patch("time.sleep"),
            pytest.raises(AuthenticationError),
        ):
            connection._verify_connection()

        assert connection._client.get.call_count == 3

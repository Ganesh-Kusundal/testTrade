"""Verify Gateway auto-token generation works end-to-end.

Tests that creating a Gateway() object:
1. Triggers TOTP generation when cached token is expired
2. Skips TOTP when cached token is fresh (cache hit)
3. Raises ConfigurationError when credentials are missing
"""

from __future__ import annotations

import base64
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scalpr.brokers.dhan._totp_cooldown import TotpCooldownGuard


def _make_jwt(exp: datetime) -> str:
    header = base64.urlsafe_b64encode(b'{"alg":"HS512"}').rstrip(b"=").decode()
    payload = base64.urlsafe_b64encode(
        json.dumps({"exp": int(exp.timestamp())}).encode()
    ).rstrip(b"=").decode()
    return f"{header}.{payload}.sig"


@pytest.fixture(autouse=True)
def _cleanup():
    keys = ["DHAN_CLIENT_ID", "DHAN_ACCESS_TOKEN", "DHAN_PIN", "DHAN_TOTP_SECRET"]
    saved = {k: os.environ.get(k) for k in keys}
    TotpCooldownGuard.reset_instances()
    cooldown_path = Path("runtime/dhan-totp-cooldown.json")
    if cooldown_path.exists():
        cooldown_path.unlink()
    yield
    for k, v in saved.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    TotpCooldownGuard.reset_instances()
    if cooldown_path.exists():
        cooldown_path.unlink()


def _set_creds():
    os.environ["DHAN_CLIENT_ID"] = "test_client_id"
    os.environ["DHAN_PIN"] = "123456"
    os.environ["DHAN_TOTP_SECRET"] = "JBSWY3DPEHPK3PXP"  # pragma: allowlist secret


class TestGatewayAutoTokenGeneration:
    def test_expired_token_triggers_totp_generation(self):
        """Gateway() with expired token should trigger TOTP generation."""
        _set_creds()
        expired = _make_jwt(datetime.now() - timedelta(hours=1))
        fresh = _make_jwt(datetime.now() + timedelta(hours=24))
        os.environ["DHAN_ACCESS_TOKEN"] = expired

        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {"accessToken": fresh}

        with patch("scalpr.brokers.dhan.auth.requests.post", return_value=mock_resp) as mock_post:
            with patch("scalpr.brokers.dhan.connection.DhanConnection.connect"):
                from scalpr.brokers.gateway.facade import Gateway
                Gateway(auto_connect=False)

        mock_post.assert_called_once()
        assert os.environ["DHAN_ACCESS_TOKEN"] == fresh

    def test_fresh_token_skips_totp_generation(self):
        """Gateway() with fresh token should NOT trigger TOTP generation."""
        _set_creds()
        fresh = _make_jwt(datetime.now() + timedelta(hours=12))
        os.environ["DHAN_ACCESS_TOKEN"] = fresh

        with patch("scalpr.brokers.dhan.auth.requests.post") as mock_post:
            with patch("scalpr.brokers.dhan.connection.DhanConnection.connect"):
                from scalpr.brokers.gateway.facade import Gateway
                Gateway(auto_connect=False)

        mock_post.assert_not_called()

    def test_missing_token_with_credentials_triggers_totp(self):
        """Gateway() with no token but valid credentials should trigger TOTP."""
        _set_creds()
        os.environ.pop("DHAN_ACCESS_TOKEN", None)
        fresh = _make_jwt(datetime.now() + timedelta(hours=24))

        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {"accessToken": fresh}

        with patch("scalpr.brokers.dhan.auth.requests.post", return_value=mock_resp) as mock_post:
            with patch("scalpr.brokers.dhan.auth.SecretsManager") as mock_sm:
                mock_sm.return_value.get_dhan_access_token.return_value = ""
                mock_sm.return_value.get_dhan_client_id.return_value = "test_client_id"
                mock_sm.return_value.get_dhan_pin.return_value = "123456"
                mock_sm.return_value.get_dhan_totp_secret.return_value = "JBSWY3DPEHPK3PXP"
                with patch("scalpr.brokers.dhan.connection.DhanConnection.connect"):
                    from scalpr.brokers.gateway.facade import Gateway
                    Gateway(auto_connect=False)

        mock_post.assert_called_once()
        assert os.environ["DHAN_ACCESS_TOKEN"] == fresh

    def test_missing_token_without_credentials_raises(self):
        """Gateway() with no token and no credentials should raise ConfigurationError."""
        os.environ["DHAN_CLIENT_ID"] = "test_client_id"
        os.environ.pop("DHAN_ACCESS_TOKEN", None)
        os.environ.pop("DHAN_PIN", None)
        os.environ.pop("DHAN_TOTP_SECRET", None)

        from scalpr.brokers.dhan.exceptions import ConfigurationError
        with patch("scalpr.brokers.dhan.auth.SecretsManager") as mock_sm:
            mock_sm.return_value.get_dhan_access_token.return_value = ""
            mock_sm.return_value.get_dhan_client_id.return_value = "test_client_id"
            mock_sm.return_value.get_dhan_pin.return_value = None
            mock_sm.return_value.get_dhan_totp_secret.return_value = None

            from scalpr.brokers.gateway.facade import Gateway
            with pytest.raises(ConfigurationError, match="DHAN_PIN"):
                Gateway(auto_connect=False)

    def test_totp_rate_limit_raises_error(self):
        """Gateway() should raise TotpRateLimitError when Dhan rate-limits TOTP."""
        _set_creds()
        os.environ.pop("DHAN_ACCESS_TOKEN", None)

        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {
            "message": "You can only generate access token once every 2 minutes"
        }

        from scalpr.brokers.errors import TradingError
        with patch("scalpr.brokers.dhan.auth.requests.post", return_value=mock_resp):
            with patch("scalpr.brokers.dhan.auth.SecretsManager") as mock_sm:
                mock_sm.return_value.get_dhan_access_token.return_value = ""
                mock_sm.return_value.get_dhan_client_id.return_value = "test_client_id"
                mock_sm.return_value.get_dhan_pin.return_value = "123456"
                mock_sm.return_value.get_dhan_totp_secret.return_value = "JBSWY3DPEHPK3PXP"
                from scalpr.brokers.gateway.facade import Gateway
                # TotpRateLimitError is now wrapped in TradingError for user-friendly output
                with pytest.raises(TradingError, match="Gateway initialization failed"):
                    Gateway(auto_connect=False)

"""Unit tests for Dhan token freshness and TOTP auto-refresh."""

from __future__ import annotations

import base64
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scalpr.brokers.dhan._totp_cooldown import TotpCooldownGuard, TotpRateLimitError
from scalpr.brokers.dhan.auth import (
    ensure_fresh_token,
    generate_token,
    get_broadcast,
    is_token_fresh,
    persist_token,
    token_expiry,
)
from scalpr.brokers.dhan.exceptions import AuthenticationError, ConfigurationError


def make_jwt(exp: datetime) -> str:
    """Build an unsigned JWT with the given expiry."""
    header = base64.urlsafe_b64encode(b'{"alg":"HS512"}').rstrip(b"=").decode()
    payload = base64.urlsafe_b64encode(
        json.dumps({"exp": int(exp.timestamp())}).encode()
    ).rstrip(b"=").decode()
    return f"{header}.{payload}.sig"


@pytest.fixture
def env_cleanup():
    keys = ["DHAN_CLIENT_ID", "DHAN_ACCESS_TOKEN", "DHAN_PIN", "DHAN_TOTP_SECRET"]
    saved = {k: os.environ.get(k) for k in keys}
    yield
    for k, v in saved.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v


@pytest.fixture(autouse=True)
def _reset_cooldown_singletons():
    TotpCooldownGuard.reset_instances()
    # Clean up persisted cooldown state so tests don't interfere
    import pathlib
    cooldown_path = pathlib.Path("runtime/dhan-totp-cooldown.json")
    if cooldown_path.exists():
        cooldown_path.unlink()
    yield
    TotpCooldownGuard.reset_instances()
    if cooldown_path.exists():
        cooldown_path.unlink()


class TestTokenExpiry:
    def test_decodes_exp_claim(self):
        exp = datetime.now() + timedelta(hours=5)
        decoded = token_expiry(make_jwt(exp))
        assert decoded is not None
        assert abs((decoded - exp).total_seconds()) < 1

    def test_garbage_returns_none(self):
        assert token_expiry("not-a-jwt") is None
        assert token_expiry("") is None
        assert token_expiry("a.b.c") is None


class TestIsTokenFresh:
    def test_fresh_beyond_buffer(self):
        assert is_token_fresh(make_jwt(datetime.now() + timedelta(hours=2)))

    def test_stale_within_buffer(self):
        assert not is_token_fresh(make_jwt(datetime.now() + timedelta(minutes=5)))

    def test_expired(self):
        assert not is_token_fresh(make_jwt(datetime.now() - timedelta(hours=1)))

    def test_unparseable(self):
        assert not is_token_fresh("garbage")


class TestEnsureFreshToken:
    def test_cache_hit_no_http(self, env_cleanup, tmp_path: Path):
        fresh = make_jwt(datetime.now() + timedelta(hours=12))
        os.environ["DHAN_ACCESS_TOKEN"] = fresh
        with patch("scalpr.brokers.dhan.auth.requests.post") as mock_post:
            token = ensure_fresh_token(env_path=tmp_path / ".env")
        assert token == fresh
        mock_post.assert_not_called()

    def test_refresh_persists_env_file_and_process_env(self, env_cleanup, tmp_path: Path):
        expired = make_jwt(datetime.now() - timedelta(hours=1))
        new_token = make_jwt(datetime.now() + timedelta(hours=24))
        env_file = tmp_path / ".env"
        env_file.write_text(f"DHAN_ACCESS_TOKEN={expired}\nOTHER=keep\n")

        os.environ["DHAN_ACCESS_TOKEN"] = expired
        os.environ["DHAN_CLIENT_ID"] = "cid"
        os.environ["DHAN_PIN"] = "1234"
        os.environ["DHAN_TOTP_SECRET"] = "JBSWY3DPEHPK3PXP"  # pragma: allowlist secret

        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {"accessToken": new_token}
        with patch("scalpr.brokers.dhan.auth.requests.post", return_value=mock_resp):
            token = ensure_fresh_token(env_path=env_file)

        assert token == new_token
        content = env_file.read_text()
        assert f"DHAN_ACCESS_TOKEN={new_token}\n" in content
        assert "OTHER=keep" in content
        assert os.environ["DHAN_ACCESS_TOKEN"] == new_token

    def test_expired_without_totp_creds_raises(self, env_cleanup, tmp_path: Path):
        os.environ["DHAN_ACCESS_TOKEN"] = make_jwt(datetime.now() - timedelta(hours=1))
        os.environ.pop("DHAN_PIN", None)
        os.environ.pop("DHAN_TOTP_SECRET", None)
        os.environ["DHAN_CLIENT_ID"] = "cid"
        # Isolate from real config/ file fallbacks
        with patch("scalpr.brokers.dhan.auth.SecretsManager") as mock_sm:
            mock_sm.return_value.get_dhan_access_token.return_value = (
                os.environ["DHAN_ACCESS_TOKEN"]
            )
            mock_sm.return_value.get_dhan_client_id.return_value = "cid"
            mock_sm.return_value.get_dhan_pin.return_value = None
            mock_sm.return_value.get_dhan_totp_secret.return_value = None
            with pytest.raises(ConfigurationError, match="DHAN_PIN"):
                ensure_fresh_token(env_path=tmp_path / ".env")

    def test_http_error_raises_authentication_error(self, env_cleanup, tmp_path: Path):
        os.environ["DHAN_ACCESS_TOKEN"] = make_jwt(datetime.now() - timedelta(hours=1))
        os.environ["DHAN_CLIENT_ID"] = "cid"
        os.environ["DHAN_PIN"] = "1234"
        os.environ["DHAN_TOTP_SECRET"] = "JBSWY3DPEHPK3PXP"  # pragma: allowlist secret

        mock_resp = MagicMock(status_code=401, text="bad totp")
        with patch("scalpr.brokers.dhan.auth.requests.post", return_value=mock_resp):
            with pytest.raises(AuthenticationError, match="401"):
                ensure_fresh_token(env_path=tmp_path / ".env")

    def test_force_regenerates_despite_fresh_cache(self, env_cleanup, tmp_path: Path):
        # W7b: on a broker 401 the cached token LOOKS fresh but is rejected —
        # force=True must bypass the local expiry check and regenerate.
        fresh_but_rejected = make_jwt(datetime.now() + timedelta(hours=12))
        new_token = make_jwt(datetime.now() + timedelta(hours=24))
        os.environ["DHAN_ACCESS_TOKEN"] = fresh_but_rejected
        os.environ["DHAN_CLIENT_ID"] = "cid"
        os.environ["DHAN_PIN"] = "1234"
        os.environ["DHAN_TOTP_SECRET"] = "JBSWY3DPEHPK3PXP"  # pragma: allowlist secret

        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {"accessToken": new_token}
        with patch("scalpr.brokers.dhan.auth.requests.post", return_value=mock_resp) as mock_post:
            token = ensure_fresh_token(env_path=tmp_path / ".env", force=True)

        assert token == new_token
        mock_post.assert_called_once()


class TestPersistToken:
    def test_appends_when_line_missing(self, env_cleanup, tmp_path: Path):
        env_file = tmp_path / ".env"
        env_file.write_text("OTHER=x\n")
        persist_token("tok123", env_file)
        assert "DHAN_ACCESS_TOKEN=tok123\n" in env_file.read_text()
        assert "OTHER=x" in env_file.read_text()

    def test_creates_file_when_absent(self, env_cleanup, tmp_path: Path):
        env_file = tmp_path / ".env"
        persist_token("tok456", env_file)
        assert env_file.read_text() == "DHAN_ACCESS_TOKEN=tok456\n"

    def test_replace_preserves_unrelated_lines(self, env_cleanup, tmp_path: Path):
        env_file = tmp_path / ".env"
        env_file.write_text("A=1\nDHAN_ACCESS_TOKEN=old\nB=2\n")
        persist_token("new", env_file)
        assert env_file.read_text() == "A=1\nDHAN_ACCESS_TOKEN=new\nB=2\n"
        # atomic write leaves no temp files behind
        assert [p.name for p in tmp_path.iterdir()] == [".env"]


class TestGenerateTokenCooldown:
    def test_cooldown_blocks_second_attempt(self, tmp_path: Path):
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {"accessToken": "tok"}
        with patch("scalpr.brokers.dhan.auth.requests.post", return_value=mock_resp):
            generate_token("cid", "pin", "JBSWY3DPEHPK3PXP")
            with pytest.raises(TotpRateLimitError, match="cooldown active"):
                generate_token("cid", "pin", "JBSWY3DPEHPK3PXP")

    def test_rate_limit_response_raises_totp_rate_limit_error(self):
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {
            "message": "You can only generate access token once every 2 minutes",
        }
        with patch("scalpr.brokers.dhan.auth.requests.post", return_value=mock_resp):
            with pytest.raises(TotpRateLimitError, match="rate limit"):
                generate_token("cid", "pin", "JBSWY3DPEHPK3PXP")


class TestEnsureFreshTokenPropagatesCooldown:
    """ensure_fresh_token must propagate TotpRateLimitError so callers
    with cooldown-aware retry (e.g. _verify_connection) can sleep."""

    def test_propagates_totp_rate_limit_error(self, env_cleanup, tmp_path: Path):
        os.environ["DHAN_ACCESS_TOKEN"] = make_jwt(datetime.now() - timedelta(hours=1))
        os.environ["DHAN_CLIENT_ID"] = "cid"
        os.environ["DHAN_PIN"] = "1234"
        os.environ["DHAN_TOTP_SECRET"] = "JBSWY3DPEHPK3PXP"  # pragma: allowlist secret

        with patch(
            "scalpr.brokers.dhan.auth.generate_token",
            side_effect=TotpRateLimitError("cooldown", remaining_seconds=90.0),
        ):
            with pytest.raises(TotpRateLimitError, match="cooldown") as exc_info:
                ensure_fresh_token(env_path=tmp_path / ".env", force=True)
            assert exc_info.value.remaining_seconds == 90.0

    def test_is_broker_agnostic_authentication_error(self):
        """TotpRateLimitError is part of the TradingError hierarchy (R1)."""
        from scalpr.brokers.errors import (
            AuthenticationError as BaseAuthError,
        )
        from scalpr.brokers.errors import (
            TokenRefreshThrottled,
            TradingError,
        )

        exc = TotpRateLimitError("cooldown", remaining_seconds=42.0)
        assert isinstance(exc, TokenRefreshThrottled)
        assert isinstance(exc, BaseAuthError)
        assert isinstance(exc, TradingError)
        assert exc.remaining_seconds == 42.0


class TestEnsureFreshTokenWaitForCooldown:
    """wait_for_cooldown=True is the ONLY sleep point for TOTP cooldown:
    sleep remaining+1s, retry generate_token exactly once."""

    def _set_env(self) -> None:
        os.environ["DHAN_ACCESS_TOKEN"] = make_jwt(datetime.now() - timedelta(hours=1))
        os.environ["DHAN_CLIENT_ID"] = "cid"
        os.environ["DHAN_PIN"] = "1234"
        os.environ["DHAN_TOTP_SECRET"] = "JBSWY3DPEHPK3PXP"  # pragma: allowlist secret

    def test_waits_then_retries_once(self, env_cleanup, tmp_path: Path):
        self._set_env()
        with (
            patch(
                "scalpr.brokers.dhan.auth.generate_token",
                side_effect=[
                    TotpRateLimitError("cooldown", remaining_seconds=90.0),
                    "tok-new",
                ],
            ) as mock_gen,
            patch("scalpr.brokers.dhan.auth.time.sleep") as mock_sleep,
        ):
            token = ensure_fresh_token(
                env_path=tmp_path / ".env", force=True, wait_for_cooldown=True
            )

        assert token == "tok-new"
        mock_sleep.assert_called_once_with(91.0)
        assert mock_gen.call_count == 2

    def test_raises_if_still_throttled_after_wait(self, env_cleanup, tmp_path: Path):
        self._set_env()
        with (
            patch(
                "scalpr.brokers.dhan.auth.generate_token",
                side_effect=TotpRateLimitError("cooldown", remaining_seconds=90.0),
            ) as mock_gen,
            patch("scalpr.brokers.dhan.auth.time.sleep") as mock_sleep,
            pytest.raises(TotpRateLimitError, match="cooldown"),
        ):
            ensure_fresh_token(
                env_path=tmp_path / ".env", force=True, wait_for_cooldown=True
            )

        # Exactly one bounded retry — no unbounded loop.
        mock_sleep.assert_called_once_with(91.0)
        assert mock_gen.call_count == 2

    def test_default_is_fail_fast_no_sleep(self, env_cleanup, tmp_path: Path):
        self._set_env()
        with (
            patch(
                "scalpr.brokers.dhan.auth.generate_token",
                side_effect=TotpRateLimitError("cooldown", remaining_seconds=90.0),
            ) as mock_gen,
            patch("scalpr.brokers.dhan.auth.time.sleep") as mock_sleep,
            pytest.raises(TotpRateLimitError),
        ):
            ensure_fresh_token(env_path=tmp_path / ".env", force=True)

        mock_sleep.assert_not_called()
        assert mock_gen.call_count == 1


class TestPersistTokenBroadcast:
    def test_persist_broadcasts_new_token(self, env_cleanup, tmp_path: Path):
        bc = get_broadcast()
        received: list[str] = []
        bc.register(lambda t: received.append(t))
        try:
            env_file = tmp_path / ".env"
            persist_token("broadcast_tok", env_file)
            assert received == ["broadcast_tok"]
        finally:
            bc.unregister_all()

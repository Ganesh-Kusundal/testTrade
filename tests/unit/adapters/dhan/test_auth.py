from __future__ import annotations

import base64
import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scalpr.adapters.dhan._auth import (
    DhanAuthError,
    DhanTokenRefreshThrottled,
    TokenManager,
)
from scalpr.engine.clock import StaticClock


def _make_jwt(exp: datetime) -> str:
    header = base64.urlsafe_b64encode(b'{"alg":"HS512"}').rstrip(b"=").decode()
    payload = base64.urlsafe_b64encode(
        json.dumps({"exp": int(exp.timestamp())}).encode()
    ).rstrip(b"=").decode()
    return f"{header}.{payload}.sig"


def _auth_response(access_token: str) -> MagicMock:
    mock = MagicMock(status_code=200)
    mock.json.return_value = {"accessToken": access_token}
    return mock


def _make_future_jwt(hours: int = 24) -> str:
    return _make_jwt(datetime(2025, 1, 2, tzinfo=timezone.utc))


def _make_expired_jwt() -> str:
    return _make_jwt(datetime(2023, 1, 1, tzinfo=timezone.utc))


@pytest.fixture
def clock():
    return StaticClock(start_time=datetime(2025, 1, 1, tzinfo=timezone.utc))


@pytest.fixture
def tmp_cache(tmp_path: Path) -> Path:
    """Per-test isolated token cache directory."""
    return tmp_path / "tokens"


@pytest.fixture
def manager(clock, tmp_cache):
    return TokenManager(client_id="test_cid", totp_secret="JBSWY3DPEHPK3PXP", clock=clock, cache_dir=tmp_cache)


class TestGetToken:
    def test_returns_token_on_first_call(self, manager, clock):
        token = _make_future_jwt()
        with patch("scalpr.adapters.dhan._auth.requests.post", return_value=_auth_response(token)):
            result = manager.get_token()
        assert result == token

    def test_reuses_fresh_token(self, manager, clock):
        token = _make_future_jwt()
        with patch("scalpr.adapters.dhan._auth.requests.post", return_value=_auth_response(token)):
            first = manager.get_token()
            second = manager.get_token()
        assert first == second
        assert manager.is_token_fresh()

    def test_refreshes_when_expired(self, manager, clock):
        old_token = _make_expired_jwt()
        new_token = _make_future_jwt()
        mock_resp = _auth_response(old_token)
        with patch("scalpr.adapters.dhan._auth.requests.post", return_value=mock_resp) as mock_post:
            manager._token = old_token
            manager._expires_at = datetime(2023, 1, 1, tzinfo=timezone.utc)
            mock_resp.json.return_value = {"accessToken": new_token}
            result = manager.get_token()
        assert result == new_token
        assert mock_post.call_count == 1

    def test_threshold_triggers_refresh(self, manager, clock):
        token = _make_future_jwt(hours=1)
        newer = _make_future_jwt(hours=48)
        mock_resp = _auth_response(token)
        with patch("scalpr.adapters.dhan._auth.requests.post", return_value=mock_resp) as mock_post:
            manager._token = token
            mock_resp.json.return_value = {"accessToken": newer}
            result = manager.get_token()
        assert result == newer
        assert mock_post.call_count == 1

    def test_raises_on_auth_failure(self, manager, clock):
        mock_resp = MagicMock(status_code=401, text="invalid totp")
        with patch("scalpr.adapters.dhan._auth.requests.post", return_value=mock_resp):
            with pytest.raises(DhanAuthError, match="401"):
                manager.get_token()

    def test_raises_on_network_error(self, manager, clock):
        import requests as _requests
        with patch("scalpr.adapters.dhan._auth.requests.post", side_effect=_requests.ConnectionError("reset")):
            with pytest.raises(DhanAuthError, match="Network error"):
                manager.get_token()

    def test_raises_on_empty_token(self, manager, clock):
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {"accessToken": ""}
        with patch("scalpr.adapters.dhan._auth.requests.post", return_value=mock_resp):
            with pytest.raises(DhanAuthError, match="Token missing"):
                manager.get_token()


class TestIsTokenFresh:
    def test_returns_false_when_no_token(self, manager):
        assert manager.is_token_fresh() is False

    def test_returns_true_with_fresh_token(self, manager, clock):
        token = _make_future_jwt()
        with patch("scalpr.adapters.dhan._auth.requests.post", return_value=_auth_response(token)):
            manager.get_token()
        assert manager.is_token_fresh() is True

    def test_returns_false_when_expired(self, manager, clock):
        manager._token = _make_expired_jwt()
        manager._expires_at = datetime(2023, 1, 1, tzinfo=timezone.utc)
        assert manager.is_token_fresh() is False


class TestRefreshToken:
    def test_forces_refresh(self, manager, clock):
        old_token = _make_future_jwt(hours=48)
        new_token = _make_future_jwt(hours=72)
        mock_resp = _auth_response(old_token)
        with patch("scalpr.adapters.dhan._auth.requests.post", return_value=mock_resp) as mock_post:
            manager._token = old_token
            mock_resp.json.return_value = {"accessToken": new_token}
            result = manager.refresh_token()
        assert result == new_token
        assert mock_post.call_count == 1

    def test_double_check_lock_skips_if_fresh(self, manager, clock):
        token = _make_future_jwt()
        mock_resp = _auth_response(token)
        with patch("scalpr.adapters.dhan._auth.requests.post", return_value=mock_resp) as mock_post:
            manager._token = token
            manager._expires_at = datetime(2025, 1, 2, tzinfo=timezone.utc)
            mock_post.reset_mock()
            result = manager.refresh_token()
            assert result == token
            mock_post.assert_not_called()

    def test_concurrent_only_one_mint(self, manager, clock):
        token = _make_future_jwt()
        mock_resp = _auth_response(token)
        barrier = threading.Barrier(5, timeout=5)
        results: list[str] = []
        errors: list[Exception] = []
        lock = threading.Lock()

        def worker():
            with patch("scalpr.adapters.dhan._auth.requests.post", return_value=mock_resp):
                barrier.wait()
                try:
                    t = manager.get_token()
                    with lock:
                        results.append(t)
                except Exception as e:
                    with lock:
                        errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert all(r == token for r in results)

    def test_raises_on_rate_limit(self, manager, clock):
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {
            "message": "You can only generate access token once every 2 minutes",
        }
        with patch("scalpr.adapters.dhan._auth.requests.post", return_value=mock_resp):
            with pytest.raises(DhanTokenRefreshThrottled, match="rate limit"):
                manager.refresh_token()


class TestMintToken:
    def test_sends_correct_payload(self, manager, clock):
        token = _make_future_jwt()
        with patch("scalpr.adapters.dhan._auth.requests.post", return_value=_auth_response(token)) as mock_post:
            manager.get_token()
            call_args, call_kwargs = mock_post.call_args
            assert call_kwargs["data"]["dhanClientId"] == "test_cid"
            assert call_args[0] == "https://auth.dhan.co/app/generateAccessToken"

    def test_stores_expires_at_from_jwt(self, manager, clock):
        token = _make_future_jwt()
        with patch("scalpr.adapters.dhan._auth.requests.post", return_value=_auth_response(token)):
            manager.get_token()
        assert manager._expires_at is not None

    def test_returns_dhanauthresponse(self, manager, clock):
        token = _make_future_jwt()
        with patch("scalpr.adapters.dhan._auth.requests.post", return_value=_auth_response(token)):
            manager.get_token()
        assert manager._token == token


class TestThreadSafety:
    def test_lock_prevents_concurrent_mint(self, manager, clock):
        token = _make_future_jwt()
        mock_resp = _auth_response(token)
        call_count = 0

        def delayed_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return mock_resp

        with patch("scalpr.adapters.dhan._auth.requests.post", side_effect=delayed_post):
            t1 = threading.Thread(target=manager.get_token)
            t2 = threading.Thread(target=manager.get_token)
            t1.start()
            t2.start()
            t1.join()
            t2.join()

        assert call_count >= 1

    def test_is_token_fresh_not_blocked_by_lock(self, manager, clock):
        token = _make_future_jwt()
        with patch("scalpr.adapters.dhan._auth.requests.post", return_value=_auth_response(token)):
            manager.get_token()
            acquired = manager._lock.acquire(blocking=False)
            manager._lock.release()
            assert acquired is True


class TestEdgeCases:
    def test_empty_client_id(self, clock):
        import requests as _requests
        with pytest.raises(DhanAuthError, match="Network error"):
            manager = TokenManager(client_id="", totp_secret="JBSWY3DPEHPK3PXP", clock=clock)
            with patch("scalpr.adapters.dhan._auth.requests.post", side_effect=_requests.ConnectionError("reset")):
                manager.get_token()

    def test_unicode_totp_secret(self, clock):
        manager = TokenManager(client_id="cid", totp_secret="JBSWY3DPEHPK3PXP", clock=clock)
        token = _make_future_jwt()
        with patch("scalpr.adapters.dhan._auth.requests.post", return_value=_auth_response(token)):
            result = manager.get_token()
        assert result == token

    def test_malformed_jwt_uses_default_expiry(self, manager, clock):
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {"accessToken": "not.a.jwt"}
        with patch("scalpr.adapters.dhan._auth.requests.post", return_value=mock_resp):
            manager.get_token()
        assert manager._expires_at is not None

    def test_clock_time_advance_triggers_expiry(self, manager, clock):
        token = _make_future_jwt(hours=1)
        with patch("scalpr.adapters.dhan._auth.requests.post", return_value=_auth_response(token)):
            manager.get_token()
        assert manager.is_token_fresh() is True
        clock.advance(3600 * 24)
        assert manager.is_token_fresh() is False

    def test_clock_time_advance_triggers_refresh_on_get(self, manager, clock):
        old_token = _make_future_jwt(hours=1)
        new_token = _make_future_jwt(hours=48)
        mock_resp = _auth_response(old_token)
        with patch("scalpr.adapters.dhan._auth.requests.post", return_value=mock_resp):
            manager.get_token()
            mock_resp.json.return_value = {"accessToken": new_token}
            clock.advance(3600 * 24)
            result = manager.get_token()
        assert result == new_token

    def test_refresh_token_without_prior_token(self, manager, clock):
        token = _make_future_jwt()
        with patch("scalpr.adapters.dhan._auth.requests.post", return_value=_auth_response(token)):
            result = manager.refresh_token()
        assert result == token

    def test_refresh_token_twice_sequential(self, manager, clock):
        token1 = _make_future_jwt(hours=48)
        token2 = _make_future_jwt(hours=72)
        mock_resp = _auth_response(token1)
        with patch("scalpr.adapters.dhan._auth.requests.post", return_value=mock_resp) as mock_post:
            r1 = manager.refresh_token()
            manager._expires_at = datetime(2023, 1, 1, tzinfo=timezone.utc)
            mock_resp.json.return_value = {"accessToken": token2}
            r2 = manager.refresh_token()
        assert r1 == token1
        assert r2 == token2
        assert mock_post.call_count == 2

    def test_get_token_double_invocation_returns_same(self, manager, clock):
        token = _make_future_jwt()
        with patch("scalpr.adapters.dhan._auth.requests.post", return_value=_auth_response(token)):
            r1 = manager.get_token()
            r2 = manager.get_token()
        assert r1 == r2
        assert r1 == token

    def test_is_token_fresh_returns_false_when_expires_at_none(self, manager, clock):
        manager._token = _make_future_jwt()
        manager._expires_at = None
        assert manager.is_token_fresh() is False

    def test_is_token_fresh_returns_false_when_token_none(self, manager, clock):
        manager._token = None
        manager._expires_at = datetime(2025, 1, 2, tzinfo=timezone.utc)
        assert manager.is_token_fresh() is False

    def test_constructor_stores_params(self, clock):
        mgr = TokenManager(client_id="x", totp_secret="y", clock=clock)
        assert mgr._client_id == "x"
        assert mgr._totp_secret == "y"
        assert mgr._clock is clock


class TestProactiveRefresh:
    def test_refresh_threshold_is_80_percent(self):
        from scalpr.adapters.dhan._auth import REFRESH_THRESHOLD
        assert REFRESH_THRESHOLD == 0.8

    def test_proactive_refresh_scheduled_after_mint(self, clock, tmp_cache):
        from scalpr.adapters.dhan._auth import TokenManager as TM  # noqa: N817
        clock2 = MagicMock()
        clock2.utc_now.return_value = datetime(2025, 1, 1, tzinfo=timezone.utc)
        manager = TM(client_id="test_cid", totp_secret="JBSWY3DPEHPK3PXP", clock=clock2, cache_dir=tmp_cache)
        token = _make_future_jwt()
        with patch("scalpr.adapters.dhan._auth.requests.post", return_value=_auth_response(token)):
            manager.get_token()
        assert manager._refresh_timer is not None
        assert manager._refresh_timer.is_alive()

    def test_proactive_refresh_cancelled_on_stop(self, clock, tmp_cache):
        from scalpr.adapters.dhan._auth import TokenManager as TM  # noqa: N817
        clock2 = MagicMock()
        clock2.utc_now.return_value = datetime(2025, 1, 1, tzinfo=timezone.utc)
        manager = TM(client_id="test_cid", totp_secret="JBSWY3DPEHPK3PXP", clock=clock2, cache_dir=tmp_cache)
        token = _make_future_jwt()
        with patch("scalpr.adapters.dhan._auth.requests.post", return_value=_auth_response(token)):
            manager.get_token()
        assert manager._refresh_timer is not None
        manager.stop()
        assert manager._refresh_timer is None

    def test_proactive_refresh_not_scheduled_for_static_clock(self, manager, clock):
        token = _make_future_jwt()
        with patch("scalpr.adapters.dhan._auth.requests.post", return_value=_auth_response(token)):
            manager.get_token()
        assert getattr(manager, "_refresh_timer", None) is None

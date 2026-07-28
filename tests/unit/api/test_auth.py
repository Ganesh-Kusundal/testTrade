"""JWT auth — Bloomberg plan Module 10 (API security).

Stdlib HS256 JWT + ASGI middleware. Enabled only when SCALPR_JWT_SECRET
is set (fail-closed on every non-exempt route); dev/paper boots without
the secret stay open so existing flows are unchanged.
"""

import time
from unittest.mock import MagicMock, patch

import pytest

from scalpr.api.auth import AuthError, create_token, verify_token

SECRET = "test-secret-key"


class TestTokenFunctions:
    def test_round_trip_returns_claims(self):
        token = create_token("trader1", SECRET)
        claims = verify_token(token, SECRET)
        assert claims["sub"] == "trader1"

    def test_expired_token_rejected(self):
        token = create_token("trader1", SECRET, expires_in_s=-1)
        with pytest.raises(AuthError, match="expired"):
            verify_token(token, SECRET)

    def test_tampered_token_rejected(self):
        token = create_token("trader1", SECRET)
        header, payload, sig = token.split(".")
        with pytest.raises(AuthError):
            verify_token(f"{header}.{payload}x.{sig}", SECRET)

    def test_wrong_secret_rejected(self):
        token = create_token("trader1", SECRET)
        with pytest.raises(AuthError):
            verify_token(token, "other-secret")

    def test_malformed_token_rejected(self):
        with pytest.raises(AuthError):
            verify_token("not-a-jwt", SECRET)

    def test_expiry_claim_present(self):
        token = create_token("trader1", SECRET, expires_in_s=3600)
        claims = verify_token(token, SECRET)
        assert claims["exp"] > time.time()


def _app():
    with patch("scalpr.api.bootstrap._load_dotenv"), \
         patch("scalpr.api.bootstrap._create_gateway") as mock_gw:
        gw = MagicMock()
        gw.get_positions.return_value = []
        mock_gw.return_value = (gw, None)
        from scalpr.api.bootstrap import create_app
        return create_app()


class TestAuthMiddleware:
    def test_protected_route_rejects_missing_token(self, monkeypatch):
        monkeypatch.setenv("SCALPR_JWT_SECRET", SECRET)
        from fastapi.testclient import TestClient
        with TestClient(_app()) as client:
            resp = client.get("/portfolio/positions")
            assert resp.status_code == 401

    def test_protected_route_rejects_bad_token(self, monkeypatch):
        monkeypatch.setenv("SCALPR_JWT_SECRET", SECRET)
        from fastapi.testclient import TestClient
        with TestClient(_app()) as client:
            resp = client.get(
                "/portfolio/positions",
                headers={"Authorization": "Bearer garbage"},
            )
            assert resp.status_code == 401

    def test_protected_route_accepts_valid_token(self, monkeypatch):
        monkeypatch.setenv("SCALPR_JWT_SECRET", SECRET)
        from fastapi.testclient import TestClient
        token = create_token("trader1", SECRET)
        with TestClient(_app()) as client:
            resp = client.get(
                "/portfolio/positions",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code != 401

    def test_health_stays_open_for_probes(self, monkeypatch):
        monkeypatch.setenv("SCALPR_JWT_SECRET", SECRET)
        from fastapi.testclient import TestClient
        with TestClient(_app()) as client:
            assert client.get("/health").status_code == 200

    def test_auth_disabled_without_secret(self, monkeypatch):
        monkeypatch.delenv("SCALPR_JWT_SECRET", raising=False)
        from fastapi.testclient import TestClient
        with TestClient(_app()) as client:
            resp = client.get("/portfolio/positions")
            assert resp.status_code != 401

"""K-043: single-token-owner protocol via shared Dhan token store.

Both this project and Trade_XV2 mint for the same Dhan client; every mint
revokes the sibling's token server-side (observed ping-pong). Cure:

1. Adopt-before-mint: when the local token is stale or broker-rejected,
   adopt a fresh, *different* token from the shared store (DHAN_TOKEN_PATH)
   instead of minting — zero revocation.
2. Write-through: every mint is persisted to the shared store in the
   Trade_XV2-compatible schema ({access_token, expires_at, ...}) so the
   sibling adopts instead of re-minting.
3. TotpCooldownGuard honors DHAN_COOLDOWN_PATH so both projects share one
   mint-rate budget.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scalpr.brokers.dhan._totp_cooldown import TotpCooldownGuard
from scalpr.brokers.dhan.auth import ensure_fresh_token
from tests.unit.brokers.dhan.test_auth import make_jwt


@pytest.fixture(autouse=True)
def _isolate(tmp_path):
    keys = [
        "DHAN_CLIENT_ID", "DHAN_ACCESS_TOKEN", "DHAN_PIN",
        "DHAN_TOTP_SECRET", "DHAN_TOKEN_PATH", "DHAN_COOLDOWN_PATH",
    ]
    saved = {k: os.environ.get(k) for k in keys}
    TotpCooldownGuard.reset_instances()
    cooldown_file = Path("runtime/dhan-totp-cooldown.json")
    if cooldown_file.exists():
        cooldown_file.unlink()
    yield
    for k, v in saved.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    TotpCooldownGuard.reset_instances()
    if cooldown_file.exists():
        cooldown_file.unlink()


def _write_shared_store(path: Path, token: str) -> None:
    """Write the store exactly as Trade_XV2's DhanTokenStore.save() does."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "access_token": token,
        "expires_at": (datetime.now() + timedelta(hours=12)).timestamp(),
        "source": "TOTP",
    }))


class TestAdoptBeforeMint:
    def test_stale_local_adopts_fresh_shared_token_without_minting(self, tmp_path):
        """THE fix: sibling already minted — adopt its token, never mint."""
        stale = make_jwt(datetime.now() - timedelta(hours=1))
        sibling = make_jwt(datetime.now() + timedelta(hours=12))
        shared = tmp_path / "dhan-token-state.json"
        _write_shared_store(shared, sibling)

        os.environ["DHAN_ACCESS_TOKEN"] = stale
        os.environ["DHAN_TOKEN_PATH"] = str(shared)
        env_file = tmp_path / ".env"

        with patch("scalpr.brokers.dhan.auth.requests.post") as mock_post:
            token = ensure_fresh_token(env_path=env_file)

        assert token == sibling
        mock_post.assert_not_called()  # zero mints — sibling's token survives
        assert f"DHAN_ACCESS_TOKEN={sibling}\n" in env_file.read_text()
        assert os.environ["DHAN_ACCESS_TOKEN"] == sibling

    def test_force_adopts_when_shared_differs_from_rejected(self, tmp_path):
        """Broker 401'd our token; the sibling's NEWER token is the valid one."""
        rejected = make_jwt(datetime.now() + timedelta(hours=11))
        sibling = make_jwt(datetime.now() + timedelta(hours=12))
        shared = tmp_path / "dhan-token-state.json"
        _write_shared_store(shared, sibling)

        os.environ["DHAN_ACCESS_TOKEN"] = rejected
        os.environ["DHAN_TOKEN_PATH"] = str(shared)

        with patch("scalpr.brokers.dhan.auth.requests.post") as mock_post:
            token = ensure_fresh_token(env_path=tmp_path / ".env", force=True)

        assert token == sibling
        mock_post.assert_not_called()

    def test_force_mints_when_shared_equals_rejected_token(self, tmp_path):
        """Shared store holds the very token the broker rejected — must mint."""
        rejected = make_jwt(datetime.now() + timedelta(hours=11))
        new_token = make_jwt(datetime.now() + timedelta(hours=24))
        shared = tmp_path / "dhan-token-state.json"
        _write_shared_store(shared, rejected)

        os.environ["DHAN_ACCESS_TOKEN"] = rejected
        os.environ["DHAN_TOKEN_PATH"] = str(shared)
        os.environ["DHAN_CLIENT_ID"] = "cid"
        os.environ["DHAN_PIN"] = "1234"
        os.environ["DHAN_TOTP_SECRET"] = "JBSWY3DPEHPK3PXP"  # pragma: allowlist secret

        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {"accessToken": new_token}
        with patch("scalpr.brokers.dhan.auth.requests.post", return_value=mock_resp):
            token = ensure_fresh_token(env_path=tmp_path / ".env", force=True)

        assert token == new_token

    def test_corrupt_shared_store_falls_through_to_mint(self, tmp_path):
        stale = make_jwt(datetime.now() - timedelta(hours=1))
        new_token = make_jwt(datetime.now() + timedelta(hours=24))
        shared = tmp_path / "dhan-token-state.json"
        shared.write_text("{not json")

        os.environ["DHAN_ACCESS_TOKEN"] = stale
        os.environ["DHAN_TOKEN_PATH"] = str(shared)
        os.environ["DHAN_CLIENT_ID"] = "cid"
        os.environ["DHAN_PIN"] = "1234"
        os.environ["DHAN_TOTP_SECRET"] = "JBSWY3DPEHPK3PXP"  # pragma: allowlist secret

        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {"accessToken": new_token}
        with patch("scalpr.brokers.dhan.auth.requests.post", return_value=mock_resp):
            token = ensure_fresh_token(env_path=tmp_path / ".env")

        assert token == new_token

    def test_no_token_path_env_preserves_existing_behaviour(self, tmp_path):
        stale = make_jwt(datetime.now() - timedelta(hours=1))
        new_token = make_jwt(datetime.now() + timedelta(hours=24))
        os.environ.pop("DHAN_TOKEN_PATH", None)
        os.environ["DHAN_ACCESS_TOKEN"] = stale
        os.environ["DHAN_CLIENT_ID"] = "cid"
        os.environ["DHAN_PIN"] = "1234"
        os.environ["DHAN_TOTP_SECRET"] = "JBSWY3DPEHPK3PXP"  # pragma: allowlist secret

        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {"accessToken": new_token}
        with patch("scalpr.brokers.dhan.auth.requests.post", return_value=mock_resp):
            token = ensure_fresh_token(env_path=tmp_path / ".env")

        assert token == new_token


class TestWriteThrough:
    def test_mint_writes_shared_store_in_tradexv2_schema(self, tmp_path):
        stale = make_jwt(datetime.now() - timedelta(hours=1))
        new_token = make_jwt(datetime.now() + timedelta(hours=24))
        shared = tmp_path / "dhan-token-state.json"

        os.environ["DHAN_ACCESS_TOKEN"] = stale
        os.environ["DHAN_TOKEN_PATH"] = str(shared)
        os.environ["DHAN_CLIENT_ID"] = "cid"
        os.environ["DHAN_PIN"] = "1234"
        os.environ["DHAN_TOTP_SECRET"] = "JBSWY3DPEHPK3PXP"  # pragma: allowlist secret

        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {"accessToken": new_token}
        with patch("scalpr.brokers.dhan.auth.requests.post", return_value=mock_resp):
            ensure_fresh_token(env_path=tmp_path / ".env")

        data = json.loads(shared.read_text())
        assert data["access_token"] == new_token
        # Trade_XV2's DhanTokenStore._read requires a usable expires_at
        assert data["expires_at"] > datetime.now().timestamp()

    def test_adopt_does_not_rewrite_shared_store(self, tmp_path):
        stale = make_jwt(datetime.now() - timedelta(hours=1))
        sibling = make_jwt(datetime.now() + timedelta(hours=12))
        shared = tmp_path / "dhan-token-state.json"
        _write_shared_store(shared, sibling)
        before = shared.read_text()

        os.environ["DHAN_ACCESS_TOKEN"] = stale
        os.environ["DHAN_TOKEN_PATH"] = str(shared)

        with patch("scalpr.brokers.dhan.auth.requests.post"):
            ensure_fresh_token(env_path=tmp_path / ".env")

        assert shared.read_text() == before


class TestSharedCooldownPath:
    def test_guard_honors_dhan_cooldown_path_env(self, tmp_path):
        shared_cd = tmp_path / "shared" / "dhan-totp-cooldown.json"
        os.environ["DHAN_COOLDOWN_PATH"] = str(shared_cd)
        TotpCooldownGuard.reset_instances()

        guard = TotpCooldownGuard.for_broker("dhan")
        guard.record_attempt()

        assert shared_cd.exists()
        state = json.loads(shared_cd.read_text())
        assert state["broker"] == "dhan"
        assert state["last_attempt_at"] is not None

    def test_guard_defaults_to_repo_runtime_without_env(self, tmp_path):
        os.environ.pop("DHAN_COOLDOWN_PATH", None)
        TotpCooldownGuard.reset_instances()
        guard = TotpCooldownGuard.for_broker("dhan")
        assert guard._state_path.name == "dhan-totp-cooldown.json"
        assert "runtime" in str(guard._state_path)

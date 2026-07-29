"""Regression tests for scripts/generate_dhan_token.py.

Root cause locked down: the script used to force-mint on every run, even
when .env held a fresh token. Each mint revokes the previously issued
token broker-side and burns Dhan's 2-minute TOTP rate limit — so two
projects sharing one client ID kept invalidating each other's tokens.

Policy (mirrors Trade_XV2 v2 probe-before-mint): fresh cached token →
zero network calls; mint only when stale or --force is passed.
"""

from __future__ import annotations

import base64
import importlib.util
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from scalpr.brokers.dhan._totp_cooldown import TotpCooldownGuard, TotpRateLimitError
from scalpr.brokers.dhan.exceptions import ConfigurationError

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_PATH = REPO_ROOT / "scripts" / "generate_dhan_token.py"


def load_script_module():
    spec = importlib.util.spec_from_file_location("generate_dhan_token", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_jwt(exp: datetime) -> str:
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
    cooldown_path = Path("runtime/dhan-totp-cooldown.json")
    if cooldown_path.exists():
        cooldown_path.unlink()
    yield
    TotpCooldownGuard.reset_instances()
    if cooldown_path.exists():
        cooldown_path.unlink()


class TestProbeBeforeMint:
    def test_fresh_token_makes_no_network_call(self, env_cleanup):
        """THE regression: fresh cached token must never trigger a mint."""
        fresh = make_jwt(datetime.now() + timedelta(hours=12))
        os.environ["DHAN_ACCESS_TOKEN"] = fresh
        os.environ["DHAN_CLIENT_ID"] = "cid"
        os.environ["DHAN_PIN"] = "1234"
        os.environ["DHAN_TOTP_SECRET"] = "JBSWY3DPEHPK3PXP"  # pragma: allowlist secret

        script = load_script_module()
        with patch("scalpr.brokers.dhan.auth.requests.post") as mock_post:
            script.main([])
        mock_post.assert_not_called()

    def test_force_flag_remints_despite_fresh_token(self, env_cleanup):
        fresh = make_jwt(datetime.now() + timedelta(hours=12))
        os.environ["DHAN_ACCESS_TOKEN"] = fresh

        script = load_script_module()
        new_token = make_jwt(datetime.now() + timedelta(hours=24))
        with patch.object(script, "ensure_fresh_token", return_value=new_token) as mock_ensure:
            script.main(["--force"])
        mock_ensure.assert_called_once()
        assert mock_ensure.call_args.kwargs["force"] is True

    def test_missing_credentials_exits_nonzero(self, env_cleanup):
        stale = make_jwt(datetime.now() - timedelta(hours=1))
        os.environ["DHAN_ACCESS_TOKEN"] = stale

        script = load_script_module()
        # Fully mocked — the refresh path must never reach the real API.
        with patch.object(
            script,
            "ensure_fresh_token",
            side_effect=ConfigurationError("needs DHAN_CLIENT_ID, DHAN_PIN"),
        ):
            with pytest.raises(SystemExit) as exc_info:
                script.main([])
        assert exc_info.value.code == 1

    def test_cooldown_exits_nonzero(self, env_cleanup):
        stale = make_jwt(datetime.now() - timedelta(hours=1))
        os.environ["DHAN_ACCESS_TOKEN"] = stale

        script = load_script_module()
        with patch.object(
            script,
            "ensure_fresh_token",
            side_effect=TotpRateLimitError("cooldown active", remaining_seconds=90.0),
        ):
            with pytest.raises(SystemExit) as exc_info:
                script.main([])
        assert exc_info.value.code == 1

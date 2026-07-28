"""Dhan token freshness: local JWT expiry check + TOTP regeneration.

The ``.env`` file is the token cache — gitignored, read by every consumer,
survives restarts. Expiry is decoded locally from the JWT ``exp`` claim,
so the cache-hit path costs zero network calls.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pyotp
import requests

from config.secrets_manager import SecretsManager
from scalpr.brokers.dhan.exceptions import AuthenticationError, ConfigurationError
from scalpr.domain.values import DEFAULT_TIMEOUT_S

logger = logging.getLogger(__name__)

TOKEN_URL = "https://auth.dhan.co/app/generateAccessToken"  # noqa: S105 — endpoint URL, not a secret
EXPIRY_BUFFER = timedelta(minutes=15)


def token_expiry(token: str) -> datetime | None:
    """Decode the ``exp`` claim from a JWT. Returns None if not parseable."""
    try:
        payload_b64 = token.split(".")[1]
        payload_b64 += "=" * (-len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        return datetime.fromtimestamp(payload["exp"])
    except (IndexError, KeyError, ValueError, TypeError):
        return None


def is_token_fresh(token: str, buffer: timedelta = EXPIRY_BUFFER) -> bool:
    """True if the token has an expiry beyond now + buffer."""
    expiry = token_expiry(token)
    return expiry is not None and expiry > datetime.now() + buffer


def generate_token(client_id: str, pin: str, totp_secret: str) -> str:
    """Generate a fresh access token via Dhan's TOTP login flow."""
    totp_code = pyotp.TOTP(totp_secret).now()
    resp = requests.post(
        TOKEN_URL,
        data={"dhanClientId": client_id, "pin": pin, "totp": totp_code},
        timeout=DEFAULT_TIMEOUT_S,
    )
    if resp.status_code != 200:
        raise AuthenticationError(
            f"Dhan token generation failed: HTTP {resp.status_code}: {resp.text}"
        )
    body = resp.json()
    access_token: str = body.get("accessToken", "")
    if not access_token:
        raise AuthenticationError(f"Dhan token missing in response: {body}")
    logger.info(
        "dhan_token_generated: client=%s expires=%s",
        body.get("dhanClientUcc"),
        body.get("expiryTime"),
    )
    return access_token


def persist_token(access_token: str, env_path: Path) -> None:
    """Write the token to ``.env`` (cache) and the current process env."""
    # ponytail: no cross-process file lock — single-operator local setup;
    # add fcntl.flock if parallel processes ever race on .env. Write is
    # atomic (tempfile + os.replace) so a crash never truncates .env.
    line = f"DHAN_ACCESS_TOKEN={access_token}\n"
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines(keepends=True)
        replaced = False
        for i, existing in enumerate(lines):
            if existing.startswith("DHAN_ACCESS_TOKEN="):
                lines[i] = line
                replaced = True
                break
        if not replaced:
            lines.append(line)
        content = "".join(lines)
    else:
        content = line
    fd, tmp_path = tempfile.mkstemp(dir=env_path.parent, prefix=".env.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp:
            tmp.write(content)
        os.replace(tmp_path, env_path)
    except BaseException:
        os.unlink(tmp_path)
        raise
    os.environ["DHAN_ACCESS_TOKEN"] = access_token


def ensure_fresh_token(env_path: Path | None = None, force: bool = False) -> str:
    """Return a valid Dhan access token, regenerating via TOTP if expired.

    Cache hit (token in env/.env still fresh) returns immediately with no
    network I/O. On miss, regenerates through the TOTP flow and persists
    the new token to ``.env`` and ``os.environ``.

    Args:
        env_path: Location of the ``.env`` token cache (default: ./.env).
        force: Skip the local expiry check and always regenerate — used
            when the broker rejects a token that still looks fresh (401).
    """
    env_path = env_path or Path(".env")
    secrets = SecretsManager()

    token = secrets.get_dhan_access_token()
    if token and is_token_fresh(token) and not force:
        return token

    client_id = secrets.get_dhan_client_id()
    pin = secrets.get_dhan_pin()
    totp_secret = secrets.get_dhan_totp_secret()
    if not all([client_id, pin, totp_secret]):
        raise ConfigurationError(
            "Dhan access token is expired or missing, and auto-refresh needs "
            "DHAN_CLIENT_ID, DHAN_PIN and DHAN_TOTP_SECRET (env or config/ "
            "file fallbacks) to regenerate it."
        )

    logger.info("dhan_token_stale: regenerating via TOTP flow")
    access_token = generate_token(client_id, pin, totp_secret)  # type: ignore[arg-type]
    persist_token(access_token, env_path)
    return access_token

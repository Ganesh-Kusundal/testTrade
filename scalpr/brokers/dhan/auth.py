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
import time
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path

import pyotp
import requests

from config.secrets_manager import SecretsManager
from scalpr.brokers.dhan._totp_cooldown import TotpCooldownGuard, TotpRateLimitError
from scalpr.brokers.dhan.exceptions import AuthenticationError, ConfigurationError
from scalpr.domain.values import DEFAULT_TIMEOUT_S

logger = logging.getLogger(__name__)

TOKEN_URL = "https://auth.dhan.co/app/generateAccessToken"  # noqa: S105 — endpoint URL, not a secret
EXPIRY_BUFFER = timedelta(minutes=15)


class TokenBroadcast:
    """Registry of token receivers + broadcast.

    One instance per broker token manager. Strong references — a token
    manager lives exactly as long as its broker connection, with at most
    a couple of receivers registered once for that same lifetime.
    """

    def __init__(self) -> None:
        self._receivers: list[Callable[[str], None]] = []

    def register(self, receiver: Callable[[str], None]) -> Callable[[str], None]:
        """Idempotent: registering the same callable twice is a no-op."""
        if receiver not in self._receivers:
            self._receivers.append(receiver)
        return receiver

    def unregister(self, receiver: Callable[[str], None]) -> None:
        if receiver in self._receivers:
            self._receivers.remove(receiver)

    def unregister_all(self) -> int:
        """Remove all receivers. Returns count removed."""
        count = len(self._receivers)
        self._receivers.clear()
        return count

    def broadcast(self, new_token: str) -> int:
        """Push new_token to every receiver; isolate per-receiver failures."""
        if not new_token:
            return 0
        delivered = 0
        for receiver in list(self._receivers):
            try:
                receiver(new_token)
                delivered += 1
            except Exception as exc:
                logger.warning(
                    "token_receiver_failed",
                    extra={
                        "receiver": getattr(receiver, "__qualname__", repr(receiver)),
                        "error": str(exc),
                    },
                )
        return delivered

    @property
    def receiver_count(self) -> int:
        return len(self._receivers)


_broadcast = TokenBroadcast()


def get_broadcast() -> TokenBroadcast:
    """Access the module-level token broadcast for registering receivers."""
    return _broadcast


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
    """Generate a fresh access token via Dhan's TOTP login flow.

    Enforces local cooldown (120s) to avoid burning Dhan's rate limit.
    """
    cooldown = TotpCooldownGuard.for_broker("dhan")
    cooldown.check_allowed()

    cooldown.record_attempt()
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

    message = str(body.get("message", ""))
    if "once every 2 minutes" in message:
        cooldown.record_rate_limited()
        raise TotpRateLimitError(
            f"Dhan TOTP rate limit: {message}",
            remaining_seconds=cooldown.remaining_cooldown_seconds() or 120.0,
        )

    access_token: str = body.get("accessToken", "")
    if not access_token:
        raise AuthenticationError(f"Dhan token missing in response: {body}")

    cooldown.record_success()
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
    _broadcast.broadcast(access_token)


def ensure_fresh_token(
    env_path: Path | None = None,
    force: bool = False,
    wait_for_cooldown: bool = False,
) -> str:
    """Return a valid Dhan access token, regenerating via TOTP if expired.

    Cache hit (token in env/.env still fresh) returns immediately with no
    network I/O. On miss, regenerates through the TOTP flow and persists
    the new token to ``.env`` and ``os.environ``.

    Contract:
    - Returns a valid token on success.
    - Raises ``AuthenticationError`` if credentials are missing or the
      Dhan API rejects the token.
    - Raises ``TotpRateLimitError`` if TOTP generation is blocked by
      cooldown and ``wait_for_cooldown`` is False — callers can inspect
      ``remaining_seconds`` to decide whether to wait and retry.

    This is the ONLY place that sleeps for the TOTP cooldown — callers
    must never add their own cooldown sleeps.

    Args:
        env_path: Location of the ``.env`` token cache (default: ./.env).
        force: Skip the local expiry check and always regenerate — used
            when the broker rejects a token that still looks fresh (401).
        wait_for_cooldown: When True and TOTP generation is blocked by
            cooldown, sleep for the remaining cooldown (+1s buffer) and
            retry once. Only interactive/connect paths should opt in —
            request paths and background threads must stay fail-fast.
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
    try:
        access_token = generate_token(client_id, pin, totp_secret)  # type: ignore[arg-type]
    except TotpRateLimitError as cooldown_exc:
        if not wait_for_cooldown:
            # Propagate — fail-fast callers surface remaining_seconds.
            raise
        wait = cooldown_exc.remaining_seconds + 1.0
        logger.warning(
            "dhan_token_cooldown_wait",
            extra={"wait_seconds": round(wait, 1)},
        )
        time.sleep(wait)
        # One bounded retry — if still throttled, propagate.
        access_token = generate_token(client_id, pin, totp_secret)  # type: ignore[arg-type]
    except Exception as exc:
        raise AuthenticationError(f"Token generation failed: {exc}") from exc
    persist_token(access_token, env_path)
    return access_token

from __future__ import annotations

import logging
import re
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING

import pyotp
import requests

from scalpr.adapters.dhan._types import (
    DhanAuthError,
    DhanAuthResponse,
    DhanTokenRefreshThrottled,
)

if TYPE_CHECKING:
    from scalpr.engine.clock import Clock

logger = logging.getLogger(__name__)

TOKEN_URL = "https://auth.dhan.co/app/generateAccessToken"  # noqa: S105
PROFILE_URL = "https://api.dhan.co/v2/profile"
REFRESH_THRESHOLD = 0.8

# Token cache directory for daily file-based token persistence.
# Each token file is named token_{client_id}_{date}.txt and stores
# the token + expiry, enabling reuse across process restarts without
# re-minting via TOTP (which is rate-limited to once per 2 minutes).
_TOKEN_CACHE_DIR = Path("runtime-dev") / "tokens"


# Error classes imported from _types.py


def _decode_jwt_exp(token: str) -> datetime | None:
    """Decode the ``exp`` claim from a JWT. Returns None if not parseable."""
    import base64
    import json
    try:
        payload_b64 = token.split(".")[1]
        payload_b64 += "=" * (-len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        return datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    except (IndexError, KeyError, ValueError, TypeError):
        return None


def _sanitise_client_id(client_id: str) -> str:
    """Strip non-alphanumeric characters for safe filename use."""
    return re.sub(r"[^A-Za-z0-9_-]", "_", client_id)


def _token_cache_path(client_id: str) -> Path:
    """Return the daily token file path for the given client ID."""
    _TOKEN_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    safe = _sanitise_client_id(client_id)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return _TOKEN_CACHE_DIR / f"token_{safe}_{today}.txt"


def _read_cached_token(path: Path) -> str | None:
    """Read token from cache file. Returns None if missing or malformed.

    File format: ``{date}|{token}|{expiry_time}``
    """
    if not path.exists():
        return None
    try:
        raw = path.read_text(encoding="utf-8").strip()
        parts = raw.split("|")
        return parts[1].strip() if len(parts) >= 2 else raw.strip()
    except OSError:
        return None


def _write_token_cache(path: Path, token: str, expiry: str = "") -> None:
    """Write token to cache file, deleting any older token files first.

    This ensures only today's token file exists, avoiding stale-token
    reuse after Dhan rate-limits TOTP generation.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    # Clean up old token files for this client
    safe = _sanitise_client_id(path.stem.split("_")[1]) if "_" in path.stem else "unknown"
    for old in path.parent.glob(f"token_{safe}_*.txt"):
        if old != path:
            try:
                old.unlink()
            except OSError:
                pass
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path.write_text(f"{today}|{token}|{expiry}", encoding="utf-8")


def _validate_token_via_profile(token: str, client_id: str) -> dict | None:
    """Validate an access token by calling the Dhan profile endpoint.

    Returns the profile dict on success, None on failure.
    """
    try:
        resp = requests.get(
            PROFILE_URL,
            headers={
                "access-token": token,
                "client-id": client_id,
                "Accept": "application/json",
            },
            timeout=10,
        )
        if resp.status_code != 200:
            return None
        return resp.json()
    except requests.RequestException:
        return None


TOTP_COOLDOWN_SECONDS = 125  # Dhan rate-limits to 1 per 2 min; add 5s safety
TOKEN_EXPIRY_WARNING_SECONDS = 3600  # Warn when token has < 1 hour remaining


class TokenManager:
    """Thread-safe Dhan token manager with auto-refresh and daily file cache.

    On startup, tries to load a cached token from ``runtime-dev/tokens/``.
    If the cached token is still fresh (validated via JWT expiry), it is
    reused — avoiding an unnecessary TOTP mint (rate-limited to once per 2
    minutes by Dhan). On successful mint, the new token is persisted to the
    daily cache file.

    TOTP rate-limit resilience:
    - Tracks the last TOTP mint attempt timestamp
    - Skips TOTP if the cooldown (125s) hasn't elapsed since the last attempt
    - Warns proactively when the token has < 1 hour until expiry
    """

    def __init__(self, client_id: str, totp_secret: str, clock: Clock, *,
                 pin: str = "1111", initial_token: str | None = None,
                 cache_dir: str | Path | None = None) -> None:
        self._client_id = client_id
        self._totp_secret = totp_secret
        self._pin = pin
        self._clock = clock
        self._lock = threading.Lock()
        self._cache_path = Path(cache_dir) / _token_cache_path(client_id).name if cache_dir else _token_cache_path(client_id)
        self._last_totp_attempt: float = 0.0  # time.monotonic() of last TOTP call
        self._refresh_timer: threading.Timer | None = None

        # Prefer initial_token from env, then try file cache
        token = initial_token or _read_cached_token(self._cache_path)
        if token:
            exp = _decode_jwt_exp(token)
            self._token = token
            self._expires_at = exp or (clock.utc_now())
            # Log cache hit for observability
            if not initial_token:
                logger.info("dhan_token_cache_hit: path=%s expires_at=%s",
                            self._cache_path, self._expires_at.isoformat() if exp else "unknown")
        else:
            self._token = None
            self._expires_at = None

    # ── Public API ──────────────────────────────────────────────────────────

    def get_token(self) -> str:
        """Return a valid token, refreshing if expired or absent.

        Thread-safe: only one thread enters the refresh path.
        Respects TOTP cooldown — skips refresh if Dhan is rate-limiting.
        """
        if self._token is not None and self._is_fresh():
            self._warn_if_expiry_near()
            return self._token
        if self._in_totp_cooldown():
            raise DhanTokenRefreshThrottled(
                f"TOTP refresh blocked by Dhan rate limit (cooldown ~{TOTP_COOLDOWN_SECONDS}s, "
                f"last attempt was {time.monotonic() - self._last_totp_attempt:.0f}s ago). "
                f"Token expired at {self._expires_at.isoformat() if self._expires_at else '?'}."
            )
        return self.refresh_token()

    def is_token_fresh(self) -> bool:
        """Check if stored token is fresh without refreshing.

        Returns False when no token is stored.
        """
        if self._token is None or self._expires_at is None:
            return False
        return self._is_fresh()

    def refresh_token(self) -> str:
        """Force a token refresh. Thread-safe with double-check locking."""
        with self._lock:
            if self._token is not None and self._is_fresh():
                return self._token
            if self._in_totp_cooldown():
                remaining = TOTP_COOLDOWN_SECONDS - (time.monotonic() - self._last_totp_attempt)
                raise DhanTokenRefreshThrottled(
                    f"TOTP refresh rate-limited. Wait {remaining:.0f}s before retrying.",
                    remaining_seconds=remaining,
                )
            try:
                resp = self._mint_token()
            except DhanTokenRefreshThrottled:
                self._last_totp_attempt = time.monotonic()
                raise
            self._last_totp_attempt = 0.0  # Reset cooldown on success
            self._token = resp.access_token
            exp = _decode_jwt_exp(resp.access_token)
            expires_at = exp or (
                self._clock.utc_now()
                + timedelta(seconds=86400)
            )
            self._expires_at = expires_at
            # Persist to daily cache
            _write_token_cache(self._cache_path, resp.access_token, resp.expires_at)
            logger.info(
                "dhan_token_refreshed: expires_at=%s cache=%s",
                self._expires_at.isoformat(), self._cache_path,
            )
            self._schedule_proactive_refresh()
            return self._token

    def clear_cache(self) -> None:
        """Delete the daily token cache file. Useful for forced re-auth."""
        with self._lock:
            self._token = None
            self._expires_at = None
            try:
                self._cache_path.unlink(missing_ok=True)
                logger.info("dhan_token_cache_cleared: %s", self._cache_path)
            except OSError:
                pass

    def stop(self) -> None:
        """Cancel the proactive refresh timer. Called during shutdown."""
        self._cancel_proactive_refresh()

    def _schedule_proactive_refresh(self) -> None:
        if type(self._clock).__name__ == "StaticClock":
            return
        remaining = self.time_until_expiry()
        if remaining <= 0:
            return
        threshold_remaining = 86400.0 * (1.0 - REFRESH_THRESHOLD)
        delay = max(0.0, remaining - threshold_remaining)
        if delay < 1.0:
            return
        self._cancel_proactive_refresh()
        self._refresh_timer = threading.Timer(delay, self.refresh_token)
        self._refresh_timer.daemon = True
        self._refresh_timer.start()

    def _cancel_proactive_refresh(self) -> None:
        timer = self._refresh_timer
        if timer is not None:
            timer.cancel()
            self._refresh_timer = None

    def time_until_expiry(self) -> float:
        """Seconds until the current token expires. Returns 0 if no token."""
        if self._expires_at is None:
            return 0.0
        now = self._clock.utc_now()
        delta = self._expires_at - now
        if delta.total_seconds() <= 0:
            return 0.0
        return delta.total_seconds()

    # ── Internal ────────────────────────────────────────────────────────────

    def _is_fresh(self) -> bool:
        """Check if token has exceeded the refresh threshold."""
        if self._expires_at is None:
            return False
        now = self._clock.utc_now()
        if self._expires_at.tzinfo is not None and now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        total_lifetime = (self._expires_at - now).total_seconds()
        if total_lifetime <= 0:
            return False
        elapsed = 1.0 - (total_lifetime / 86400.0)
        return elapsed < REFRESH_THRESHOLD

    def _warn_if_expiry_near(self) -> None:
        """Log a warning if the token is approaching expiry."""
        remaining = self.time_until_expiry()
        if 0 < remaining < TOKEN_EXPIRY_WARNING_SECONDS:
            logger.warning(
                "dhan_token_expiry_approaching: expires_at=%s remaining=%.0fs "
                "— refresh token or set a new DHAN_ACCESS_TOKEN in .env",
                self._expires_at.isoformat() if self._expires_at else "?",
                remaining,
            )

    def _in_totp_cooldown(self) -> bool:
        """Check if we're still inside the TOTP rate-limit window."""
        if self._last_totp_attempt == 0.0:
            return False
        elapsed = time.monotonic() - self._last_totp_attempt
        return elapsed < TOTP_COOLDOWN_SECONDS

    def _mint_token(self) -> DhanAuthResponse:
        """Call the Dhan auth endpoint to mint a new token."""
        totp_code = pyotp.TOTP(self._totp_secret).now()
        try:
            resp = requests.post(
                TOKEN_URL,
                data={
                    "dhanClientId": self._client_id,
                    "pin": self._pin,
                    "totp": totp_code,
                },
                timeout=15,
            )
        except requests.RequestException as exc:
            raise DhanAuthError(f"Network error during auth: {exc}") from exc

        if resp.status_code != 200:
            raise DhanAuthError(
                f"Dhan auth failed: HTTP {resp.status_code}: {resp.text}"
            )

        body = resp.json()
        message = str(body.get("message", ""))
        if "once every 2 minutes" in message:
            raise DhanTokenRefreshThrottled(
                f"Dhan TOTP rate limit: {message}",
            )

        access_token = body.get("accessToken", "")
        if not access_token:
            raise DhanAuthError(f"Token missing in response: {body}")

        return DhanAuthResponse(
            access_token=access_token,
            expires_at=body.get("expiryTime", ""),
            token_type="Bearer",  # noqa: S106
        )

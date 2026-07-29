from __future__ import annotations

import logging
import re
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING

import pyotp
import requests

from scalpr.adapters.dhan._types import DhanAuthResponse

if TYPE_CHECKING:
    from scalpr.engine.clock import Clock

logger = logging.getLogger(__name__)

TOKEN_URL = "https://auth.dhan.co/app/generateAccessToken"
PROFILE_URL = "https://api.dhan.co/v2/profile"
REFRESH_THRESHOLD = 0.9

# Token cache directory for daily file-based token persistence.
# Each token file is named token_{client_id}_{date}.txt and stores
# the token + expiry, enabling reuse across process restarts without
# re-minting via TOTP (which is rate-limited to once per 2 minutes).
_TOKEN_CACHE_DIR = Path("runtime-dev") / "tokens"


class DhanAuthError(Exception):
    """Raised when Dhan authentication fails."""


class DhanTokenExpired(DhanAuthError):
    """Raised when the token has expired and refresh was requested."""


class DhanTokenRefreshThrottled(DhanAuthError):
    """Raised when TOTP generation is blocked by cooldown."""

    def __init__(self, message: str, *, remaining_seconds: float = 0.0) -> None:
        super().__init__(message)
        self.remaining_seconds = remaining_seconds


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


class TokenManager:
    """Thread-safe Dhan token manager with auto-refresh and daily file cache.

    On startup, tries to load a cached token from ``runtime-dev/tokens/``.
    If the cached token is still fresh (validated via JWT + optional profile
    check), it is reused — avoiding an unnecessary TOTP mint (rate-limited
    to once per 2 minutes by Dhan). On successful mint, the new token is
    persisted to the daily cache file.
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
        """
        if self._token is not None and self._is_fresh():
            return self._token
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
            resp = self._mint_token()
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
            token_type="Bearer",
        )

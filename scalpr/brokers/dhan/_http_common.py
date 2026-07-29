"""Shared HTTP client logic — single source of truth for sync/async clients.

Extracts constants, helpers, and stateless logic shared by
:class:`DhanHttpClient` (sync) and :class:`AsyncDhanHttpClient` (async).
Both clients import from here instead of duplicating the logic.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# ── Endpoint → rate-limit bucket mapping ────────────────────────────────────
# Single source of truth shared by both sync and async clients.
_ENDPOINT_BUCKETS: dict[str, str] = {
    "/marketfeed/quote": "quotes",
    "/marketfeed/ltp": "historical",
    "/marketfeed/ohlc": "historical",
    "/optionchain": "optionchain",
    "/charts/": "historical",
    "/orders": "orders",
    "/profile": "admin",
    "/fundlimit": "admin",
    "/positions": "admin",
    "/holdings": "admin",
    "/orderbook": "admin",
    "/tradebook": "admin",
}
_DEFAULT_BUCKET = "admin"

# ── Retry / backoff configuration ───────────────────────────────────────────
_MAX_RETRIES = 3
_BASE_DELAY_MS = 500
_MAX_DELAY_MS = 5000
# Cooldown is now owned by _totp_cooldown.py (single source of truth).
# The HTTP client no longer has its own refresh cooldown — it delegates
# to ensure_fresh_token which checks the TOTP cooldown guard.

# Fail-fast timeout for the orders bucket — order path must never block.
_ORDERS_ACQUIRE_TIMEOUT_S = 0.5


def bucket_for(endpoint: str) -> str:
    """Resolve endpoint to rate-limit bucket name via prefix match."""
    if endpoint in _ENDPOINT_BUCKETS:
        return _ENDPOINT_BUCKETS[endpoint]
    for prefix, bucket in _ENDPOINT_BUCKETS.items():
        if endpoint.startswith(prefix):
            return bucket
    return _DEFAULT_BUCKET


def backoff_delay(attempt: int) -> float:
    """Exponential backoff: 500ms, 1s, 2s, 4s... capped at 5s."""
    delay_ms: int = min(_BASE_DELAY_MS * (2 ** (attempt - 1)), _MAX_DELAY_MS)
    return delay_ms / 1000.0


def try_refresh_token(
    token_refresh_fn: Any,
    update_token_fn: Any,
    client_id: str,
    is_expiring_soon_fn: Any = None,
) -> bool:
    """Attempt token refresh. Returns True if successful.

    Cooldown is enforced by the TOTP cooldown guard (single source of truth).
    This helper no longer has its own cooldown layer.

    Args:
        is_expiring_soon_fn: Optional callable returning True when the
            current token is near expiry. When provided and returns False,
            the refresh is skipped — a 401 on a fresh token is likely
            a scope/entitlement error, not staleness.
    """
    if token_refresh_fn is None:
        return False

    if is_expiring_soon_fn is not None and not is_expiring_soon_fn():
        logger.info("token_refresh_skipped: token_is_fresh_not_expiring_soon")
        return False

    try:
        new_token = token_refresh_fn()
        if new_token:
            update_token_fn(new_token)
            logger.info("token_refreshed", extra={"client_id": client_id})
            return True
    except Exception as exc:
        logger.warning("token_refresh_failed", extra={"error": str(exc)})

    return False


def build_url(base_url: str, endpoint: str) -> str:
    """Build full URL from base_url and endpoint."""
    return f"{base_url}{endpoint}" if endpoint.startswith("/") else endpoint


def classify_response(status: int, text: str) -> str:
    """Classify HTTP response into a category for decision-making.

    Returns one of: 'success', 'auth_rejected', 'rate_limited',
    'server_error', 'client_error'.
    """
    if status < 400:
        return "success"

    # 401 — or Dhan's DH-906 "Invalid Token" (arrives as HTTP 400)
    if status == 401 or (status >= 400 and "DH-906" in (text or "")):
        return "auth_rejected"

    if status == 429:
        return "rate_limited"

    if status >= 500:
        return "server_error"

    return "client_error"

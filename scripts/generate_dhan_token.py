#!/usr/bin/env python
"""Ensure a fresh Dhan access token, minting via TOTP only when needed.

Probe-before-mint (mirrors Trade_XV2 v2 policy): a fresh cached token in
.env is returned with zero network calls. Minting revokes the previously
issued token broker-side and burns Dhan's 2-minute TOTP rate limit, so
we never mint unless the token is stale or --force is passed.

Usage:
    python scripts/generate_dhan_token.py            # mint only if stale
    python scripts/generate_dhan_token.py --force    # always re-mint
"""

import argparse
import sys

from dotenv import load_dotenv

from config.secrets_manager import SecretsManager
from scalpr.brokers.dhan._totp_cooldown import TotpRateLimitError
from scalpr.brokers.dhan.auth import (
    ensure_fresh_token,
    is_token_fresh,
    token_expiry,
)
from scalpr.brokers.dhan.exceptions import ConfigurationError


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force",
        action="store_true",
        help="re-mint even if the cached token is still fresh "
        "(revokes the previous token and arms the 2-minute cooldown)",
    )
    args = parser.parse_args(argv)

    load_dotenv()
    secrets = SecretsManager()

    cached = secrets.get_dhan_access_token()
    if cached and is_token_fresh(cached) and not args.force:
        print("✅ Cached token is still fresh — no mint needed")
        print(f"   Expires: {token_expiry(cached)}")
        print("   Use --force to re-mint anyway")
        return

    try:
        access_token = ensure_fresh_token(force=args.force, wait_for_cooldown=True)
    except ConfigurationError as exc:
        print(f"❌ {exc}")
        print("Required: DHAN_CLIENT_ID, DHAN_PIN, DHAN_TOTP_SECRET")
        sys.exit(1)
    except TotpRateLimitError as exc:
        print(f"❌ TOTP cooldown still active: {exc}")
        sys.exit(1)

    print("\n✅ Token is fresh!")
    print(f"   Expires: {token_expiry(access_token)}")
    print(f"   Token: {access_token[:60]}...")
    print("✅ Token saved to .env")


if __name__ == "__main__":
    main()

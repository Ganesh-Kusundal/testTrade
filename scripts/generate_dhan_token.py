#!/usr/bin/env python
"""Generate fresh Dhan access token using TOTP.

Always regenerates (force refresh). For expiry-aware refresh, use
``scalpr.brokers.dhan.auth.ensure_fresh_token`` instead.

Usage:
    python scripts/generate_dhan_token.py
"""

import sys
from pathlib import Path

from dotenv import load_dotenv

from config.secrets_manager import SecretsManager
from scalpr.brokers.dhan.auth import generate_token, persist_token, token_expiry


def main() -> None:
    load_dotenv()
    secrets = SecretsManager()
    client_id = secrets.get_dhan_client_id()
    pin = secrets.get_dhan_pin()
    totp_secret = secrets.get_dhan_totp_secret()

    if not all([client_id, pin, totp_secret]):
        print("❌ Missing credentials in .env file")
        print("Required: DHAN_CLIENT_ID, DHAN_PIN, DHAN_TOTP_SECRET")
        sys.exit(1)

    print(f"📡 Requesting token for client: {client_id}...")
    access_token = generate_token(client_id, pin, totp_secret)
    persist_token(access_token, Path(".env"))

    print("\n✅ Token generated successfully!")
    print(f"   Expires: {token_expiry(access_token)}")
    print(f"   Token: {access_token[:60]}...")
    print("✅ Token saved to .env")


if __name__ == "__main__":
    main()

"""Check Dhan gateway connection is working.

Usage:
    python scripts/live/check_dhan_connection.py

Reads DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN from .env (or environment).
Exits 0 on success, 1 on failure.
"""
from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

load_dotenv(".env")

from scalpr.brokers.dhan.gateway import DhanGateway


def main() -> None:
    client_id = os.getenv("DHAN_CLIENT_ID", "")
    access_token = os.getenv("DHAN_ACCESS_TOKEN", "")

    if not client_id or not access_token:
        print("ERROR: DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN must be set in .env")
        sys.exit(1)

    gateway = DhanGateway({
        "client_id": client_id,
        "access_token": access_token,
    })

    try:
        gateway.connect()
    except Exception as e:
        print(f"Connection failed: {e}")
        sys.exit(1)

    if gateway.is_connected():
        print("Connected to Dhan successfully.")

        # Quick sanity check — fetch fund limits
        try:
            limits = gateway.get_margins()
            print(f"Available margin: {limits.get('available_margin')}")
            print(f"Total balance:  {limits.get('total_balance')}")
        except Exception as e:
            print(f"Connected but fund limits call failed: {e}")
    else:
        print("Not connected after connect() call.")
        sys.exit(1)

    gateway.disconnect()
    print("Disconnected cleanly.")


if __name__ == "__main__":
    main()

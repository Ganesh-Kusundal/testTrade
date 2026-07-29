#!/usr/bin/env python3
"""DhanClient example: funds, positions, holdings, and P&L.

Usage:
    export DHAN_CLIENT_ID=...
    export DHAN_ACCESS_TOKEN=...
    export DHAN_TOTP_SECRET=...
    python3 examples/adapters/dhan/01_funds_and_positions.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from scalpr.adapters.dhan.client import DhanClient
from scalpr.engine.clock import LiveClock
from scalpr.engine.message_bus import MessageBus


def main() -> None:
    load_dotenv()

    client_id = os.getenv("DHAN_CLIENT_ID")
    access_token = os.getenv("DHAN_ACCESS_TOKEN")
    totp_secret = os.getenv("DHAN_TOTP_SECRET", "")

    if not client_id or not access_token:
        print("ERROR: DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN must be set.")
        print("Tip: cp .env.example .env and fill in your credentials.")
        sys.exit(1)

    bus = MessageBus()
    clock = LiveClock()
    config = {
        "client_id": client_id,
        "access_token": access_token,
        "totp_secret": totp_secret,
        "csv_path": str(Path("instrument.csv")),
    }

    client = DhanClient(bus, clock, config)

    print("=" * 60)
    print("  DhanClient – Funds, Positions & PnL")
    print("=" * 60)

    # ── Funds / Limits ─────────────────────────────────────────────
    print("\n[1/5] get_funds() ── Available margin & limits")
    try:
        funds = client.get_funds()
        for k, v in funds.items():
            print(f"  {k}: {v}")
    except Exception as e:
        print(f"  ERROR: {e}")

    # ── Positions ──────────────────────────────────────────────────
    print("\n[2/5] get_positions() ── Open positions")
    try:
        positions = client.get_positions()
        print(f"  Count: {len(positions)}")
        for p in positions:
            print(f"    {p.symbol:20s} qty={p.quantity:+5d}  "
                  f"avg={float(p.avg_price):10.2f}  "
                  f"unrealised={float(p.unrealised_pnl):+8.2f}")
    except Exception as e:
        print(f"  ERROR: {e}")

    # ── Holdings ───────────────────────────────────────────────────
    print("\n[3/5] get_holdings() ── Delivery holdings")
    try:
        holdings = client.get_holdings()
        if isinstance(holdings, dict):
            for k, v in holdings.items():
                if isinstance(v, list):
                    print(f"  {k}: {len(v)} items")
                    for item in v[:5]:
                        print(f"    {item}")
                else:
                    print(f"  {k}: {v}")
        else:
            print(f"  {holdings}")
    except Exception as e:
        print(f"  ERROR: {e}")

    # ── Live P&L ───────────────────────────────────────────────────
    print("\n[4/5] get_live_pnl() ── Day MTM P&L")
    try:
        pnl = client.get_live_pnl()
        print(f"  Live P&L: {pnl:+.2f}")
    except Exception as e:
        print(f"  ERROR: {e}")

    # ── Positions Summary ──────────────────────────────────────────
    print("\n[5/5] get_positions_summary() ── Aggregated portfolio")
    try:
        summary = client.get_positions_summary()
        for k, v in summary.items():
            print(f"  {k}: {v}")
    except Exception as e:
        print(f"  ERROR: {e}")

    print("\nDone.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""DhanClient example: option chain, expiry list, and strike selection.

Usage:
    export DHAN_CLIENT_ID=...
    export DHAN_ACCESS_TOKEN=...
    export DHAN_TOTP_SECRET=...
    python3 examples/adapters/dhan/02_option_chain.py
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from scalpr.adapters.dhan.client import DhanClient
from scalpr.engine.clock import LiveClock
from scalpr.engine.message_bus import MessageBus

logging.basicConfig(level=logging.WARNING)


def main() -> None:
    load_dotenv()

    client_id = os.getenv("DHAN_CLIENT_ID")
    access_token = os.getenv("DHAN_ACCESS_TOKEN")
    totp_secret = os.getenv("DHAN_TOTP_SECRET", "")

    if not client_id or not access_token:
        print("ERROR: DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN must be set.")
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

    try:
        client.start()
    except Exception as e:
        print(f"  [info] start() note: {e}")

    print("=" * 60)
    print("  DhanClient – Option Chain & Expiry")
    print("=" * 60)

    # ── Expiry lists ───────────────────────────────────────────────
    print("\n[1/5] Expiries: NIFTY (NSE)")
    try:
        nifty_exp = client.get_expiry_list("NIFTY", "NSE")
        for i, d in enumerate(nifty_exp):
            print(f"  [{i}] {d}")
    except Exception as e:
        print(f"  ERROR: {e}")

    print("\n[2/5] Expiries: CRUDEOIL (MCX)")
    try:
        crude_exp = client.get_expiry_list("CRUDEOIL", "MCX")
        for i, d in enumerate(crude_exp):
            print(f"  [{i}] {d}")
    except Exception as e:
        print(f"  ERROR: {e}")

    # ── Option chain (NIFTY nearest expiry) ────────────────────────
    print(f"\n[3/5] Option chain: NIFTY @ {nifty_exp[0] if nifty_exp else '?'}")
    try:
        chain = client.get_option_chain("NIFTY", "NSE")
        print(f"  Underlying: {chain.get('underlying')}")
        print(f"  Exchange:   {chain.get('exchange')}")
        print(f"  Expiry:     {chain.get('expiry')}")
        strikes = chain.get("strikes", [])
        print(f"  Total strikes: {len(strikes)}")
    except Exception as e:
        print(f"  ERROR: {e}")
        strikes = []

    # ── ATM / OTM / ITM strikes ────────────────────────────────────
    print("\n[4/5] ATM / OTM / ITM strikes")
    try:
        atm_ce, atm_pe, atm_price = client.atm_strike("NIFTY", 0, "NSE")
        print(f"  ATM strike={atm_price:.0f}  ce={atm_ce}  pe={atm_pe}")
    except Exception as e:
        print(f"  ATM ERROR: {e}")

    try:
        otm_ce, otm_pe, otm_ce_strike, otm_pe_strike = client.otm_strike("NIFTY", 0, 1, "NSE")
        print(f"  OTM ce_strike={otm_ce_strike:.0f}  ce={otm_ce}")
        print(f"  OTM pe_strike={otm_pe_strike:.0f}  pe={otm_pe}")
    except Exception as e:
        print(f"  OTM ERROR: {e}")

    try:
        itm_ce, itm_pe, itm_ce_strike, itm_pe_strike = client.itm_strike("NIFTY", 0, 1, "NSE")
        print(f"  ITM ce_strike={itm_ce_strike:.0f}  ce={itm_ce}")
        print(f"  ITM pe_strike={itm_pe_strike:.0f}  pe={itm_pe}")
    except Exception as e:
        print(f"  ITM ERROR: {e}")

    # ── Step sizes ─────────────────────────────────────────────────
    print("\n[5/5] Strike / step sizes")
    known = {"NIFTY": 50.0, "BANKNIFTY": 100.0, "FINNIFTY": 50.0, "SENSEX": 100.0}
    for sym, step in known.items():
        print(f"  {sym}: step={step:.0f}")

    try:
        client.stop()
    except Exception:
        pass

    print("\nDone.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""DhanClient example: options greeks from chain + local Black-Scholes.

Usage:
    export DHAN_CLIENT_ID=...
    export DHAN_ACCESS_TOKEN=...
    export DHAN_TOTP_SECRET=...
    python3 examples/adapters/dhan/04_greeks.py
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from scalpr.adapters.dhan._greeks import GreeksCalculator
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
    print("  DhanClient – Options Greeks")
    print("=" * 60)

    # ── Resolve nearest expiry + ATM strike ────────────────────────
    print("\n[1/3] Finding NIFTY ATM strike for nearest expiry...")
    try:
        atm_ce, atm_pe, atm_strike = client.atm_strike("NIFTY", 0, "NSE")
        expiries = client.get_expiry_list("NIFTY", "NSE")
        near_expiry = expiries[0] if expiries else "unknown"
        print(f"  Nearest expiry:  {near_expiry}")
        print(f"  ATM strike:      {atm_strike:.0f}")
        print(f"  ATM CE symbol:   {atm_ce}")
        print(f"  ATM PE symbol:   {atm_pe}")
    except Exception as e:
        print(f"  ERROR resolving ATM strike: {e}")
        sys.exit(1)

    # ── Greeks from Dhan chain ─────────────────────────────────────
    print(f"\n[2/3] Greeks from option chain (NIFTY {atm_strike:.0f} CE)")
    try:
        greeks = client.get_greeks("NIFTY", near_expiry, atm_strike, "CE", "NSE")
        if greeks:
            print(f"  Source: {greeks.get('source', 'chain')}")
            print(f"  Delta:  {greeks.get('delta')}")
            print(f"  Gamma:  {greeks.get('gamma')}")
            print(f"  Theta:  {greeks.get('theta')}")
            print(f"  Vega:   {greeks.get('vega')}")
            print(f"  IV:     {greeks.get('iv')}")
            print(f"  LTP:    {greeks.get('ltp')}")
        else:
            print("  (no greeks returned from chain)")
    except Exception as e:
        print(f"  ERROR: {e}")

    # ── Local Black-Scholes ────────────────────────────────────────
    print(f"\n[3/3] Local Black-Scholes greeks (NIFTY {atm_strike:.0f} CE)")
    try:
        calc = GreeksCalculator()
        bs = calc.calculate_greeks(
            underlying_price=float(atm_strike),
            strike=float(atm_strike),
            days_to_expiry=7,
            option_type="CE",
            interest_rate=0.1,
            volatility=0.15,
        )
        print(f"  Delta:      {bs['delta']:.4f}")
        print(f"  Gamma:      {bs['gamma']:.4f}")
        print(f"  Theta:      {bs['theta']:.4f}")
        print(f"  Vega:       {bs['vega']:.4f}")
        print(f"  IV:         {bs['iv']:.2f}%")
        print(f"  Call price: {bs['call_price']:.2f}")
        print(f"  Put price:  {bs['put_price']:.2f}")
        print()
        print("  Note: local BS uses hypothetical parameters.")
        print("  For live greeks use get_greeks() which pulls from the Dhan chain.")
    except Exception as e:
        print(f"  ERROR: {e}")

    try:
        client.stop()
    except Exception:
        pass

    print("\nDone.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""DhanClient example: historical and intraday candle data.

Usage:
    export DHAN_CLIENT_ID=...
    export DHAN_ACCESS_TOKEN=...
    export DHAN_TOTP_SECRET=...
    python3 examples/adapters/dhan/03_historical_data.py
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
    print("  DhanClient – Historical & Intraday Data")
    print("=" * 60)

    # ── Intraday (5 min) for NIFTY ─────────────────────────────────
    print("\n[1/3] get_intraday() ── NIFTY (NSE, 5min)")
    try:
        candles = client.get_intraday("NIFTY", "NSE", interval=5)
        print(f"  Candles returned: {len(candles)}")
        if candles:
            last = candles[-1]
            print("\n  Latest candle:")
            print(f"    Time:   {last.get('timestamp')}")
            print(f"    Open:   {last.get('open'):.2f}")
            print(f"    High:   {last.get('high'):.2f}")
            print(f"    Low:    {last.get('low'):.2f}")
            print(f"    Close:  {last.get('close'):.2f}")
            print(f"    Volume: {last.get('volume')}")
            first = candles[0]
            print("\n  First candle:")
            print(f"    Time:   {first.get('timestamp')}")
            print(f"    Open:   {first.get('open'):.2f}")
    except Exception as e:
        print(f"  ERROR: {e}")

    # ── Daily data for NIFTY ───────────────────────────────────────
    print("\n[2/3] get_daily() ── NIFTY daily candles")
    try:
        daily = client.get_daily("NIFTY", "NSE")
        print(f"  Daily candles returned: {len(daily)}")
        if daily:
            last = daily[-1]
            print("\n  Latest daily:")
            print(f"    Date:   {last.get('timestamp')}")
            print(f"    Open:   {last.get('open'):.2f}")
            print(f"    High:   {last.get('high'):.2f}")
            print(f"    Low:    {last.get('low'):.2f}")
            print(f"    Close:  {last.get('close'):.2f}")
            print(f"    Volume: {last.get('volume')}")
    except Exception as e:
        print(f"  ERROR: {e}")

    # ── LTP ────────────────────────────────────────────────────────
    print("\n[3/3] get_quote() ── Live price snapshot (NIFTY)")
    try:
        from scalpr.domain.instrument import Exchange, SimpleInstrumentId
        inst_id = SimpleInstrumentId("NIFTY", Exchange.NSE)
        quote = client.get_quote(inst_id)
        for k, v in quote.items():
            print(f"  {k}: {v}")
    except Exception as e:
        print(f"  ERROR: {e}")

    try:
        client.stop()
    except Exception:
        pass

    print("\nDone.")


if __name__ == "__main__":
    main()

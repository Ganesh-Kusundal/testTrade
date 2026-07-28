"""Live test: market feed in FULL mode + 20-level market depth.

Part 1 — DhanWebSocketClient in mode="full" (SDK MarketFeed.Full packets).
Part 2 — 20-level depth via SDK FullDepth (wss depth_20_feed; NSE/NSE_FNO only).

Canonical symbols only — the broker resolver owns the security_id mapping.
"""

import asyncio
import os
import sys
import time
from datetime import datetime

from dotenv import load_dotenv

load_dotenv(".env")

from scalpr.brokers.dhan.loader import InstrumentLoader
from scalpr.brokers.dhan.resolver import SymbolResolver
from scalpr.brokers.dhan.ws_client import DhanWebSocketClient
from scalpr.domain.tick import Tick

RUN_SECONDS = 20
SYMBOLS = [("RELIANCE", "NSE"), ("TCS", "NSE"), ("NIFTY", "NSE")]
DEPTH_SYMBOLS = [("RELIANCE", "NSE"), ("TCS", "NSE")]  # 20-depth: NSE/NSE_FNO only


def _now() -> str:
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


async def test_full_mode(client_id: str, token: str, resolver: SymbolResolver) -> int:
    print("=" * 80)
    print(f"PART 1: Market feed FULL mode — {[s for s, _ in SYMBOLS]} for {RUN_SECONDS}s")
    print("=" * 80)

    tick_count = [0]

    def on_tick(tick: Tick) -> None:
        tick_count[0] += 1
        if tick_count[0] <= 5 or tick_count[0] % 25 == 0:
            print(
                f"[{_now()}] #{tick_count[0]:>4} {tick.symbol:<10} "
                f"LTP={tick.ltp} bid={tick.bid} ask={tick.ask} "
                f"dVol={tick.delta_volume} cumVol={tick.cumulative_volume}"
            )

    client = DhanWebSocketClient(
        access_token=token, client_id=client_id, mode="full", resolver=resolver
    )
    client.on_tick(on_tick)

    await client.connect()
    print(f"[{_now()}] connected: {client}")
    await client.subscribe(SYMBOLS)
    print(f"[{_now()}] subscribed (full mode): {client.subscriptions}")

    await asyncio.sleep(RUN_SECONDS)
    await client.disconnect()

    print(f"\nFULL MODE RESULT: {tick_count[0]} ticks in {RUN_SECONDS}s")
    return tick_count[0]


def test_depth_20(client_id: str, token: str, resolver: SymbolResolver) -> int:
    print("\n" + "=" * 80)
    print(f"PART 2: 20-level market depth — {[s for s, _ in DEPTH_SYMBOLS]} for {RUN_SECONDS}s")
    print("=" * 80)

    from dhanhq.fulldepth import FullDepth

    class _Ctx:
        def get_client_id(self) -> str:
            return client_id

        def get_access_token(self) -> str:
            return token

    # Resolve canonical symbols to (exchange_int, security_id) for the SDK
    sid_to_symbol = {}
    instruments = []
    for sym, exch in DEPTH_SYMBOLS:
        inst = resolver.resolve(sym, exch)
        wire = resolver.wire_segment_of(sym, exch)
        exch_int = FullDepth.NSE_FNO if wire == "NSE_FNO" else FullDepth.NSE
        instruments.append((exch_int, str(inst.security_id)))
        sid_to_symbol[str(inst.security_id)] = sym
        print(f"  {sym}/{exch} -> sid={inst.security_id} wire={wire}")

    depth = FullDepth(_Ctx(), instruments, depth_level=20)
    depth.run_forever()  # connects + subscribes

    updates = [0]
    deadline = time.monotonic() + RUN_SECONDS
    while time.monotonic() < deadline:
        try:
            data = depth.get_data()
        except Exception as exc:
            print(f"[{_now()}] get_data error: {type(exc).__name__}: {exc}")
            break
        if not data:
            continue
        entries = data if isinstance(data, list) else [data]
        for entry in entries:
            updates[0] += 1
            sid = str(entry.get("security_id", entry.get("SecurityId", "?")))
            sym = sid_to_symbol.get(sid, sid)
            levels = entry.get("depth", entry.get("data", []))
            n = len(levels) if isinstance(levels, list) else "?"
            if updates[0] <= 4 or updates[0] % 50 == 0:
                print(f"[{_now()}] #{updates[0]:>4} {sym:<10} levels={n}")
                if isinstance(levels, list) and levels:
                    for line in levels[:3]:
                        print(f"    {line}")

    try:
        depth.disconnect()
    except Exception:
        pass

    print(f"\nDEPTH-20 RESULT: {updates[0]} updates in {RUN_SECONDS}s")
    return updates[0]


def main() -> None:
    client_id = os.getenv("DHAN_CLIENT_ID")
    token = os.getenv("DHAN_ACCESS_TOKEN")
    if not client_id or not token:
        print("ERROR: DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN must be set in .env")
        sys.exit(1)

    resolver = SymbolResolver()
    resolver.load_from_rows(InstrumentLoader.load_cached())

    full_ticks = asyncio.run(test_full_mode(client_id, token, resolver))
    depth_updates = test_depth_20(client_id, token, resolver)

    print("\n" + "=" * 80)
    print(f"SUMMARY: full-mode ticks={full_ticks}, depth-20 updates={depth_updates}")
    print("=" * 80)
    sys.exit(0 if full_ticks > 0 and depth_updates > 0 else 1)


if __name__ == "__main__":
    main()

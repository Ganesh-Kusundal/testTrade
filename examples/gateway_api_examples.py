"""Gateway v0/v1 API — usage examples.

Run from project root:
    python examples/gateway_api_examples.py

Requires .env with DHAN_ACCESS_TOKEN, DHAN_CLIENT_ID etc.
"""
from __future__ import annotations

import os
import sys
from datetime import date

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()


# ──────────────────────────────────────────────────────────────────────────────
# 1. Gateway construction
# ──────────────────────────────────────────────────────────────────────────────

def demo_gateway_construction():
    """Show the three ways to create a Gateway."""
    from scalpr.brokers.gateway import Gateway

    # Default — uses .env credentials
    gw = Gateway()
    print(f"Gateway created: {gw}")
    return gw


# ──────────────────────────────────────────────────────────────────────────────
# 2. Instrument resolution — three calling conventions
# ──────────────────────────────────────────────────────────────────────────────

def demo_instrument_resolution(gw):
    """gw.instrument() accepts qualified strings, separate args, or domain objects."""
    from scalpr.domain.instrument import Exchange, Segment, SimpleInstrumentId

    # Convention 1: Qualified string
    tcs = gw.instrument("TCS:NSE")
    print(f"1. Qualified string:  {tcs.symbol} @ {tcs.exchange} (sid={tcs.security_id})")

    # Convention 2: Separate args (enum or string)
    reliance = gw.instrument("RELIANCE", Exchange.NSE)
    print(f"2. Separate args:     {reliance.symbol} @ {reliance.exchange}")

    # Convention 3: SimpleInstrumentId domain object
    sid = SimpleInstrumentId(symbol="INFY", exchange=Exchange.NSE)
    infy = gw.instrument(sid)
    print(f"3. Domain object:     {infy.symbol} @ {infy.exchange}")

    # Index with segment
    nifty = gw.instrument("NIFTY", Exchange.NSE, Segment.INDEX)
    print(f"4. Index:             {nifty.symbol} @ {nifty.exchange} (id={nifty.id})")

    # MCX commodity
    gold = gw.instrument("GOLD", "MCX")
    print(f"5. Commodity:         {gold.symbol} @ {gold.exchange}")

    return tcs, nifty


# ──────────────────────────────────────────────────────────────────────────────
# 3. Market data — ltp, quote, ohlc, depth, historical
# ──────────────────────────────────────────────────────────────────────────────

def demo_market_data(tcs):
    """InstrumentHandle market data methods."""

    # Last traded price
    price = tcs.ltp()
    print(f"LTP:  ₹{price}")

    # Full quote (all fields)
    q = tcs.quote()
    print(f"Quote: open={q.get('open')} high={q.get('high')} "
          f"low={q.get('low')} close={q.get('close')} vol={q.get('volume')}")

    # OHLC snapshot (convenience — extracts OHLC from quote)
    ohlc = tcs.ohlc()
    print(f"OHLC: O={ohlc['open']} H={ohlc['high']} L={ohlc['low']} C={ohlc['close']}")

    # Market depth (REST = 5 levels; use WS FULL for 20-level)
    depth = tcs.depth()
    print(f"Depth: best bid={depth.get('bids', [{}])[0].get('price', 'N/A')}, "
          f"best ask={depth.get('asks', [{}])[0].get('price', 'N/A')}")

    # Historical candles (default: 90 days daily)
    candles = tcs.historical(interval="1D", start="2025-01-01", end="2025-06-30")
    print(f"Historical: {len(candles)} candles from {candles[0]['timestamp']} "
          f"to {candles[-1]['timestamp']}")


# ──────────────────────────────────────────────────────────────────────────────
# 4. Option chain — with moneyness filtering
# ──────────────────────────────────────────────────────────────────────────────

def demo_option_chain(nifty):
    """Option chain with ATM/ITM/OTM filtering."""

    # ── Raw chain (all strikes, both CE and PE) ──
    all_legs = nifty.option_chain()
    print(f"\nRaw chain: {len(all_legs)} legs")
    print(f"  Sample: strike={all_legs[0]['strike']} "
          f"type={all_legs[0]['option_type']} "
          f"bid={all_legs[0]['bid']} ask={all_legs[0]['ask']}")

    # ── ATM only (strikes within 0.5% of spot) ──
    atm = nifty.option_chain(moneyness="ATM")
    print(f"\nATM legs: {len(atm)}")
    for leg in atm:
        print(f"  {leg['option_type']:2s} strike={leg['strike']:>10} "
              f"bid={leg['bid']:>8} ask={leg['ask']:>8} "
              f"oi={leg['oi']:>10} delta={leg.get('delta')}")

    # ── ITM only ──
    itm = nifty.option_chain(moneyness="ITM")
    print(f"\nITM legs: {len(itm)}")

    # ── OTM only ──
    otm = nifty.option_chain(moneyness="OTM")
    print(f"\nOTM legs: {len(otm)}")

    # ── Combination: ATM + ITM ──
    atm_itm = nifty.option_chain(moneyness="ATM,ITM")
    print(f"\nATM+ITM legs: {len(atm_itm)}")

    # ── N strikes around ATM ──
    around = nifty.option_chain(strikes_around=3)
    strikes = sorted({leg["strike"] for leg in around})
    print(f"\n3 strikes around ATM: {len(around)} legs across {len(strikes)} strikes")
    print(f"  Strikes: {strikes}")

    # ── Filter by option type ──
    ce_only = nifty.option_chain(option_type="CE")
    pe_only = nifty.option_chain(option_type="PE")
    print(f"\nCE legs: {len(ce_only)}, PE legs: {len(pe_only)}")

    # ── Combined: ATM calls, 2 strikes around ──
    atm_ce = nifty.option_chain(moneyness="ATM", strikes_around=2, option_type="CE")
    print(f"\nATM CE (2 around): {len(atm_ce)} legs")
    for leg in atm_ce:
        print(f"  {leg['option_type']} strike={leg['strike']} "
              f"moneyness={leg['moneyness']} spot={leg['spot_price']}")

    # ── Specific expiry ──
    chain_expiry = nifty.option_chain(expiry=date(2026, 8, 28), moneyness="ATM")
    print(f"\nATM for 2026-08-28 expiry: {len(chain_expiry)} legs")


# ──────────────────────────────────────────────────────────────────────────────
# 5. Option chain — error handling
# ──────────────────────────────────────────────────────────────────────────────

def demo_option_chain_error(tcs):
    """Equities don't support option chain — clear error."""
    from scalpr.brokers.errors import OptionChainNotSupported

    try:
        tcs.option_chain()
    except OptionChainNotSupported as e:
        print("\n✓ TCS.option_chain() correctly rejected:")
        print(f"  {e}")


# ──────────────────────────────────────────────────────────────────────────────
# 6. Live feed — subscribe / unsubscribe
# ──────────────────────────────────────────────────────────────────────────────

def demo_live_feed(gw):
    """Subscribe to live market data via WebSocket."""
    from scalpr.domain.instrument import MarketFeed

    def handle_tick(event):
        print(f"  tick: {event}")

    # Subscribe multiple instruments
    gw.subscribe_feed(
        MarketFeed.QUOTE,
        ["TCS:NSE", "RELIANCE:NSE", "NIFTY:NSE"],
        on_event=handle_tick,
    )
    print("Subscribed to QUOTE feed for TCS, RELIANCE, NIFTY")

    # Unsubscribe
    gw.unsubscribe(["RELIANCE:NSE"])
    print("Unsubscribed RELIANCE")

    # Clean shutdown
    gw.close()
    print("Gateway closed")


# ──────────────────────────────────────────────────────────────────────────────
# 7. Per-instrument subscribe
# ──────────────────────────────────────────────────────────────────────────────

def demo_instrument_subscribe(nifty):
    """Subscribe to a single instrument via its handle."""
    from scalpr.domain.instrument import MarketFeed

    def on_tick(event):
        print(f"  NIFTY tick: {event}")

    nifty.subscribe(MarketFeed.FULL, on_tick)
    print("Subscribed to NIFTY FULL feed via handle")


# ──────────────────────────────────────────────────────────────────────────────
# 8. Gateway-level option chain (legacy path)
# ──────────────────────────────────────────────────────────────────────────────

def demo_gateway_option_chain(gw):
    """Gateway.option_chain() — works but prefer handle.option_chain()."""
    chain = gw.option_chain("NIFTY", "NSE")
    print(f"Gateway option_chain: {len(chain)} legs")


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("TradeXV2 Gateway API — Examples")
    print("=" * 60)

    # 1. Create gateway
    print("\n── 1. Gateway Construction ──")
    gw = demo_gateway_construction()

    # 2. Resolve instruments
    print("\n── 2. Instrument Resolution ──")
    tcs, nifty = demo_instrument_resolution(gw)

    # 3. Market data
    print("\n── 3. Market Data ──")
    demo_market_data(tcs)

    # 4. Option chain with filtering
    print("\n── 4. Option Chain (filtered) ──")
    demo_option_chain(nifty)

    # 5. Error handling
    print("\n── 5. Option Chain Error ──")
    demo_option_chain_error(tcs)

    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    main()

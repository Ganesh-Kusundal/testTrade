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
    from scalpr.gateway import Gateway

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
    print(f"1. Qualified string:  {tcs.resolved.trading_symbol} @ {tcs.resolved.exchange}")

    # Convention 2: Separate args (enum or string)
    reliance = gw.instrument("RELIANCE", Exchange.NSE)
    print(f"2. Separate args:     {reliance.resolved.trading_symbol} @ {reliance.resolved.exchange}")

    # Convention 3: SimpleInstrumentId domain object
    sid = SimpleInstrumentId(symbol="INFY", exchange=Exchange.NSE)
    infy = gw.instrument(sid)
    print(f"3. Domain object:     {infy.resolved.trading_symbol} @ {infy.resolved.exchange}")

    # Index with segment
    nifty = gw.instrument("NIFTY", Exchange.NSE, Segment.INDEX)
    print(f"4. Index:             {nifty.resolved.trading_symbol} @ {nifty.resolved.exchange}")

    # MCX commodity
    gold = gw.instrument("GOLD", "MCX")
    print(f"5. Commodity:         {gold.resolved.trading_symbol} @ {gold.resolved.exchange}")

    return tcs, nifty


# ──────────────────────────────────────────────────────────────────────────────
# 3. Market data — ltp, quote, ohlc, depth, historical
# ──────────────────────────────────────────────────────────────────────────────

def demo_market_data(tcs):
    """InstrumentHandle market data methods."""

    # Full quote (domain object)
    q = tcs.quote()
    print(f"Quote: open={q.open} high={q.high} low={q.low} close={q.close} vol={q.volume}")

    # OHLC snapshot (domain object)
    ohlc = tcs.ohlc()
    print(f"OHLC: O={ohlc.open} H={ohlc.high} L={ohlc.low} C={ohlc.close}")

    # Market depth (domain object)
    depth = tcs.depth()
    print(f"Depth: {len(depth.bid_levels)} bids, {len(depth.ask_levels)} asks")

    # Historical candles (domain objects)
    candles = tcs.historical(interval="1D", start="2025-01-01", end="2025-06-30")
    print(f"Historical: {len(candles)} candles")


# ──────────────────────────────────────────────────────────────────────────────
# 4. Option chain — with moneyness filtering
# ──────────────────────────────────────────────────────────────────────────────

def demo_option_chain(nifty):
    """Option chain with ATM/ITM/OTM filtering."""

    # Raw chain (all strikes, both CE and PE)
    all_legs = nifty.option_chain()
    print(f"\nRaw chain: {len(all_legs)} legs")


# ──────────────────────────────────────────────────────────────────────────────
# 5. Option chain — error handling
# ──────────────────────────────────────────────────────────────────────────────

def demo_option_chain_error(tcs):
    """Equities don't support option chain — clear error."""
    from scalpr.gateway.instrument import OptionChainNotSupported

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
    sub = gw.subscribe_feed(
        MarketFeed.QUOTE,
        ["TCS:NSE", "RELIANCE:NSE", "NIFTY:NSE"],
        on_event=handle_tick,
    )
    print(f"Subscribed to QUOTE feed: {sub.id}")

    # Unsubscribe
    gw.unsubscribe(sub)
    print("Unsubscribed")

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

    sub = nifty.subscribe(MarketFeed.FULL, on_tick)
    print(f"Subscribed to NIFTY FULL feed via handle: {sub.id}")


# ──────────────────────────────────────────────────────────────────────────────
# 8. Order management
# ──────────────────────────────────────────────────────────────────────────────

def demo_order_management(gw):
    """Place, modify, and cancel orders."""
    from scalpr.domain.order import OrderRequest, Side, ProductType, OrderType, Validity
    from decimal import Decimal

    # Place order
    req = OrderRequest(
        instrument="TCS:NSE",
        side=Side.BUY,
        quantity=10,
        order_type=OrderType.LIMIT,
        product=ProductType.INTRADAY,
        validity=Validity.DAY,
        price=Decimal("2500.00"),
    )
    order = gw.orders.place(req)
    print(f"Placed order: {order.order_id}")

    # Cancel order
    gw.orders.cancel(order.order_id)
    print(f"Cancelled order: {order.order_id}")


# ──────────────────────────────────────────────────────────────────────────────
# 9. Portfolio and account
# ──────────────────────────────────────────────────────────────────────────────

def demo_portfolio_and_account(gw):
    """Portfolio and account queries."""
    holdings = gw.portfolio.holdings()
    print(f"Holdings: {len(holdings)}")

    positions = gw.portfolio.positions()
    print(f"Positions: {len(positions)}")

    funds = gw.account.fund_limits()
    print(f"Available margin: {funds.available_margin}")


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

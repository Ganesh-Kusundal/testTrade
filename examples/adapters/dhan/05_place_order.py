#!/usr/bin/env python3
"""DhanClient example: dry-run order payload construction.

This script DOES NOT place a real order. It demonstrates how an Order
object is mapped to the Dhan API request payload and shows available
product types and order types.

Usage:
    export DHAN_CLIENT_ID=...
    export DHAN_ACCESS_TOKEN=...
    python3 examples/adapters/dhan/05_place_order.py
"""

from __future__ import annotations

import json
import os
import sys
from decimal import Decimal

from dotenv import load_dotenv

from scalpr.adapters.dhan._mapper import order_to_dhan_request_v2
from scalpr.domain.instrument import Exchange
from scalpr.domain.order import Order, OrderSide, OrderType


def main() -> None:
    load_dotenv()

    client_id = os.getenv("DHAN_CLIENT_ID")
    if not client_id:
        print("ERROR: DHAN_CLIENT_ID must be set.")
        sys.exit(1)

    print("=" * 60)
    print("  DhanClient – Order Payload (Dry Run, NO actual order)")
    print("=" * 60)

    # ── Available product types ────────────────────────────────────
    print("\n[1/4] Product types supported by Dhan:")
    products = {
        "INTRADAY": "MIS — intraday, squared off by EOD",
        "DELIVERY": "CNC — delivery / holdings",
        "MARGIN": "NRML — F&O / commodity",
    }
    for code, desc in products.items():
        print(f"  {code:12s}  {desc}")

    # ── Available order types ──────────────────────────────────────
    print("\n[2/4] Order types supported by Dhan:")
    for ot in OrderType:
        print(f"  {ot.value}")

    # ── Build a sample Order ───────────────────────────────────────
    print("\n[3/4] Constructing a sample Order (LIMIT BUY)")
    order = Order(
        order_id="dry-run-001",
        symbol="RELIANCE",
        exchange=Exchange.NSE,
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=10,
        price=Decimal("2500.00"),
        trigger_price=Decimal("0"),
        product_type="INTRADAY",
        validity="DAY",
    )
    print(f"  order_id:      {order.order_id}")
    print(f"  symbol:        {order.symbol}")
    print(f"  exchange:      {order.exchange.value}")
    print(f"  side:          {order.side.value}")
    print(f"  order_type:    {order.order_type.value}")
    print(f"  quantity:      {order.quantity}")
    print(f"  price:         {order.price}")
    print(f"  product_type:  {order.product_type}")
    print(f"  validity:      {order.validity}")

    # ── Map to Dhan request payload ────────────────────────────────
    print("\n[4/4] Mapped Dhan API request payload (order_to_dhan_request_v2):")
    try:
        payload = order_to_dhan_request_v2(
            order=order,
            security_id="123456",
            segment="NSE_EQ",
            client_id=client_id,
            product_type="INTRADAY",
            after_market=False,
            disclosed_qty=0,
        )
        print(json.dumps(payload, indent=2))
        print()
        print("  This payload would be POSTed to /orders.")
        print("  No request was sent — this is a dry run.")

        # Show a MARKET order variant too
        print("\n  ── Variant: MARKET SELL ──")
        market_order = Order(
            order_id="dry-run-002",
            symbol="TCS",
            exchange=Exchange.NSE,
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=5,
            price=Decimal("0"),
            product_type="DELIVERY",
            validity="DAY",
        )
        mkt_payload = order_to_dhan_request_v2(
            order=market_order,
            security_id="789012",
            segment="NSE_EQ",
            client_id=client_id,
            product_type="DELIVERY",
        )
        print(json.dumps(mkt_payload, indent=2))
    except Exception as e:
        print(f"  ERROR: {e}")

    print("\nDone. No orders were placed.")


if __name__ == "__main__":
    main()

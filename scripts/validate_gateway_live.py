#!/usr/bin/env python
"""Live Dhan data validation for Gateway API.

Validates:
1. All Gateway methods work with live data
2. Return types match contracts
3. Intelligent defaults work correctly
4. Real data is returned (not mocks)

Usage:
    python scripts/validate_gateway_live.py
"""

import sys
from datetime import datetime
from decimal import Decimal

from scalpr.brokers import Gateway


def print_header(title: str) -> None:
    """Print formatted section header."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")

def print_result(test_name: str, success: bool, details: str = "") -> None:
    """Print test result."""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} | {test_name}")
    if details:
        print(f"     {details}")

def validate_connection(g: Gateway) -> bool:
    """Validate gateway connection."""
    print_header("PHASE 1: Connection Validation")

    try:
        connected = g.is_connected()
        print_result("Gateway connected", connected, f"Broker: {g.broker_name}")
        return connected
    except Exception as e:
        print_result("Gateway connected", False, str(e))
        return False

def validate_ltp(g: Gateway) -> bool:
    """Validate LTP with intelligent defaults."""
    print_header("PHASE 2: LTP Validation")

    symbols = ["TCS", "RELIANCE", "INFY"]
    all_passed = True

    for symbol in symbols:
        try:
            ltp = g.ltp(symbol)  # Should use default exchange="NSE"
            success = isinstance(ltp, Decimal) and ltp > 0
            print_result(
                f"LTP({symbol})",
                success,
                f"₹{ltp}" if success else f"Invalid: {ltp}"
            )
            if not success:
                all_passed = False
        except Exception as e:
            print_result(f"LTP({symbol})", False, str(e))
            all_passed = False

    return all_passed

def validate_quote(g: Gateway) -> bool:
    """Validate quote returns canonical Quote model."""
    print_header("PHASE 3: Quote Validation")

    try:
        quote = g.quote("TCS")

        # Verify it's a Quote dataclass
        from scalpr.domain.contracts import Quote
        is_quote = isinstance(quote, Quote)

        # Verify fields
        has_fields = all([
            hasattr(quote, 'ltp'),
            hasattr(quote, 'open'),
            hasattr(quote, 'high'),
            hasattr(quote, 'low'),
            hasattr(quote, 'close'),
            hasattr(quote, 'volume'),
        ])

        success = is_quote and has_fields and quote.ltp > 0

        print_result(
            "Quote(TCS)",
            success,
            f"LTP: ₹{quote.ltp}, Volume: {quote.volume}"
        )

        if not success:
            print(f"     Quote type: {type(quote)}")
            print(f"     Has all fields: {has_fields}")

        return success
    except Exception as e:
        print_result("Quote(TCS)", False, str(e))
        return False

def validate_history(g: Gateway) -> bool:
    """Validate history returns canonical DataFrame schema."""
    print_header("PHASE 4: Historical Data Validation")

    try:
        # Test with minimal arguments (intelligent defaults)
        df = g.history("TCS")  # Should use exchange="NSE", timeframe="1m", lookback_days=90

        # Verify DataFrame
        import pandas as pd
        is_dataframe = isinstance(df, pd.DataFrame)

        # Verify required columns
        required_columns = [
            "timestamp", "open", "high", "low", "close",
            "volume", "oi", "symbol", "exchange", "timeframe"
        ]
        has_columns = all(col in df.columns for col in required_columns)

        # Verify data
        has_data = len(df) > 0

        success = is_dataframe and has_columns and has_data

        print_result(
            "History(TCS)",
            success,
            f"Rows: {len(df)}, Columns: {len(df.columns)}"
        )

        if success:
            print(f"     Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
            print(f"     Symbols: {df['symbol'].unique()}")

        if not has_columns:
            missing = [col for col in required_columns if col not in df.columns]
            print(f"     Missing columns: {missing}")
            print(f"     Actual columns: {list(df.columns)}")

        return success
    except Exception as e:
        print_result("History(TCS)", False, f"{type(e).__name__}: {e}")
        return False

def validate_positions(g: Gateway) -> bool:
    """Validate positions."""
    print_header("PHASE 5: Positions Validation")

    try:
        positions = g.positions()
        is_list = isinstance(positions, list)

        print_result(
            "Positions",
            is_list,
            f"Count: {len(positions)}"
        )

        if len(positions) > 0:
            pos = positions[0]
            print(f"     Sample: {pos.symbol} qty={pos.quantity}")

        return is_list
    except Exception as e:
        print_result("Positions", False, str(e))
        return False

def validate_holdings(g: Gateway) -> bool:
    """Validate holdings returns canonical Holding models."""
    print_header("PHASE 6: Holdings Validation")

    try:
        holdings = g.holdings()
        is_list = isinstance(holdings, list)

        from scalpr.domain.contracts import Holding
        all_holdings = all(isinstance(h, Holding) for h in holdings)

        success = is_list and all_holdings

        print_result(
            "Holdings",
            success,
            f"Count: {len(holdings)}"
        )

        if len(holdings) > 0:
            h = holdings[0]
            print(f"     Sample: {h.symbol} qty={h.quantity} pnl={h.pnl}")

        return success
    except Exception as e:
        print_result("Holdings", False, str(e))
        return False

def validate_funds(g: Gateway) -> bool:
    """Validate funds returns canonical Funds model."""
    print_header("PHASE 7: Funds Validation")

    try:
        funds = g.funds()

        from scalpr.domain.contracts import Funds
        is_funds = isinstance(funds, Funds)

        has_balance = funds.total_balance > 0

        success = is_funds and has_balance

        print_result(
            "Funds",
            success,
            f"Balance: ₹{funds.total_balance}, Available: ₹{funds.available_margin}"
        )

        return success
    except Exception as e:
        print_result("Funds", False, str(e))
        return False

def validate_orders(g: Gateway) -> bool:
    """Validate orders."""
    print_header("PHASE 8: Orders Validation")

    try:
        orders = g.orders()
        is_list = isinstance(orders, list)

        print_result(
            "Orders",
            is_list,
            f"Count: {len(orders)}"
        )

        return is_list
    except Exception as e:
        print_result("Orders", False, str(e))
        return False

def validate_trades(g: Gateway) -> bool:
    """Validate trades returns canonical Trade models."""
    print_header("PHASE 9: Trades Validation")

    try:
        trades = g.trades()
        is_list = isinstance(trades, list)

        from scalpr.domain.contracts import Trade
        all_trades = all(isinstance(t, Trade) for t in trades)

        success = is_list and all_trades

        print_result(
            "Trades",
            success,
            f"Count: {len(trades)}"
        )

        if len(trades) > 0:
            t = trades[0]
            print(f"     Sample: {t.symbol} qty={t.quantity} price={t.price}")

        return success
    except Exception as e:
        print_result("Trades", False, str(e))
        return False

def main() -> int:
    """Run all validation tests."""
    print("\n" + "="*70)
    print("  GATEWAY LIVE DATA VALIDATION")
    print(f"  Timestamp: {datetime.now().isoformat()}")
    print("="*70)

    # Initialize Gateway
    print_header("INITIALIZATION")
    try:
        g = Gateway(broker="dhan")
        print_result("Gateway created", True, f"Broker: {g.broker_name}")
    except Exception as e:
        print_result("Gateway created", False, str(e))
        print("\n❌ Gateway initialization failed. Aborting validation.")
        return 1

    # Run validations
    results = {
        "Connection": validate_connection(g),
        "LTP": validate_ltp(g),
        "Quote": validate_quote(g),
        "History": validate_history(g),
        "Positions": validate_positions(g),
        "Holdings": validate_holdings(g),
        "Funds": validate_funds(g),
        "Orders": validate_orders(g),
        "Trades": validate_trades(g),
    }

    # Summary
    print_header("VALIDATION SUMMARY")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} | {test_name}")

    print(f"\n{'='*70}")
    print(f"  Total: {passed}/{total} tests passed")
    print(f"{'='*70}")

    # Cleanup
    try:
        g.disconnect()
        print("\n✅ Gateway disconnected successfully")
    except Exception as e:
        print(f"\n⚠️  Disconnect warning: {e}")

    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())

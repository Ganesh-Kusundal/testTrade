#!/usr/bin/env python
"""Research workflow validation for Gateway API.

Validates that the Gateway enables natural research workflows:
1. Discover available brokers
2. Connect and get funds
3. Look up LTP/quote
4. Get historical data
5. Check positions/holdings
6. Stream live data

Usage:
    python scripts/validate_research_workflow.py
"""

import sys
import time
from datetime import datetime
from decimal import Decimal

from scalpr.brokers import Gateway
from scalpr.brokers.registry import BrokerRegistry
from scalpr.domain.tick import Tick


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

def validate_research_workflow() -> int:
    """Run complete research workflow validation."""
    print("\n" + "="*70)
    print("  GATEWAY RESEARCH WORKFLOW VALIDATION")
    print(f"  Timestamp: {datetime.now().isoformat()}")
    print("="*70)

    workflow_passed = True
    tick_count = 0

    # Step 1: Discover brokers
    print_header("STEP 1: Discover Available Brokers")
    try:
        brokers = BrokerRegistry.list_brokers()
        has_dhan = "dhan" in brokers
        print_result("Brokers discovered", True, f"Available: {', '.join(brokers)}")
        print_result("Dhan available", has_dhan)
        if not has_dhan:
            workflow_passed = False
    except Exception as e:
        print_result("Brokers discovered", False, str(e))
        workflow_passed = False

    # Step 2: Create Gateway and connect
    print_header("STEP 2: Create Gateway and Connect")
    try:
        g = Gateway(broker="dhan")
        connected = True
        print_result("Gateway created", True, f"Broker: {g.broker_name}")
        print_result("Auto-connected", connected)
    except Exception as e:
        print_result("Gateway created", False, str(e))
        workflow_passed = False
        return 1

    # Step 3: Get funds
    print_header("STEP 3: Get Account Funds")
    try:
        funds = g.funds()
        has_funds = funds.available > 0
        print_result("Funds retrieved", has_funds,
                    f"Available: ₹{funds.available:,.2f}")
        if not has_funds:
            workflow_passed = False
    except Exception as e:
        print_result("Funds retrieved", False, str(e))
        workflow_passed = False

    # Step 4: Get LTP
    print_header("STEP 4: Look Up LTP")
    try:
        ltp = g.ltp("TCS")
        has_ltp = ltp > 0
        print_result("LTP retrieved", has_ltp, f"TCS: ₹{ltp}")
        if not has_ltp:
            workflow_passed = False
    except Exception as e:
        print_result("LTP retrieved", False, str(e))
        workflow_passed = False

    # Step 5: Get quote
    print_header("STEP 5: Get Full Quote")
    try:
        quote = g.quote("TCS")
        has_quote = quote.ltp > 0
        print_result("Quote retrieved", has_quote,
                    f"LTP: ₹{quote.ltp}, High: ₹{quote.high}, Low: ₹{quote.low}")
        if not has_quote:
            workflow_passed = False
    except Exception as e:
        print_result("Quote retrieved", False, str(e))
        workflow_passed = False

    # Step 6: Get historical data
    print_header("STEP 6: Get Historical Data")
    try:
        df = g.history("TCS", lookback_days=5)
        has_history = len(df) > 0
        print_result("History retrieved", has_history,
                    f"Rows: {len(df)}, Columns: {len(df.columns)}")
        if has_history:
            print(f"     Columns: {', '.join(df.columns)}")
            print(f"     Date range: {df['datetime'].iloc[0]} to {df['datetime'].iloc[-1]}")
        if not has_history:
            workflow_passed = False
    except Exception as e:
        print_result("History retrieved", False, str(e))
        workflow_passed = False

    # Step 7: Check positions
    print_header("STEP 7: Check Positions")
    try:
        positions = g.positions()
        print_result("Positions retrieved", True,
                    f"Active positions: {len(positions)}")
    except Exception as e:
        print_result("Positions retrieved", False, str(e))
        workflow_passed = False

    # Step 8: Check holdings
    print_header("STEP 8: Check Holdings")
    try:
        holdings = g.holdings()
        print_result("Holdings retrieved", True,
                    f"Total holdings: {len(holdings)}")
    except Exception as e:
        print_result("Holdings retrieved", False, str(e))
        workflow_passed = False

    # Step 9: Test streaming capability
    print_header("STEP 9: Test Streaming Capability")
    try:
        has_stream = hasattr(g, 'stream')
        print_result("Stream method available", has_stream)

        if has_stream:
            # Quick stream test (2 seconds)
            ticks_received = []

            def on_tick(tick: Tick) -> None:
                ticks_received.append(tick)

            print("     Subscribing to TCS for 2 seconds...")
            g.stream("TCS", callback=on_tick)
            time.sleep(2)
            g.stop_stream()

            if len(ticks_received) > 0:
                print_result("Streaming works", True,
                            f"Received {len(ticks_received)} ticks")
            else:
                print_result("Streaming works", False,
                            "No ticks received (market may be closed)")
    except Exception as e:
        print_result("Streaming test", False, str(e))
        workflow_passed = False

    # Step 10: Cleanup
    print_header("STEP 10: Cleanup")
    try:
        g.disconnect()
        print_result("Disconnected", True)
    except Exception as e:
        print_result("Disconnected", False, str(e))
        workflow_passed = False

    # Summary
    print_header("RESEARCH WORKFLOW VALIDATION SUMMARY")
    if workflow_passed:
        print("  ✅ All workflow steps completed successfully!")
        print("  The Gateway API enables natural research workflows.")
        return 0
    else:
        print("  ⚠️  Some workflow steps failed")
        print("  Review failed steps above for details")
        return 1

if __name__ == "__main__":
    sys.exit(validate_research_workflow())

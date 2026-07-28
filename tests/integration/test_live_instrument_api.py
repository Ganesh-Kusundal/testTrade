"""Live E2E test for Gateway.instrument() API against real Dhan market.

Run: python tests/integration/test_live_instrument_api.py
Requires: Valid DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN in .env
"""
import sys
import os
import time
from pathlib import Path
from decimal import Decimal

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
load_dotenv()

from scalpr.brokers import Gateway
from scalpr.domain.instrument import SimpleInstrumentId, Exchange


def test_instrument_resolution():
    """Test 1: Gateway.instrument() resolves TCS:NSE correctly."""
    print("\n=== Test 1: Instrument Resolution ===")
    gw = Gateway()
    
    try:
        tcs = gw.instrument("TCS:NSE")
        print(f"✓ Resolved: {tcs.symbol} on {tcs.exchange}")
        print(f"  Security ID: {tcs.resolved.security_id}")
        print(f"  Wire segment: {tcs.resolved.wire_segment}")
        print(f"  Lot size: {tcs.resolved.lot_size}")
        assert tcs.symbol == "TCS"
        assert tcs.exchange == "NSE"
        assert tcs.resolved.security_id is not None
        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False


def test_ltp():
    """Test 2: InstrumentHandle.ltp() returns live price."""
    print("\n=== Test 2: LTP (Last Traded Price) ===")
    gw = Gateway()
    
    try:
        tcs = gw.instrument("TCS:NSE")
        ltp = tcs.ltp()
        print(f"✓ TCS LTP: ₹{ltp}")
        assert isinstance(ltp, Decimal)
        assert ltp > 0
        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False


def test_quote():
    """Test 3: InstrumentHandle.quote() returns full quote."""
    print("\n=== Test 3: Full Quote ===")
    gw = Gateway()
    
    try:
        tcs = gw.instrument("TCS:NSE")
        quote = tcs.quote()
        print(f"✓ TCS Quote:")
        print(f"  LTP: ₹{quote.get('ltp', 'N/A')}")
        print(f"  Open: ₹{quote.get('open', 'N/A')}")
        print(f"  High: ₹{quote.get('high', 'N/A')}")
        print(f"  Low: ₹{quote.get('low', 'N/A')}")
        print(f"  Volume: {quote.get('volume', 'N/A')}")
        assert isinstance(quote, dict)
        assert "ltp" in quote
        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_historical():
    """Test 4: InstrumentHandle.historical() returns OHLCV candles."""
    print("\n=== Test 4: Historical Data ===")
    gw = Gateway()
    
    try:
        tcs = gw.instrument("TCS:NSE")
        candles = tcs.historical(interval="1D")
        print(f"✓ TCS Historical: {len(candles)} candles")
        if candles:
            first = candles[0]
            print(f"  First candle: {first.get('timestamp', 'N/A')}")
            print(f"  O: ₹{first.get('open', 'N/A')}")
            print(f"  H: ₹{first.get('high', 'N/A')}")
            print(f"  L: ₹{first.get('low', 'N/A')}")
            print(f"  C: ₹{first.get('close', 'N/A')}")
            print(f"  Vol: {first.get('volume', 'N/A')}")
        assert isinstance(candles, list)
        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_multiple_instruments():
    """Test 5: Resolve multiple instruments."""
    print("\n=== Test 5: Multiple Instruments ===")
    gw = Gateway()
    
    instruments = ["TCS:NSE", "RELIANCE:NSE", "INFY:NSE"]
    results = []
    
    for symbol in instruments:
        try:
            time.sleep(1.1)  # respect Dhan 1 req/sec market-feed rate limit
            handle = gw.instrument(symbol)
            ltp = handle.ltp()
            results.append((symbol, ltp))
            print(f"✓ {symbol}: ₹{ltp}")
        except Exception as e:
            print(f"✗ {symbol}: {e}")
    
    return len(results) == len(instruments)


def test_index_instrument():
    """Test 6: Resolve index instrument (NIFTY)."""
    print("\n=== Test 6: Index Instrument ===")
    gw = Gateway()
    
    try:
        nifty = gw.instrument("NIFTY:NSE")
        print(f"✓ Resolved: {nifty.symbol} on {nifty.exchange}")
        print(f"  Security ID: {nifty.resolved.security_id}")
        print(f"  Wire segment: {nifty.resolved.wire_segment}")
        ltp = nifty.ltp()
        print(f"  LTP: ₹{ltp}")
        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all live E2E tests."""
    print("=" * 60)
    print("LIVE E2E TEST: Gateway.instrument() API")
    print("=" * 60)
    
    tests = [
        test_instrument_resolution,
        test_ltp,
        test_quote,
        test_historical,
        test_multiple_instruments,
        test_index_instrument,
    ]
    
    results = []
    for test in tests:
        try:
            time.sleep(1.1)  # pace tests to respect Dhan rate limits
            result = test()
            results.append(result)
        except Exception as e:
            print(f"✗ Test crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    print("\n" + "=" * 60)
    print(f"RESULTS: {sum(results)}/{len(results)} tests passed")
    print("=" * 60)
    
    if all(results):
        print("\n✓ ALL TESTS PASSED — Live market API is working!")
        return 0
    else:
        print("\n✗ SOME TESTS FAILED — Check output above")
        return 1


if __name__ == "__main__":
    sys.exit(main())

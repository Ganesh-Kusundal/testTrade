"""Test live WebSocket with NIFTY 50 (should be very liquid)."""

import os
import time
import sys
from dotenv import load_dotenv
from datetime import datetime

load_dotenv(".env")

from scalpr.brokers.dhan.loader import InstrumentLoader
from scalpr.brokers.dhan.resolution import SymbolResolver
from scalpr.brokers.dhan.ws_client import DhanWebSocketClient
from scalpr.domain.tick import Tick


def on_tick_received(tick: Tick) -> None:
    """Callback for received ticks."""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{timestamp}] TICK: {tick.symbol} | LTP: {tick.ltp} | Bid: {tick.bid} | Ask: {tick.ask} | Vol: {tick.cumulative_volume}")


def main():
    """Test live WebSocket subscription for NIFTY 50."""
    client_id = os.getenv("DHAN_CLIENT_ID")
    access_token = os.getenv("DHAN_ACCESS_TOKEN")
    
    if not client_id or not access_token:
        print("ERROR: DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN must be set in .env")
        sys.exit(1)
    
    print("=" * 80)
    print("Testing Live WebSocket Subscription - NIFTY 50 (NSE)")
    print("=" * 80)
    print(f"Client ID: {client_id}")
    print(f"Token: {access_token[:20]}...")
    print()
    
    # Canonical symbol only — the broker resolver owns the security_id mapping
    resolver = SymbolResolver()
    resolver.load_from_rows(InstrumentLoader.load_cached())
    symbols_to_test = [
        ("NIFTY", "NSE", "NIFTY 50 Index"),
    ]
    
    for symbol, exchange, description in symbols_to_test:
        print(f"\n{'=' * 80}")
        print(f"Testing: {description}")
        print(f"{'=' * 80}")
        
        client = DhanWebSocketClient(
            access_token=access_token,
            client_id=client_id,
            mode="quote",
            resolver=resolver,
        )
        
        tick_count = [0]
        client.on_tick(on_tick_received)
        
        original_callback = client._tick_callback
        def counting_callback(tick: Tick) -> None:
            tick_count[0] += 1
            if original_callback:
                original_callback(tick)
        client.on_tick(counting_callback)
        
        try:
            import asyncio
            
            async def test_one():
                connected = await client.connect()
                if not connected:
                    print("✗ Connection failed")
                    return False
                
                print(f"✓ Connected")
                
                subscribed = await client.subscribe([(symbol, exchange)])
                if not subscribed:
                    print(f"✗ Subscription failed")
                    return False
                
                print(f"✓ Subscribed to {symbol} ({exchange})")
                print("Waiting 30 seconds for ticks...")
                
                start_time = time.time()
                timeout = 30
                
                while time.time() - start_time < timeout:
                    await asyncio.sleep(1)
                    elapsed = int(time.time() - start_time)
                    if elapsed % 10 == 0 and elapsed > 0:
                        print(f"  [{elapsed}s] Ticks received: {tick_count[0]}")
                
                print(f"\nResult: {tick_count[0]} ticks in 30 seconds")
                
                if tick_count[0] > 0:
                    print("✓✓✓ WORKING! ✓✓✓")
                    return True
                else:
                    print("✗ No ticks received")
                    return False
            
            result = asyncio.run(test_one())
            
            if result:
                return True
            
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()
        finally:
            try:
                import asyncio
                asyncio.run(client.disconnect())
            except:
                pass
    
    return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

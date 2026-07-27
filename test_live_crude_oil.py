"""Test live WebSocket subscription for Crude Oil spot price."""

import os
import time
import sys
from dotenv import load_dotenv
from datetime import datetime

load_dotenv(".env")

from scalpr.brokers.dhan.ws_client import DhanWebSocketClient
from scalpr.domain.tick import Tick


def on_tick_received(tick: Tick) -> None:
    """Callback for received ticks."""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{timestamp}] TICK: {tick.symbol} | LTP: {tick.ltp} | Bid: {tick.bid} | Ask: {tick.ask} | Vol: {tick.cumulative_volume}")


def main():
    """Test live WebSocket subscription for Crude Oil."""
    client_id = os.getenv("DHAN_CLIENT_ID")
    access_token = os.getenv("DHAN_ACCESS_TOKEN")
    
    if not client_id or not access_token:
        print("ERROR: DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN must be set in .env")
        sys.exit(1)
    
    print("=" * 80)
    print("Testing Live WebSocket Subscription - Crude Oil (MCX)")
    print("=" * 80)
    print(f"Client ID: {client_id}")
    print(f"Token: {access_token[:20]}...")
    print()
    
    # Crude Oil on MCX - security_id 119773
    # Using direct security_id since we may not have resolver configured
    crude_oil_symbol = "119773"  # MCX Crude Oil security_id
    exchange = "MCX"
    
    print(f"Subscribing to: {crude_oil_symbol} ({exchange})")
    print("Waiting for ticks (60 seconds timeout)...")
    print()
    
    # Create WebSocket client
    client = DhanWebSocketClient(
        access_token=access_token,
        client_id=client_id,
        mode="quote",  # Get quote data (LTP, bid, ask, volume)
    )
    
    # Register tick callback
    client.on_tick(on_tick_received)
    
    tick_count = [0]
    original_callback = client._tick_callback
    
    def counting_callback(tick: Tick) -> None:
        tick_count[0] += 1
        if original_callback:
            original_callback(tick)
    
    client.on_tick(counting_callback)
    
    try:
        # Connect to WebSocket
        print("Connecting to Dhan WebSocket...")
        import asyncio
        
        async def test_subscription():
            connected = await client.connect()
            if not connected:
                print("ERROR: Failed to connect to WebSocket")
                return False
            
            print("✓ Connected to Dhan WebSocket")
            print()
            
            # Subscribe to Crude Oil
            print("Subscribing to Crude Oil...")
            subscribed = await client.subscribe([(crude_oil_symbol, exchange)])
            
            if not subscribed:
                print("ERROR: Failed to subscribe")
                return False
            
            print(f"✓ Subscribed to {crude_oil_symbol} ({exchange})")
            print()
            print("Waiting for ticks...")
            print("-" * 80)
            
            # Wait for ticks (60 seconds)
            start_time = time.time()
            timeout = 60
            
            while time.time() - start_time < timeout:
                await asyncio.sleep(1)
                
                # Show progress every 10 seconds
                elapsed = int(time.time() - start_time)
                if elapsed % 10 == 0 and elapsed > 0:
                    print(f"  [{elapsed}s] Waiting... (received {tick_count[0]} ticks so far)")
            
            print("-" * 80)
            print()
            
            # Summary
            print("=" * 80)
            print("SUBSCRIPTION TEST SUMMARY")
            print("=" * 80)
            print(f"Symbol: {crude_oil_symbol} ({exchange})")
            print(f"Duration: {timeout} seconds")
            print(f"Ticks Received: {tick_count[0]}")
            
            if tick_count[0] > 0:
                print("Status: ✓ WORKING - Receiving live ticks")
                return True
            else:
                print("Status: ✗ NO TICKS RECEIVED")
                print()
                print("Possible reasons:")
                print("  1. Market is closed (MCX hours: 9:00 AM - 11:30 PM IST)")
                print("  2. Token expired (check DHAN_ACCESS_TOKEN in .env)")
                print("  3. Security ID incorrect (Crude Oil = 119773)")
                print("  4. No market activity for this instrument")
                return False
        
        # Run async test
        result = asyncio.run(test_subscription())
        
        return result
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Cleanup
        try:
            import asyncio
            asyncio.run(client.disconnect())
            print("\nDisconnected from WebSocket")
        except:
            pass


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

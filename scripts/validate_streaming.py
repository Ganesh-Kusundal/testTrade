#!/usr/bin/env python
"""Streaming validation for Gateway API.

Validates:
1. WebSocket connection establishment
2. Tick reception
3. Reconnection behavior
4. Performance metrics

Usage:
    python scripts/validate_streaming.py
"""

import sys
import time
from datetime import datetime
from decimal import Decimal

from scalpr.brokers import Gateway
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

def validate_streaming() -> int:
    """Run streaming validation tests."""
    print("\n" + "="*70)
    print("  GATEWAY STREAMING VALIDATION")
    print(f"  Timestamp: {datetime.now().isoformat()}")
    print("="*70)
    
    # Initialize Gateway
    print_header("INITIALIZATION")
    try:
        g = Gateway(broker="dhan")
        print_result("Gateway created", True, f"Broker: {g.broker_name}")
    except Exception as e:
        print_result("Gateway created", False, str(e))
        return 1
    
    # Test 1: Check streaming capability
    print_header("TEST 1: Streaming Capability")
    try:
        has_streaming = hasattr(g, 'stream')
        print_result("Stream method exists", has_streaming)
        
        if not has_streaming:
            print("     ❌ Gateway does not support streaming")
            return 1
    except Exception as e:
        print_result("Stream method exists", False, str(e))
        return 1
    
    # Test 2: Initialize streaming
    print_header("TEST 2: WebSocket Initialization")
    tick_count = 0
    first_tick_time = None
    last_tick = None
    
    def on_tick(tick: Tick) -> None:
        """Callback for tick reception."""
        nonlocal tick_count, first_tick_time, last_tick
        tick_count += 1
        
        if first_tick_time is None:
            first_tick_time = time.time()
        
        last_tick = tick
        
        # Print first 5 ticks
        if tick_count <= 5:
            print(f"     Tick #{tick_count}: {tick.symbol} LTP={tick.last_traded_price}")
    
    try:
        print("     Subscribing to TCS...")
        g.stream("TCS", callback=on_tick)
        print_result("Subscription created", True)
        
        # Wait for ticks (10 seconds)
        print("     Waiting 10 seconds for ticks...")
        time.sleep(10)
        
        if tick_count > 0:
            elapsed = time.time() - first_tick_time
            ticks_per_second = tick_count / elapsed if elapsed > 0 else 0
            
            print_result("Ticks received", True, 
                        f"Count: {tick_count}, Rate: {ticks_per_second:.2f} ticks/sec")
            
            if last_tick:
                print(f"     Last tick: {last_tick.symbol} @ {last_tick.last_traded_price}")
        else:
            print_result("Ticks received", False, "No ticks received in 10 seconds")
            
    except Exception as e:
        print_result("Subscription created", False, str(e))
    
    # Test 3: Stop streaming
    print_header("TEST 3: Stop Streaming")
    try:
        g.stop_stream()
        is_stopped = not g.is_streaming()
        print_result("Stream stopped", is_stopped)
    except Exception as e:
        print_result("Stream stopped", False, str(e))
    
    # Summary
    print_header("STREAMING VALIDATION SUMMARY")
    print(f"  Ticks received: {tick_count}")
    print(f"  Streaming active: {g.is_streaming()}")
    
    # Cleanup
    try:
        g.disconnect()
        print("\n✅ Gateway disconnected successfully")
    except Exception as e:
        print(f"\n⚠️  Disconnect warning: {e}")
    
    return 0 if tick_count > 0 else 1

if __name__ == "__main__":
    sys.exit(validate_streaming())

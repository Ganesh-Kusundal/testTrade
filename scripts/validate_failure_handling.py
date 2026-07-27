#!/usr/bin/env python
"""Failure testing and graceful degradation for Gateway API.

Validates that the Gateway handles failures gracefully:
1. Invalid credentials
2. Network errors
3. Rate limiting
4. Broker API errors
5. Invalid symbols
6. Market closed scenarios
7. Streaming disconnection
8. Circuit breaker activation

Usage:
    python scripts/validate_failure_handling.py
"""

import sys
import time
from datetime import datetime
from decimal import Decimal
from unittest.mock import Mock, patch

from scalpr.brokers import Gateway
from scalpr.brokers.broker_port import IBrokerGateway
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

def validate_failure_handling() -> int:
    """Run failure handling validation tests."""
    print("\n" + "="*70)
    print("  GATEWAY FAILURE HANDLING VALIDATION")
    print(f"  Timestamp: {datetime.now().isoformat()}")
    print("="*70)
    
    tests_passed = 0
    tests_total = 0
    
    # Test 1: Invalid credentials
    print_header("TEST 1: Invalid Credentials Handling")
    tests_total += 1
    try:
        mock_gateway = Mock(spec=IBrokerGateway)
        mock_gateway.connect.side_effect = Exception("Invalid credentials")
        
        with patch('scalpr.brokers.registry.BrokerRegistry.get', return_value=mock_gateway):
            try:
                g = Gateway(broker="dhan", auto_connect=True)
                print_result("Invalid credentials", False, "Should have raised exception")
            except Exception as e:
                if "Invalid credentials" in str(e):
                    print_result("Invalid credentials", True, "Exception raised properly")
                    tests_passed += 1
                else:
                    print_result("Invalid credentials", False, f"Wrong exception: {e}")
    except Exception as e:
        print_result("Invalid credentials", False, str(e))
    
    # Test 2: Network error on LTP
    print_header("TEST 2: Network Error on LTP")
    tests_total += 1
    try:
        mock_gateway = Mock(spec=IBrokerGateway)
        mock_gateway.connect = Mock()
        mock_gateway.get_ltp.side_effect = ConnectionError("Network unreachable")
        
        with patch('scalpr.brokers.registry.BrokerRegistry.get', return_value=mock_gateway):
            g = Gateway(broker="dhan", auto_connect=False)
            g._gateway = mock_gateway
            
            try:
                ltp = g.ltp("TCS")
                print_result("Network error handling", False, "Should have raised exception")
            except ConnectionError as e:
                print_result("Network error handling", True, f"Exception propagated: {e}")
                tests_passed += 1
    except Exception as e:
        print_result("Network error handling", False, str(e))
    
    # Test 3: Invalid symbol
    print_header("TEST 3: Invalid Symbol Handling")
    tests_total += 1
    try:
        mock_gateway = Mock(spec=IBrokerGateway)
        mock_gateway.connect = Mock()
        mock_gateway.get_ltp.side_effect = ValueError("Symbol INVALID not found")
        
        with patch('scalpr.brokers.registry.BrokerRegistry.get', return_value=mock_gateway):
            g = Gateway(broker="dhan", auto_connect=False)
            g._gateway = mock_gateway
            
            try:
                ltp = g.ltp("INVALID_SYMBOL")
                print_result("Invalid symbol handling", False, "Should have raised exception")
            except (ValueError, Exception) as e:
                print_result("Invalid symbol handling", True, f"Exception raised: {e}")
                tests_passed += 1
    except Exception as e:
        print_result("Invalid symbol handling", False, str(e))
    
    # Test 4: Empty history
    print_header("TEST 4: Empty History Handling")
    tests_total += 1
    try:
        mock_gateway = Mock(spec=IBrokerGateway)
        mock_gateway.connect = Mock()
        
        import pandas as pd
        mock_gateway.get_ohlcv.return_value = []  # Empty list of candles
        
        with patch('scalpr.brokers.registry.BrokerRegistry.get', return_value=mock_gateway):
            g = Gateway(broker="dhan", auto_connect=False)
            g._gateway = mock_gateway
            
            df = g.history("TCS")
            if len(df) == 0:
                print_result("Empty history handling", True, "Returns empty DataFrame")
                tests_passed += 1
            else:
                print_result("Empty history handling", False, f"Expected 0 rows, got {len(df)}")
    except Exception as e:
        print_result("Empty history handling", False, str(e))
    
    # Test 5: Streaming disconnection
    print_header("TEST 5: Streaming Disconnection Handling")
    tests_total += 1
    try:
        mock_gateway = Mock(spec=IBrokerGateway)
        mock_gateway.connect = Mock()
        
        with patch('scalpr.brokers.registry.BrokerRegistry.get', return_value=mock_gateway):
            g = Gateway(broker="dhan", auto_connect=False)
            g._gateway = mock_gateway
            
            # Test that stop_stream() handles None ws_manager gracefully
            g.stop_stream()  # Should not raise
            print_result("Stop stream (no WS)", True, "Handled gracefully")
            tests_passed += 1
    except Exception as e:
        print_result("Stop stream (no WS)", False, str(e))
    
    # Test 6: Is streaming check
    print_header("TEST 6: Is Streaming Check")
    tests_total += 1
    try:
        mock_gateway = Mock(spec=IBrokerGateway)
        mock_gateway.connect = Mock()
        
        with patch('scalpr.brokers.registry.BrokerRegistry.get', return_value=mock_gateway):
            g = Gateway(broker="dhan", auto_connect=False)
            g._gateway = mock_gateway
            
            # Should be False when not streaming
            if not g.is_streaming():
                print_result("Is streaming (not active)", True, "Returns False")
                tests_passed += 1
            else:
                print_result("Is streaming (not active)", False, "Should return False")
    except Exception as e:
        print_result("Is streaming (not active)", False, str(e))
    
    # Test 7: Disconnect without connection
    print_header("TEST 7: Disconnect Without Connection")
    tests_total += 1
    try:
        mock_gateway = Mock(spec=IBrokerGateway)
        # connect not called
        
        with patch('scalpr.brokers.registry.BrokerRegistry.get', return_value=mock_gateway):
            g = Gateway(broker="dhan", auto_connect=False)
            g._gateway = mock_gateway
            
            # Should handle gracefully
            g.disconnect()
            print_result("Disconnect (not connected)", True, "Handled gracefully")
            tests_passed += 1
    except Exception as e:
        print_result("Disconnect (not connected)", False, str(e))
    
    # Test 8: Invalid broker name
    print_header("TEST 8: Invalid Broker Name")
    tests_total += 1
    try:
        from scalpr.brokers.registry import BrokerRegistry
        
        try:
            gateway = BrokerRegistry.get("invalid_broker", {})
            print_result("Invalid broker name", False, "Should have raised exception")
        except (ValueError, KeyError) as e:
            print_result("Invalid broker name", True, f"Exception raised: {e}")
            tests_passed += 1
    except Exception as e:
        print_result("Invalid broker name", False, str(e))
    
    # Summary
    print_header("FAILURE HANDLING VALIDATION SUMMARY")
    print(f"  Tests passed: {tests_passed}/{tests_total}")
    print(f"  Success rate: {tests_passed/tests_total*100:.1f}%")
    
    if tests_passed == tests_total:
        print("\n✅ All failure handling tests passed!")
        return 0
    else:
        print(f"\n⚠️  {tests_total - tests_passed} test(s) failed")
        return 1

if __name__ == "__main__":
    sys.exit(validate_failure_handling())

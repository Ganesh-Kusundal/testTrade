# Dhan Connection Tester

Comprehensive endpoint testing tool for Dhan broker API integration.

## Quick Start

### 1. Setup Credentials

**Option A: Environment Variables**
```bash
export DHAN_CLIENT_ID="your_client_id"
export DHAN_ACCESS_TOKEN="your_access_token"
```

**Option B: Create .env file**
```bash
cat > .env << EOF
DHAN_CLIENT_ID=your_client_id
DHAN_ACCESS_TOKEN=your_access_token
EOF
```

**Option C: Command-line arguments**
```bash
./scripts/run_dhan_test.sh --client-id YOUR_ID --access-token YOUR_TOKEN
```

### 2. Run Tests

**Using the shell script (recommended):**
```bash
# Live environment
./scripts/run_dhan_test.sh

# Sandbox environment
./scripts/run_dhan_test.sh --sandbox

# Verbose output
./scripts/run_dhan_test.sh --verbose
```

**Using Python directly:**
```bash
python scripts/test_dhan_connection.py --verbose
```

## What Gets Tested

### ✅ Connection Lifecycle
- Connection establishment
- Profile validation
- Idempotent connect/disconnect
- Clean resource cleanup

### ✅ Market Data Endpoints
- **LTP** (Last Traded Price) - `/marketfeed/ltp`
- **Quote** (Full market depth) - `/marketfeed/quote`
- **OHLC** (Candle data) - `/marketfeed/ohlc`

Test symbols:
- NIFTY (Index)
- RELIANCE (NSE Equity)

### ✅ Historical Data
- Intraday candles - `/charts/intraday`
- Historical candles - `/charts/historical`
- Multiple timeframes (1m, 5m, 15m, 1h, 1d)

### ✅ Portfolio Endpoints
- **Positions** - `/positions`
- **Holdings** - `/holdings`
- **Fund Limits** - `/fundlimits`

### ✅ Order Management
- Order book fetch - `/orders`
- Trade book fetch - `/trades`
- Order adapter initialization

### ✅ Instrument Master
- CSV download from `images.dhan.co`
- Symbol resolution
- Security ID mapping

### ✅ WebSocket Live Feed
- WebSocket connection
- Subscription to live ticks
- Tick data reception
- Clean disconnect

## Output Format

Each test produces:
```
✅ test_name: Description with details
```

Or on failure:
```
❌ test_name: Error description
```

Final summary shows:
```
Total: 20 | Passed: 19 | Failed: 1
```

## Verbose Mode

Use `--verbose` or `-v` to see:
- Full API responses
- Detailed tick data
- Complete quote information
- Raw candle data

## Sandbox Testing

The tester supports Dhan's sandbox environment:

```bash
./scripts/run_dhan_test.sh --sandbox
```

This uses:
- Base URL: `https://sandbox.dhan.co/v2`
- Sandbox credentials
- Paper trading instruments

## Troubleshooting

### "No credentials found"
Set environment variables or use command-line args:
```bash
export DHAN_CLIENT_ID="123456"
export DHAN_ACCESS_TOKEN="your_token_here"
```

### "Connection failed"
1. Verify credentials are correct
2. Check token hasn't expired
3. Ensure network connectivity
4. Verify static IP (if required by Dhan)

### "WebSocket connection timeout"
1. Check firewall settings
2. Verify WebSocket URL is accessible
3. Ensure token is valid
4. Check network stability

### "Rate limit exceeded"
The tester respects Dhan's rate limits:
- Orders: 10 req/sec
- Quotes: 1 req/sec
- LTP/OHLC: 5 req/sec

If you hit limits, wait a few seconds and retry.

## API Endpoints Reference

See [docs/dhan_endpoint_reference.md](../docs/dhan_endpoint_reference.md) for complete endpoint documentation.

## Programmatic Usage

You can also use the tester in your code:

```python
from config.endpoints import Dhan
from scalpr.brokers.dhan.connection import DhanConnection
from scripts.test_dhan_connection import DhanEndpointTester

# Create connection
connection = DhanConnection({
    "client_id": "123456",
    "access_token": "your_token",
})

# Run tests
tester = DhanEndpointTester(connection, verbose=True)
results = tester.run_all_tests()

# Check specific results
if results["ltp_NIFTY"]["success"]:
    print(f"NIFTY LTP: {results['ltp_NIFTY']['data']}")
```

## Test Results

Results are stored in a dictionary:
```python
{
    "test_name": {
        "success": True,
        "details": "Description",
        "data": {...}  # Optional response data
    }
}
```

## Exit Codes

- `0`: All tests passed
- `1`: One or more tests failed

Useful for CI/CD pipelines:
```bash
./scripts/run_dhan_test.sh && echo "SUCCESS" || echo "FAILED"
```

## Files

- `scripts/test_dhan_connection.py` - Main test script
- `scripts/run_dhan_test.sh` - Helper shell script
- `docs/dhan_endpoint_reference.md` - Complete endpoint reference
- `config/endpoints.py` - Dhan API endpoint definitions

## Requirements

- Python 3.10+
- Dhan broker account
- Valid API credentials (client ID + access token)
- Network access to Dhan APIs

## Notes

- Tests run in sequence (not parallel)
- Each test is independent
- Safe to run multiple times
- No actual orders are placed (read-only tests)
- WebSocket test subscribes to live market data

## Support

For issues or questions:
1. Check verbose output: `--verbose`
2. Review endpoint reference docs
3. Verify credentials with Dhan dashboard
4. Check Dhan API status page

---

**Status**: Production Ready ✅
**Last Updated**: 2024-06-24

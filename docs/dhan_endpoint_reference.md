# Dhan API Endpoint Reference

Complete reference for all Dhan API endpoints tested in the connection tester.

## REST API Endpoints

### Base URL
- **Live**: `https://api.dhan.co/v2`
- **Sandbox**: `https://sandbox.dhan.co/v2`

---

## 1. Authentication

### Token Generation
```python
GENERATE_TOKEN_URL = "https://auth.dhan.co/app/generateAccessToken"
```

### Profile Validation
```python
GET /profile
```
**Response Fields:**
- `name`: Account holder name
- `dataPlan`: Subscription status ("active" | "inactive")
- `dataValidity`: Token expiry date
- `activeSegment`: List of enabled segments (e.g., ["NSE_EQ", "NSE_FNO", "MCX_COMM"])

---

## 2. Market Data Endpoints

### LTP (Last Traded Price)
```python
GET /marketfeed/ltp
```
**Parameters:**
- `securityId`: Instrument security ID
- `exchangeSegment`: Exchange segment (NSE_EQ, MCX_COMM, etc.)

**Returns:** `Decimal` price

### Quote (Full Market Depth)
```python
GET /marketfeed/quote
```
**Returns:** Dict with:
- `ltp`: Last traded price
- `open`, `high`, `low`, `close`: OHLC
- `volume`: Traded volume
- `bidPrice`, `askPrice`: Best bid/ask
- `bidQty`, `askQty`: Best bid/ask quantities

### OHLC (Candle Data)
```python
GET /marketfeed/ohlc
```
**Parameters:**
- `securityId`: Instrument security ID
- `exchangeSegment`: Exchange segment

---

## 3. Historical Data Endpoints

### Intraday Candles
```python
GET /charts/intraday
```
**Parameters:**
- `securityId`: Instrument security ID
- `exchangeSegment`: Exchange segment
- `timeFrame`: Timeframe (1m, 5m, 15m, 1h, 1d, etc.)

### Historical Candles
```python
GET /charts/historical
```
**Parameters:**
- `securityId`: Instrument security ID
- `exchangeSegment`: Exchange segment
- `fromDate`: Start date (ISO format)
- `toDate`: End date (ISO format)
- `timeFrame`: Timeframe

**Returns:** List of `OHLCV` candles

---

## 4. Option Chain

### Option Chain Data
```python
GET /optionchain
```
**Parameters:**
- `securityId`: Underlying security ID
- `exchangeSegment`: Segment (NSE_FNO, MCX_COMM)

**Returns:** Option chain with strikes, Greeks, OI

---

## 5. Order Management

### Place Order
```python
POST /orders
```
**Payload:**
```json
{
  "dhanClientId": "123456",
  "correlationId": "unique_id_123",
  "transactionType": "BUY",
  "exchangeSegment": "NSE_EQ",
  "productType": "INTRADAY",
  "orderType": "LIMIT",
  "validity": "DAY",
  "securityId": "11536",
  "quantity": 10,
  "price": "2500.00",
  "triggerPrice": "2450.00"
}
```

### Modify Order
```python
PUT /orders/{orderId}
```
**Payload:**
```json
{
  "orderId": "ord_123",
  "price": "2600.00",
  "quantity": 15,
  "triggerPrice": "2550.00"
}
```

### Cancel Order
```python
DELETE /orders/{orderId}
```

### Order Book
```python
GET /orders
```
**Returns:** List of all orders for the day

### Trade Book
```python
GET /trades
```
**Returns:** List of all executed trades

---

## 6. Portfolio Endpoints

### Positions
```python
GET /positions
```
**Returns:** List of intraday/positional trades

### Holdings
```python
GET /holdings
```
**Returns:** List of long-term holdings

### Fund Limits
```python
GET /fundlimits
```
**Returns:**
- `availableBalance`: Available cash
- `collateralAmount`: Collateral value
- `usedMargin`: Margin used
- `realizedProfit`: Realized P&L
- `unrealizedProfit`: Unrealized P&L

---

## 7. Instrument Master

### Download CSV
```python
GET https://images.dhan.co/api-data/api-scrip-master.csv
```
**Returns:** CSV with all instruments across segments

### MCX Detailed
```python
GET /instrument/MCX_COMM
```

---

## 8. WebSocket Live Feed

### Depth 20 (20-level depth)
```python
WS wss://depth-api-feed.dhan.co/twentydepth
```

### Depth 200 (Full depth)
```python
WS wss://full-depth-api.dhan.co/twohundreddepth
```

**Subscription Message:**
```json
{
  "subscription": {
    "mode": "R",  // R=Quote, D=Depth, T=Trade
    "symbols": [
      {
        "securityId": "13",
        "exchangeSegment": "IDX_I"
      }
    ]
  }
}
```

**Tick Response:**
```json
{
  "type": "1",
  "symbol": "13",
  "ltp": "22450.50",
  "ltpQty": "100",
  "volume": "1234567",
  "totalBuyQty": "500000",
  "totalSellQty": "450000",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

## Exchange Segments

| Segment Code | Description |
|--------------|-------------|
| `NSE_EQ` | NSE Equity |
| `NSE_FNO` | NSE Futures & Options |
| `BSE_EQ` | BSE Equity |
| `MCX_COMM` | MCX Commodity |
| `IDX_I` | Indices |

---

## Rate Limits

| Endpoint | Limit | Interval |
|----------|-------|----------|
| `/orders` | 10 requests | 1 second |
| `/marketfeed/quote` | 1 request | 1 second |
| `/marketfeed/ltp` | 5 requests | 1 second |
| `/marketfeed/ohlc` | 5 requests | 1 second |
| `/optionchain` | 1 request | 1 second |
| `/charts/*` | 5 requests | 1 second |

---

## Error Handling

### HTTP Status Codes
- `200`: Success
- `400`: Bad Request (invalid parameters)
- `401`: Unauthorized (invalid token)
- `429`: Rate Limited
- `500`: Internal Server Error

### Common Errors
```python
AuthenticationError: Token expired or invalid
BrokerError: Generic broker error
ConfigurationError: Missing config keys
OrderError: Order placement/modification failed
```

---

## Usage Examples

### 1. Test All Endpoints
```bash
# Set credentials
export DHAN_CLIENT_ID="your_client_id"
export DHAN_ACCESS_TOKEN="your_access_token"

# Run comprehensive tests
python scripts/test_dhan_connection.py --verbose
```

### 2. Use Connection in Code
```python
from config.endpoints import Dhan
from scalpr.brokers.dhan.connection import DhanConnection

# Create connection
connection = DhanConnection({
    "client_id": "123456",
    "access_token": "your_token",
})

# Connect
connection.connect()

# Market Data
ltp = connection.market_data.get_ltp("RELIANCE", "NSE")
quote = connection.market_data.get_quote("RELIANCE", "NSE")

# Historical Data
candles = connection.historical.get_ohlcv(
    symbol="RELIANCE",
    exchange="NSE",
    timeframe="5m",
)

# Portfolio
positions = connection.portfolio.get_positions()
funds = connection.portfolio.get_fund_limits()

# Orders
order = Order(
    order_id="1",
    symbol="RELIANCE",
    exchange=Exchange.NSE,
    side=OrderSide.BUY,
    order_type=OrderType.LIMIT,
    quantity=10,
    price=Decimal("2500.00"),
    state=OrderState.PENDING,
)
fill = connection.orders.place_order(order)

# Disconnect
connection.disconnect()
```

### 3. WebSocket Live Feed
```python
import asyncio
from scalpr.brokers.dhan.websocket import DhanWebSocketClient

async def test_feed():
    ws = DhanWebSocketClient(
        access_token="your_token",
        client_id="123456",
    )
    
    # Connect
    await ws.connect()
    
    # Subscribe to NIFTY
    await ws.subscribe([("13", "R")])
    
    # Receive ticks
    while True:
        tick = await ws.receive_tick()
        print(f"LTP: {tick.get('ltp')}")
    
    # Disconnect
    await ws.disconnect()

asyncio.run(test_feed())
```

---

## Testing Checklist

- [ ] Profile endpoint returns valid data
- [ ] LTP fetch works for NSE and MCX
- [ ] Quote fetch returns all fields
- [ ] Historical candles retrieved
- [ ] Positions/holdings accessible
- [ ] Fund limits accurate
- [ ] Instrument master downloaded
- [ ] Order book/trade book fetchable
- [ ] WebSocket connects and receives ticks
- [ ] Rate limits respected
- [ ] Error handling works correctly

---

## Troubleshooting

### Connection Failed
1. Check client_id and access_token
2. Verify token hasn't expired
3. Check network connectivity
4. Verify static IP (if required)

### Order Rejected
1. Check sufficient funds
2. Verify exchange segment mapping
3. Ensure market is open
4. Check price within circuit limits

### WebSocket Not Connecting
1. Verify WebSocket URL
2. Check firewall/proxy settings
3. Ensure token is valid
4. Monitor connection state

---

**Last Updated**: 2024-06-24
**Status**: Production Ready ✅

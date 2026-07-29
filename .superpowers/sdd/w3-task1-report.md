# W3 Task 1: Split `IBrokerGateway` into Focused Sub-Interfaces

**Status:** DONE

## Files Changed

| File | Change |
|------|--------|
| `scalpr/brokers/broker_port.py` | Defined `ITradingPort`, `IMarketDataPort`, `IAccountPort`; `IBrokerGateway` now inherits all 3 + lifecycle |
| `scalpr/brokers/gateway/__init__.py` | Exported new interfaces in `__all__` |
| `scalpr/brokers/gateway/facade.py` | Added typed port properties (`.trading`, `.market_data`, `.account`); replaced `adapters()["http_client/resolver"]` with `connection.http_client` / `connection.resolver` |
| `scalpr/execution/order_router.py` | Changed `gateway: IBrokerGateway` → `gateway: ITradingPort` |
| `tests/unit/brokers/test_gateway.py` | Updated 3 test methods to mock `connection` instead of `adapters()` |

## Interface Design

```
ITradingPort          IMarketDataPort       IAccountPort
────────────────────  ────────────────────  ────────────────────
place_order()         get_ltp()             get_positions()
modify_order()        get_quote()           get_holdings()
cancel_order()        get_ohlcv()           get_margins()
get_order_status()                          get_fund_limits()
get_orders()
get_tradebook()
square_off_all()

             ┌─────────────────────────────────────┐
             │     IBrokerGateway                   │
             │  (ITradingPort + IMarketDataPort     │
             │   + IAccountPort + lifecycle)        │
             │                                     │
             │  connect() / disconnect()            │
             │  is_connected() / connection         │
             │  adapters()                          │
             └─────────────────────────────────────┘
```

## Design Decisions

1. **Backward compatibility preserved** — `IBrokerGateway` inherits all three sub-interfaces, so every existing consumer (`Mock(spec=IBrokerGateway)`, `create_autospec(IBrokerGateway)`, `issubclass(X, IBrokerGateway)`, `isinstance(x, IBrokerGateway)`) continues to work unchanged.

2. **No method changes** — all method names and signatures are exactly as they were. This is pure interface segregation, not API redesign.

3. **Typography** — the three implementors (`DhanGateway`, `SimulatedGateway`, `PaperOms`) did **not** need changes because they already implement all methods, and `IBrokerGateway` still unifies the three sub-interfaces.

4. **`facade.py` port exposure** — `Gateway` now exposes `.trading`, `.market_data`, `.account` as typed `ITradingPort`/`IMarketDataPort`/`IAccountPort` properties. Internal methods (`_get_option_chain_adapter`, `strike_selection`) use `connection.http_client`/`connection.resolver` instead of `adapters()["http_client"]`/`adapters()["resolver"]`.

5. **Lifecycle stays on `IBrokerGateway`** — `connect()`, `disconnect()`, `is_connected()`, `connection` property, and `adapters()` are only on the combined interface since they don't belong to any single functional domain.

## Test Results

- **Unit tests:** 947 passed, 0 failed
- **Contract tests:** 54 passed, 0 failed
- **Warnings:** 2 (pre-existing Starlette deprecation + asyncio warning)

# M5: Gateway API — MagicMock → SimulatedGateway + real doubles

## Status
**Complete.** All 15 tests pass with zero `MagicMock` usage.

## Mock count

| Metric | Before | After |
|--------|--------|-------|
| `MagicMock()` calls | 11 | 0 |
| `from unittest.mock import MagicMock` | Yes | **Removed** |

## What changed

### Removed (all `MagicMock()`)
1. `gw._registry = MagicMock()` → `None` (never used)
2. `mock_conn = MagicMock()` → `_FakeConnection(resolver)`
3. `mock_resolver = MagicMock()` → `_FakeResolver(return_value=…)`
4–6. `mock_conn.market_data / historical / http_client = MagicMock()` → via `_FakeConnection.__init__`
7. `mock_oc_adapter_cls = MagicMock()` → registered `_FakeOptionChainAdapter` class
8. `mock_oc_adapter_cls.return_value = MagicMock()` → (no longer needed — instances created by real class)
9. `mock_broker_gw = MagicMock()` → `_FakeSimulatedGateway(connection=conn)`
10–11. `handle._option_chain = MagicMock(...)` → `_FakeOptionChainAdapter` with `_return_value` / default `[]`

### Added (real test doubles)
| Class | Role |
|-------|------|
| `_FakeResolver` | Canned `resolve_full()` + `assert_called_once_with` |
| `_FakeMarketData` | Stub `get_ltp_by_id`, `get_quote_by_id`, `get_depth_by_id` |
| `_FakeHistorical` | Stub `get_ohlcv` |
| `_FakeHttpClient` | Stub implementing `HttpClientProtocol` (6 no-op methods) |
| `_FakeConnection` | Aggregates resolver + 3 adapters |
| `_FakeSimulatedGateway` | Extends `SimulatedGateway` + overrides `connection` property |
| `_FakeOptionChainAdapter` | Canned `get_option_chain()` + `assert_called_once` |

### Architecture
- `_gateway_with_mock` → `_gateway_with_real_doubles`
- Underlying broker gateway is now `_FakeSimulatedGateway(SimulatedGateway)` — uses the real `IBrokerGateway` implementation as base, only overrides `connection` to provide resolver stubs needed by `Gateway.instrument()`
- Zero `unittest.mock` imports in the file

## Test results
```
15 passed in 1.36s
```

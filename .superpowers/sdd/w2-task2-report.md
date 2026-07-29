# Task 2: Consolidate error-handling patterns in `scalpr/brokers/dhan/mapper.py`

**Status:** DONE

## Three patterns found

| # | Location | Method | Return type | Error handling |
|---|----------|--------|-------------|----------------|
| 1 | `mapper.py:63` | `order_to_dhan_request` | `Result[T, str]` | `try`/`except` wrapping entire body, returns `Result.failure(str(exc))` |
| 2 | `mapper.py:168` | `raw_order_to_order` | `Order` (plain) | No error handling — relies on `.get()` defaults, exceptions propagate raw |
| 3 | `mapper.py:233` | `raw_trade_to_fill` | `Fill` (plain) | Partial — `contextlib.suppress` on date parsing, otherwise exceptions propagate raw |

## Chosen pattern

**Pattern 1** — `Result[T, str]` monadic wrapper, already defined in `mapper.py:20-47` and used by 3 other methods (`order_to_dhan_request`, `dhan_response_to_fill`, `dhan_position_to_domain`). Cleanly signals failure in the type signature.

## Changes

### `scalpr/brokers/dhan/mapper.py`
- `raw_order_to_order`: return type `Order` → `Result[Order, str]`, body wrapped in `try`/`except` returning `Result.success()` / `Result.failure(str(exc))`
- `raw_trade_to_fill`: return type `Fill` → `Result[Fill, str]`, same wrapping

### `scalpr/brokers/dhan/gateway.py`
- `get_order()`: unwrap Result; raise `BrokerError` on failure
- `get_orders()`: unwrap via `.value` (raises `ValueError` on failure)
- `get_tradebook()`: unwrap via `.value`

### `tests/unit/brokers/dhan/test_gateway_connection.py`
- 14 call sites: `order = DhanMapper.raw_order_to_order(...)` → `result = ...` / `assert result.is_ok` / `order = result.value`

### `tests/unit/brokers/test_gateway_trades.py`
- 2 call sites: same pattern for `raw_trade_to_fill`

## Test results

```
558 passed, 3 failed in 2.68s
```

The 3 failures are **pre-existing and unrelated** (token refresh key error, missing `connection` attribute in interface compliance). All mapper-related tests pass.

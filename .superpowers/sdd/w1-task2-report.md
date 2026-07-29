# W1 Task 2 — Replace `adapters()["connection"]` with typed property

**Status:** DONE

## Files changed

### 1. `scalpr/brokers/gateway/facade.py` (lines 186-190)

**Before:**
```python
        adapters = self._gateway.adapters()
        if not adapters:
            raise NotImplementedError(
                "instrument() requires a broker that provides adapters"
            )
        conn = adapters["connection"]
```

**After:**
```python
        conn = self._gateway.connection
        if conn is None:
            raise NotImplementedError(
                "instrument() requires a broker that provides adapters"
            )
```

### 2. `scalpr/brokers/broker_port.py` — Added `connection` abstract property to `IBrokerGateway`

Added typed property so `self._gateway.connection` is valid across all implementations.

### 3. `scalpr/simulation/simulated_gateway.py` — Added `connection` property (returns `None`)

### 4. `scalpr/oms/paper_oms.py` — Added `connection` property (returns `None`)

### 5. `tests/unit/brokers/test_gateway.py` — Updated test mock to use `.connection` instead of `.adapters()`

In `TestGatewayErrorTranslation::test_instrument_not_found_is_broker_agnostic`:
- Replaced `gw._gateway.adapters.return_value = {...}` with `gw._gateway.connection = conn`
- Added `gw._broker_name = "dhan"`

### 6. `tests/unit/brokers/dhan/test_gateway_connection.py` — Updated compliance test to detect properties

In `test_should_implement_all_abstract_methods`: added `isinstance(method, property)` check alongside `callable(method)` so the `connection` property (which is a descriptor, not callable) is detected as a concrete implementation.

## Test results

```
$ pytest tests/unit/brokers/dhan/ -q --tb=short
426 passed in 1.54s

$ pytest tests/unit/ -q --tb=short
947 passed, 2 warnings in 23.58s
```

**0 failures** — full unit suite green.

# P1-K037: Delete dead `adapters()` method from `DhanGateway`

**Status:** ✅ Done

## What was deleted

**File:** `scalpr/brokers/dhan/gateway.py` (lines 396–407)

Removed the `adapters()` method from `DhanGateway`:

```python
def adapters(self) -> dict[str, Any]:
    """Return Dhan-specific adapters for advanced operations.

    Returns a dict with 'connection' and 'resolver' keys that the
    broker-agnostic layer can use for operations like option chains.
    This eliminates the need to reach into private state.
    """
    return {
        "connection": self._connection,
        "resolver": self._connection.resolver,
        "http_client": self._connection.http_client,
    }
```

## Verification

- **Production code:** `grep` for `\.adapters\(\)` in `scalpr/` — **zero results**. The facade (`facade.py`) uses `self._gateway.connection` directly since K-032.
- **Test code:** `grep` for `\.adapters\(\)` in `tests/` — **zero results**. No test file calls this method.
- **Base class:** `IBrokerGateway.adapters()` in `broker_port.py` remains as a default implementation (`return {}`) for the contract — intentionally kept.
- **Import `Any`:** Still used elsewhere in `gateway.py` (config, quotes, margins, OHLCV types) — not removed.

## Test results

```
$ pytest tests/unit/brokers/dhan/test_gateway_connection.py -q --tb=short
89 passed in 0.66s
```

All 89 tests pass. No regressions.

# K-034: Rename `CircuitBreaker` → `HttpCircuitBreaker` — Report

**Status:** ✅ Complete

## Files changed

| File | Change |
|------|--------|
| `scalpr/brokers/dhan/http_client.py:40` | Class renamed `CircuitBreaker` → `HttpCircuitBreaker` |
| `scalpr/brokers/dhan/http_client.py:95` | Type annotation updated |
| `scalpr/brokers/dhan/http_client.py:105` | Default constructor call updated |
| `scalpr/brokers/dhan/connection.py:21` | Import updated |
| `scalpr/brokers/dhan/connection.py:255` | Constructor call updated |

## Verification

- **`pytest tests/unit/brokers/dhan/ -q --tb=short`**: **417 passed** in 1.47s
- **Stale import check**: 0 remaining references to `CircuitBreaker` from `http_client`
- **Risk `CircuitBreaker`** (`scalpr/risk/circuit_breaker.py`): untouched — no files changed

## Summary

The HTTP fault-isolation class is now `HttpCircuitBreaker`, fully disambiguated from the financial risk `CircuitBreaker`. No test modifications were needed — the Dhan broker test suite (`tests/unit/brokers/dhan/`) had no direct references to the old name.

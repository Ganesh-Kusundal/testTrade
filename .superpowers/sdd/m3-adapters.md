# M3 — Replace `MagicMock` with real implementations in Dhan adapter tests

## Files changed

| File | Before (MagicMock calls) | After (MagicMock calls) |
|---|---|---|
| `tests/unit/brokers/dhan/test_option_chain.py` | 13 | 2 |
| `tests/unit/brokers/dhan/test_adapters.py` | 9 | 1 |
| **Total** | **22** | **3** |

Reduction: **19 bare `MagicMock()` calls removed** (–86 %).

## Test results

```
pytest tests/unit/brokers/dhan/test_option_chain.py \
       tests/unit/brokers/dhan/test_adapters.py \
       -v --tb=short
→ 124 passed in 0.96s  (pre-change: 124 passed in 0.81s)
```

Zero regressions.

## What changed

### `test_option_chain.py`

- **`_adapter()`** now builds a **real `SymbolResolver`** loaded with test CSV rows
  (NIFTY index, TCS/RELIANCE equities, GOLD/SILVER MCX futures) instead of
  bare `MagicMock()` for both `resolver` and `resolved`.
- HTTP client kept as **`MagicMock(spec=DhanHttpClient)`** — tests precisely
  control wire responses while the spec prevents interface drift.
- **13 tests** that previously created per-test `MagicMock() resolved` objects
  now use the real resolver, exercising actual `resolve_full`,
  `resolve_underlying_for_options`, and `get_by_security_id` behaviour.
- Tests needing extra resolver data (option securities) pass
  `include_options=True` to `_adapter()`.
- `test_scanner_resolves_by_security_id` uses a **real** `SymbolResolver` for
  the scanner too (was `MagicMock` with `get_by_security_id` stubbed).

### `test_adapters.py`

- **`mock_resolver` fixture** replaced bare `MagicMock()` with a **real
  `SymbolResolver`** pre-loaded with RELIANCE, TCS, NIFTY, INFY, HDFC rows.
- **`mock_http_client` fixture** changed from bare `MagicMock()` to
  **`MagicMock(spec=DhanHttpClient)`** — spec-safe.
- All **6 inline `MagicMock()` instrument instances** eliminated; real
  `Instrument` objects returned by the resolver satisfy the adapter code.
- 13 tests updated to work with the real resolver:
  - Call-assertion tests (`assert_called_once_with`) → behaviour verification
    (check HTTP payloads instead)
  - `side_effect` / `return_value` overrides → symbols not in the resolver
    naturally produce the required error (e.g. `"UNKNOWN"` → `NotFoundError`)

## Mock usage still remaining

The **3 remaining `MagicMock` calls** are all `MagicMock(spec=DhanHttpClient)`
— minimal, spec-constrained mocks for the HTTP layer. The resolver layer has
zero mocks: all 124 tests run against the real `SymbolResolver`.

## Risk

Low. All changes are in test code only. The real `SymbolResolver` uses
in-memory data (no I/O), is deterministic, and matches the live CSV row format
already used by `tests/unit/brokers/dhan/test_instrument_mapper.py`.

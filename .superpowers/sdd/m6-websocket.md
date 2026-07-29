# M6: Replace MagicMock/Mock with spec'd implementations in WebSocket tests

**Status:** ✅ Done
**Branch:** feat/30day-remediation
**Commit:** 0a361a7 (dirty)

---

## Changes

### `tests/unit/brokers/dhan/test_websocket.py`

| Location | Before | After | Reason |
|---|---|---|---|
| `_make_manager()` | `MagicMock()` (mock_client) | `MagicMock(spec=DhanWebSocketClient)` | Enforces client interface contract (connect, disconnect, subscribe, unsubscribe, on_tick) |
| `_make_manager()` | `mgr._ws_parser = MagicMock()` | `mgr._ws_parser = None` | Dead code — `_ensure_components()` sets it to `None` in prod |
| `_make_resolver()` | `MagicMock()` (resolver) | `MagicMock(spec=ResolverProtocol)` | Ensures resolver has `resolve()` and `wire_segment_of()` |
| `_make_resolver()` | `MagicMock()` (inst) | `MagicMock(spec=Instrument)` | Ensures returned instrument has `security_id` field |
| `test_on_tick_registers_callback` | `cb = MagicMock()` | `cb = MagicMock(spec=lambda x: None)` | Callable-contract enforcement |

### `tests/unit/brokers/dhan/test_ws_subscribe_honest.py`

| Location | Before | After | Reason |
|---|---|---|---|
| `mock_resolver` fixture | `MagicMock()` (resolver) | `MagicMock(spec=ResolverProtocol)` | Ensures resolver interface contract |
| `mock_resolver` fixture | `MagicMock()` (inst) | `MagicMock(spec=Instrument)` | Ensures instrument shape (security_id) |
| `_connected_client()` | `MagicMock()` (feed) | `MagicMock(spec=_FeedSpec)` | Custom spec class with `subscribe_symbols` |
| `test_mixed_results` | `MagicMock()` (inst) | `MagicMock(spec=Instrument)` | Same fixture-level enforcement |

---

## Mock count

| File | Before | After | Δ |
|---|---|---|---|
| `test_websocket.py` | 10 | 8 | -2 (ws_parser removed, cb spec'd) |
| `test_ws_subscribe_honest.py` | 4 | 4 | 0 (all 4 now spec'd) |

Note: All remaining mocks are now spec'd — zero bare `MagicMock()` calls.

---

## Test results

```
47 passed in 0.98s
```

All 47 tests pass with no regressions.

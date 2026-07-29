# P1-K033 Report: OMS `_append_event` Order Fix

**Status:** DONE

## Summary

Only `process_fill` had the actual bug — `add_order` and `update_order_state` already appended the event before mutating state.

## Caller-by-caller audit

### 1. `add_order` (line 39) — **Already correct**

| Step | Before (line) | After (line) |
|------|----------------|--------------|
| Validate duplicate | 42-43 | 42-43 |
| **`_append_event`** | **45** | **45** |
| `self.orders[...] = order` | 47 | 47 |

No change needed.

### 2. `update_order_state` (line 57) — **Already correct**

| Step | Before (line) | After (line) |
|------|----------------|--------------|
| `transition_to` (returns new instance, no mutation) | 63 | 63 |
| **`_append_event`** | **65-67** | **65-67** |
| `self.orders[...] = updated` | 69 | 69 |

`transition_to` uses `replace` → no in-place mutation. Event already fires before the dict write. No change needed.

### 3. `process_fill` (line 81) — **Fixed**

| Step | Before (line) | After (line) |
|------|----------------|--------------|
| `self.fills[order_id] = []` | 90 | 103-104 (moved **after** append) |
| Duplicate check (reads `self.fills`) | 93 | 90 (now safe via `.get(order_id, [])`) |
| Overflow check (reads `self.fills`) | 97 | 94 (now safe via `.get(order_id, [])`) |
| **`_append_event`** | **104** | **101** |
| `self.fills[order_id] = []` | — | 103-104 |
| `self.fills[...].append(fill)` | 106 | 106 |

**Root cause:** `self.fills[order_id] = []` at the old line 90 was a state mutation that executed *before* `_append_event`. If `_append_event` raised (EventStore down), the OMS had a dangling empty fill list with no event recorded — data corruption.

**Fix:** Moved `_append_event` (now line 101) before any state mutation. The two reads that previously depended on the init (`existing_ids`, `prospective_total`) now use `.get(order_id, [])`, which returns `[]` for unseen order_ids — a pure read, no mutation.

## Test results

```
tests/unit/execution/ tests/unit/oms/ -q --tb=short
46 passed in 1.12s
```

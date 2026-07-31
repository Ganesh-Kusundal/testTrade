# Task 3 Report — `OrderRegistry` (local↔broker identity map)

## What was implemented

- `scalpr/adapters/dhan/_order_registry.py` — `OrderRegistry`, a pure in-memory
  bidirectional map between local order ids and Dhan broker order ids. Taken
  verbatim from the Step 3 reference in
  `.superpowers/sdd/lifecycle-task-3-brief.md`: methods `register`,
  `broker_id`, `local_id`, `forget`, `all_broker_ids` with the exact
  signatures/semantics the brief specifies, including:
  - re-register replaces the stale reverse entry (old broker id no longer resolves)
  - `forget` removes both directions; unknown local id is a no-op
  - empty `broker_id` / `local_id` raise `ValueError` (refuse malformed broker responses)
  - `threading.Lock` guarding all operations (the brief's reference implementation includes it)
- `tests/unit/adapters/dhan/test_order_registry.py` — the brief's 7 test cases,
  converted from the brief's bare-pytest style to the `unittest.TestCase` +
  `setUp` + `self.assertEqual`/`self.assertIsNone` pattern used by neighbouring
  files (e.g. `test_order_queries.py`), per the orchestrator's instruction.
  Test names and asserted behaviour are unchanged from the brief.

## TDD sequence

1. Wrote the test file first.
2. Ran it — failed as the brief predicted:
   `ModuleNotFoundError: No module named 'scalpr.adapters.dhan._order_registry'`.
3. Wrote the implementation, re-ran — passed.

## Definition-of-done commands and output

### New tests

```
$ .venv/bin/python -m pytest tests/unit/adapters/dhan/test_order_registry.py -q
7 passed in 0.83s
```

(Brief expects `7 passed` — matches.)

### Full unit + contract suite

```
$ .venv/bin/python -m pytest tests/unit/ tests/contract/ -q
1688 passed, 3 warnings in 27.91s
```

Baseline was 1681 passed; 1681 + 7 new = 1688, `0 failed`. Matches expectation.

## Files changed

Created and staged (git add only — nothing committed):

- `scalpr/adapters/dhan/_order_registry.py` (new)
- `tests/unit/adapters/dhan/test_order_registry.py` (new)

```
A  scalpr/adapters/dhan/_order_registry.py
A  tests/unit/adapters/dhan/test_order_registry.py
```

Per the brief's Global Constraints, `python3 .qoder/skills/kanban.cli/scripts/kanban.py scan`
was re-run after the change (it updates its own `.kanban/` state files; those
were not staged).

## Self-review findings

- Exact names verbatim: `OrderRegistry`, `register`, `broker_id`, `local_id`,
  `forget`, `all_broker_ids` — Tasks 4/5/8 can call them as planned.
- Round-trip covered: `test_register_maps_both_directions` asserts both
  `broker_id()` and `local_id()` after one `register`.
- Forget-both-directions covered: `test_forget_removes_both_directions`
  asserts both lookups return `None` after `forget`.
- Tests assert behaviour (lookups, exceptions, list contents), not internals —
  no reference to `_to_broker`/`_to_local`.
- Nothing extra added: no persistence, no logging, no eviction, no `__len__`,
  no extra query helpers.

## Concerns

1. **Test style deviation from the brief's literal code**: the brief's Step 1
   shows bare-pytest classes; the orchestrator instruction said to follow the
   neighbouring `unittest.TestCase` pattern instead. I followed the
   orchestrator; the 7 cases, their names, and asserted semantics are identical
   to the brief.
2. **Thread lock vs. scope note**: the orchestrator's scope-discipline list says
   "no thread locks", but the brief's reference implementation explicitly
   includes `threading.Lock`. The brief is the stated source of truth for the
   implementation ("use ... verbatim"), so the lock is included.
3. The kanban scan reports pre-existing staleness (71 stale annotations,
   graphify STALE) unrelated to this task; not addressed here.

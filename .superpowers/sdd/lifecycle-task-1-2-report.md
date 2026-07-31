# Task 1 + Task 2 Report — Boundary guards made real, ports replace DhanClient

Date: 2026-07-31 · Base: HEAD c7fc087 · Status: **DONE**

## What was implemented

### Task 1: Make the boundary guards real
1. **Proved the guard was dead**: `.venv/bin/lint-imports --config pyproject.toml` exited 1 with
   `Module 'scalpr.adapters.dhan' does not exist.` — zero contracts evaluated.
2. **Created package markers** (both empty): `scalpr/adapters/__init__.py`,
   `scalpr/engine/__init__.py`. These were implicit namespace packages, which grimp
   cannot address.
3. **Demonstrated the cache lie** (same code, same config, opposite verdict):
   - Cached run: `Analyzed 133 files, 279 dependencies` → `Contracts: 7 kept, 0 broken.` (exit 0)
   - `--no-cache` run: `Analyzed 133 files, 309 dependencies` → `Contracts: 5 kept, 2 broken.` (exit 1), naming:
     - `scalpr.risk.session_guard -> scalpr.adapters.dhan.client (l.7)`
     - `scalpr.market_data.historical -> scalpr.adapters.dhan.client (l.5)`
   - *Deviation from brief*: the brief predicted 129 files / 266 vs 283 dependencies; actual
     counts were 133 / 279 vs 309. The verdicts and the two named violations match the brief
     exactly — the count drift is consistent with other files having landed since the brief's
     numbers were captured. Noted as a concern, not a blocker.
4. **Created `tests/unit/test_import_contracts.py`** verbatim from the brief: two tests —
   console-script presence, and a `--no-cache` subprocess run asserting both `"Contracts:"`
   in output (anti-vacuous-pass) and exit code 0.
5. **Confirmed it failed as designed**: `1 failed, 1 passed` — the failure message contained
   both violating imports from Step 3. Left red until Task 2, per plan.
6. **CI + cache hygiene**:
   - `.github/workflows/ci.yml:31` → `run: lint-imports --config pyproject.toml --no-cache`
   - Appended `.import_linter_cache/` to `.gitignore`
   - `git rm -r --cached .import_linter_cache` was a no-op (directory was never tracked;
     `|| true` handled it as anticipated); `rm -rf .import_linter_cache` removed it from disk.
7. **Suite unaffected**: `pytest tests/unit/ tests/contract/ -q --deselect tests/unit/test_import_contracts.py`
   → `1679 passed, 2 deselected, 3 warnings in 25.38s`.

### Task 2: Ports instead of DhanClient
1. **`scalpr/domain/contracts.py`**: appended `ExecutionGatewayProtocol`
   (`get_positions() -> list[Any]`, `place_order(order: Any) -> str`) and
   `HistoricalSourceProtocol` (`get_historical(symbol, exchange, timeframe, lookback_days) -> list[dict[str, Any]]`)
   after the existing `ResolverProtocol`, both `@runtime_checkable`, code verbatim from
   the brief. `Any` is deliberate — keeps `domain/contracts` free of an import edge to
   `scalpr.domain.position` (protects the `Domain independence` contract).
2. **`scalpr/risk/session_guard.py`**: line 7 import swapped to
   `from scalpr.domain.contracts import ExecutionGatewayProtocol`; constructor annotation
   changed to `gateway: ExecutionGatewayProtocol`. Body untouched — it only calls
   `get_positions()` and `place_order(...)`, both on the protocol.
3. **`scalpr/market_data/historical.py`**: line 5 import swapped to
   `from scalpr.domain.contracts import HistoricalSourceProtocol`; constructor annotation
   changed to `client: HistoricalSourceProtocol`. Body untouched (`load_history` returns `[]`).
4. No adapter changes — `DhanClient` satisfies both protocols structurally.

## Definition-of-done checks (exact commands + output)

### Check 1: guard
```
$ .venv/bin/lint-imports --config pyproject.toml --no-cache
Analyzed 133 files, 309 dependencies.
-------------------------------------
Domain independence KEPT
Risk cannot import API KEPT
OMS cannot import API KEPT
Strategy cannot import API KEPT
Broker Dhan isolation KEPT
Risk cannot import Dhan implementation KEPT
Market data cannot import Dhan implementation KEPT

Contracts: 7 kept, 0 broken.
```

### Check 2: suite
```
$ .venv/bin/python -m pytest tests/unit/ tests/contract/ -q
1681 passed, 3 warnings in 25.36s
```
1681 = 1679 baseline + 2 new guard tests. `tests/unit/test_import_contracts.py` now passes
legitimately (violations fixed, not the test weakened).

## Files changed (all staged via `git add`, nothing committed)

| File | Change |
|---|---|
| `scalpr/adapters/__init__.py` | new, empty package marker |
| `scalpr/engine/__init__.py` | new, empty package marker |
| `tests/unit/test_import_contracts.py` | new guard test (2 tests) |
| `.github/workflows/ci.yml` | line 31: added `--no-cache` |
| `.gitignore` | appended `.import_linter_cache/` |
| `scalpr/domain/contracts.py` | +2 protocols after existing protocol block |
| `scalpr/risk/session_guard.py` | import + constructor annotation → `ExecutionGatewayProtocol` |
| `scalpr/market_data/historical.py` | import + constructor annotation → `HistoricalSourceProtocol` |

Also present in the index: `docs/superpowers/plans/2026-07-31-broker-lifecycle-truth.md` was
**already staged before this work began** and was not touched. Unrelated working-tree
modifications (`.qoder/skills/dhanhq/**` etc.) were left undisturbed; no `git stash/checkout/
reset/clean` was run.

Per Global Constraints, `python3 .qoder/skills/kanban.cli/scripts/kanban.py scan` was re-run
after the code changes (reported +3 added / ~3 changed / 71 annotations stale — informational).

## Self-review findings

- **Completeness**: every step of both tasks executed; code taken verbatim from the brief.
  Nothing extra added (no adapter edits, no call-site changes beyond the two named files).
- **Real behaviour, not mocks**: the guard test shells out to the actual `lint-imports`
  console script against the real codebase; the `"Contracts:"` assertion prevents a
  vacuous pass. Verified it failed for the right reason before Task 2 and passes after.
- **Pattern conformance**: new protocols mirror `HttpClientProtocol`/`ResolverProtocol`
  style in `contracts.py` (`@runtime_checkable`, docstrings, `...` bodies, `Any` at
  boundaries). Test file follows existing unit-test conventions (module docstring,
  plain functions, stdlib only).
- **Cache hygiene double-checked**: `.import_linter_cache/` is gitignored, absent from
  disk, and never tracked; the pytest guard run (which uses `--no-cache`) does not
  recreate it.

## Concerns

1. **Brief's dependency counts were stale** (129/266/283 predicted vs 133/279/309 actual).
   Verdicts, contract names and the two violations matched exactly, so I proceeded; the
   drift suggests files landed after the brief was verified. No action needed, flagged
   for the plan author.
2. `test_import_contracts.py` remains red *in isolation between* Task 1 and Task 2 by
   design; since both tasks are staged together the staged state passes the full suite,
   satisfying the AGENTS.md staged-state rule. Committable only as a pair (not committed,
   per instruction).

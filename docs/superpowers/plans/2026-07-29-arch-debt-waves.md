# Architectural Debt — Multi-Wave Remediation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate the 16 remaining architectural debt items from the codebase review in 3 parallelizable waves.

**Architecture:** Isolated debt items within each wave are dispatched to parallel agents. Wave boundaries are sequential (Wave 2 depends on Wave 1 decisions for facade/connection cleanup).

**Tech Stack:** Python 3.13, pytest, dhanhq, aiohttp, pydantic

## Global Constraints

- 426 passing tests must remain passing after each merge point
- No new external dependencies
- All code changes must pass `pytest tests/unit/brokers/dhan/ -q --tb=short`
- Stage only (`git add`), never commit unless explicitly asked

---

## Wave 1: Quick Wins — 4 parallel agents

All 4 tasks are fully independent. Dispatch all 4 simultaneously.

### Task 1.1: K-031 — os.environ → SecretsManager (bootstrap.py)

**Files:**
- Modify: `scalpr/api/bootstrap.py:129-137`
- Test: no new tests needed (regression covered by existing DhanWebSocketManager tests)

**Interfaces:**
- Consumes: `SecretsManager.get_dhan_access_token()`, `SecretsManager.get_dhan_client_id()`
- Produces: bootstrap.py no longer reads `os.environ["DHAN_ACCESS_TOKEN"]` directly

- [ ] **Step 1: Read current code**

Read `scalpr/api/bootstrap.py` lines 125-144 and `config/secrets_manager.py` to understand SecretsManager API.

- [ ] **Step 2: Replace os.environ.get calls**

```python
from config.secrets_manager import SecretsManager

sm = SecretsManager()
feed = DhanWebSocketManager(
    access_token=sm.get_dhan_access_token() or "",
    client_id=sm.get_dhan_client_id() or "",
    resolver=gateway.connection.resolver,
    token_refresh_fn=lambda: ensure_fresh_token(force=True),
)
```

- [ ] **Step 3: Remove os import if no longer used elsewhere in file**

- [ ] **Step 4: Run tests**

Run: `pytest tests/unit/brokers/dhan/ -q --tb=short`
Expected: all 426 tests pass.

---

### Task 1.2: K-032 — Gateway property exposure (facade.py)

**Files:**
- Modify: `scalpr/brokers/gateway/facade.py:186-191`
- Test: `tests/unit/brokers/test_gateway_api.py` (if exists)

**Interfaces:**
- Consumes: `Gateway.connection` property (already exists)
- Produces: `instrument()` uses typed `self._gateway.connection` instead of `adapters()["connection"]`

- [ ] **Step 1: Read current code**

Read `scalpr/brokers/gateway/facade.py` lines 157-215 and `scalpr/brokers/gateway/gateway.py` to find the typed `connection` property.

- [ ] **Step 2: Replace adapters() dict access with typed property**

Replace:
```python
adapters = self._gateway.adapters()
if not adapters:
    raise NotImplementedError(...)
conn = adapters["connection"]
```

With:
```python
conn = self._gateway.connection
if conn is None:
    raise NotImplementedError(...)
```

- [ ] **Step 3: Update import if needed** (check if `connection` import is already present)

- [ ] **Step 4: Run tests**

Run: `pytest tests/unit/brokers/dhan/ tests/unit/brokers/test_gateway_api.py -q --tb=short`
Expected: all pass.

---

### Task 1.3: Remove PartialFill dead code (domain/fill.py)

**Files:**
- Modify: `scalpr/domain/fill.py:29-45`
- Test: search for PartialFill references, remove those tests too

**Interfaces:**
- Consumes: nothing
- Produces: `PartialFill` dataclass removed

- [ ] **Step 1: Check for all usages**

Run: `rg "PartialFill" scalpr/ tests/`
Check if anything still imports or references `PartialFill`.

- [ ] **Step 2: If dead, remove the class and all test references**

```python
# Delete lines 29-45 from scalpr/domain/fill.py
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/ -q --tb=short -x`
Expected: all pass (if PartialFill was truly dead code).

---

### Task 1.4: Fix stale annotation — test_verify_connection_retry.py

**Files:**
- Modify: `tests/unit/brokers/dhan/test_verify_connection_retry.py`

**Interfaces:**
- Consumes: `DhanConnection._verify_connection()`, `ensure_fresh_token()`
- Produces: docstrings/comments match current K-027 behavior

- [ ] **Step 1: Read file and verify behavior**

```bash
pytest tests/unit/brokers/dhan/test_verify_connection_retry.py -v --tb=short
```

- [ ] **Step 2: Fix stale annotation**

The file's `TotpRateLimitError` import references `from scalpr.brokers.dhan._totp_cooldown import TotpRateLimitError` — if it was moved to `scalpr/brokers/errors.py`, update the import. Also check docstrings for any references to deleted behavior.

- [ ] **Step 3: Re-run tests**

```bash
pytest tests/unit/brokers/dhan/test_verify_connection_retry.py -v --tb=short
```

Expected: all pass, no stale annotation warning from kanban.

---

## Wave 2: Component Cleanup — 4 parallel agents

Wave 2 starts after Wave 1 is merged. Tasks are independent.

### Task 2.1: PaperOms no-op consolidation (oms/paper_oms.py)

**Files:**
- Modify: `scalpr/oms/paper_oms.py:140-164`
- Test: `tests/unit/oms/test_paper_oms.py`

**Interfaces:**
- Consumes: `PaperOms` class
- Produces: `modify_order`, `cancel_order`, `get_order_status`, `get_positions`, `get_margins`, `is_connected` — remove no-ops that return `False`, consolidate or document

- [ ] **Step 1: Read the file**

Read `scalpr/oms/paper_oms.py` lines 140-264 to see which methods are true no-ops.

- [ ] **Step 2: Consolidate or annotate**

For each method that always returns a literal (`False`, `True`, `0`, etc), add a `# no-op: paper OMS fills immediately` comment or consolidate into base class defaults if possible.

- [ ] **Step 3: Run tests**

Run: `pytest tests/unit/oms/ -q --tb=short`

---

### Task 2.2: Mapper error pattern consolidation (mapper.py)

**Files:**
- Modify: `scalpr/brokers/dhan/mapper.py:63,168,233`

**Interfaces:**
- Consumes: `DhanMapper`, `Result` type
- Produces: unified error handling pattern

- [ ] **Step 1: Read the 3 locations**

Read `scalpr/brokers/dhan/mapper.py` lines 60-80, 165-180, 230-250 to understand the 3 different error patterns.

- [ ] **Step 2: Consolidate to one pattern**

Pick the best error-handling pattern and make all 3 locations use it consistently.

- [ ] **Step 3: Run tests**

Run: `pytest tests/unit/brokers/dhan/test_mapper.py -q --tb=short`

---

### Task 2.3: Lazy Dhan import relocation (facade.py:41-46)

**Files:**
- Modify: `scalpr/brokers/gateway/facade.py:41-46`

- [ ] **Step 1: Read the lazy import block and check if it's still needed**

The original review flagged `facade.py:41-46` which does `from scalpr.brokers.dhan import ...` inside a function. If the Dhan connection is now always required, move it to top-level; if truly optional, keep but document.

- [ ] **Step 2: Run tests**

Run: `pytest tests/unit/brokers/ -q --tb=short`

---

### Task 2.4: EventStore transactional guarantee (order_manager.py:151-158)

**Files:**
- Modify: `scalpr/observability/event_store.py`, `scalpr/execution/order_manager.py:151-158`

- [ ] **Step 1: Read current EventStore `_append_event` implementation**

- [ ] **Step 2: Make it transactional** — wrap in a try/except that rolls back on failure (or raise so the caller retries)

- [ ] **Step 3: Run tests**

Run: `pytest tests/unit/execution/ tests/unit/observability/ -q --tb=short`

---

## Wave 3: Architecture — 2 agents (partially dependent)

Wave 3 requires Wave 2 context.

### Task 3.1: God interface decomposition (broker_port.py)

**Files:**
- Modify: `scalpr/brokers/broker_port.py`
- Create: `scalpr/brokers/trading_port.py`, `scalpr/brokers/market_data_port.py` (or similar)

**Note:** This is the largest item. Break IBrokerGateway's 17 methods into focused interfaces. This touches all implementors (DhanGateway, SimulatedGateway). Requires careful planning — may need a separate sub-plan.

- [ ] **Step 1: Read IBrokerGateway interface and all implementors**

- [ ] **Step 2: Design interface split** — e.g. `ITradingPort` (orders, positions), `IMarketDataPort` (quotes, depth), `IAccountPort` (funds, profile)

- [ ] **Step 3: Implement the split across all implementors**

- [ ] **Step 4: Update all consumers** (`facade.py`, `order_router.py`, strategy code)

- [ ] **Step 5: Run full test suite**

---

### Task 3.2: _verify_connection decomposition (connection.py:307-421)

**Files:**
- Modify: `scalpr/brokers/dhan/connection.py:307-421`

- [ ] **Step 1: Read the 114-line method**

- [ ] **Step 2: Extract phases** — token check, profile fetch, data-plan validation, segment logging into separate private methods

- [ ] **Step 3: Run tests**

Run: `pytest tests/unit/brokers/dhan/test_gateway_connection.py tests/unit/brokers/dhan/test_verify_connection_retry.py -q --tb=short`

---

## Execution Order

```
Wave 1          │  Wave 2          │  Wave 3
─────────────────┼──────────────────┼──────────────────
Task 1.1 K-031  │  Task 2.1 Paper  │  Task 3.1 God I/F
Task 1.2 K-032  │  Task 2.2 Mapper │  Task 3.2 verify
Task 1.3 Partial │  Task 2.3 Import │
Task 1.4 Stale   │  Task 2.4 Events │
                 │                   │
ALL 4 PARALLEL   │  ALL 4 PARALLEL   │  2 PARALLEL
```

**After each wave:** run `pytest tests/unit/ -q --tb=short` and `pytest tests/contract/ -q --tb=short` to validate no regressions.

**After Wave 3:** run `pytest tests/ -q --tb=short` for full suite.

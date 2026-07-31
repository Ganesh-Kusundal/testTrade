## Global Constraints

- Money is `Decimal`. Never `float` in a domain object. `Fill.price` and `Order.price` raise `TypeError` on non-`Decimal`.
- `Order`, `Fill`, and all `exec.*` payloads are `@dataclass(frozen=True)`. Mutation means `dataclasses.replace`.
- Time comes from the injected `Clock` (`clock.timestamp()` / `clock.utc_now()`). Never call `datetime.now()` in adapter or engine code paths added by this plan.
- Topic convention is `{domain}.{verb}.{broker}` for broker-directed and broker-emitted messages: commands `exec.command.<verb>.dhan`, events `exec.event.<verb>.dhan`. Engine-internal domain events stay unsuffixed (`domain.order.placed`, `domain.fill.received`).
- Never import a private module across a package boundary. `scalpr.adapters.dhan._http` is internal to the Dhan adapter.
- Production modules outside `scalpr/adapters/dhan/` must not import `DhanClient` concretely — depend on a Protocol from `scalpr.domain.contracts`.
- Staging discipline from `AGENTS.md`: `git add` only. **Never `git commit`** unless the user explicitly asks. Every staged state must pass `pytest tests/unit/ tests/contract/` with 0 failures.
- After any code change, re-run `python3 .qoder/skills/kanban.cli/scripts/kanban.py scan`.


## Task 1: Make the boundary guards real

The guard currently aborts on the missing `scalpr/adapters/__init__.py`, and when that is fixed it reports green off a stale cache. Both have to go, and the cache must never be able to lie again.

**Files:**
- Create: `scalpr/adapters/__init__.py`
- Create: `scalpr/engine/__init__.py`
- Create: `tests/unit/test_import_contracts.py`
- Modify: `.github/workflows/ci.yml:31`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: nothing.
- Produces: a live `lint-imports --no-cache` run. Task 2 fixes the two violations it exposes.

- [ ] **Step 1: Prove the guard is currently dead**

```bash
.venv/bin/lint-imports --config pyproject.toml
```
Expected: `Module 'scalpr.adapters.dhan' does not exist.` — it never evaluates a single contract.

- [ ] **Step 2: Create the two missing package markers**

Both files are empty. `scalpr/adapters/` and `scalpr/engine/` are currently implicit namespace packages, which `grimp` cannot address.

```bash
touch scalpr/adapters/__init__.py scalpr/engine/__init__.py
```

- [ ] **Step 3: Show that the cache lies**

```bash
.venv/bin/lint-imports --config pyproject.toml
.venv/bin/lint-imports --config pyproject.toml --no-cache
```
Expected: the cached run reports `Analyzed 129 files, 266 dependencies` / `7 kept, 0 broken`. The `--no-cache` run reports `283 dependencies` / **`5 kept, 2 broken`**, naming:

```
scalpr.risk.session_guard -> scalpr.adapters.dhan.client (l.7)
scalpr.market_data.historical -> scalpr.adapters.dhan.client (l.5)
```

Same code, same config, opposite verdict. That is the finding.

- [ ] **Step 4: Write the failing guard test**

Create `tests/unit/test_import_contracts.py`:

```python
"""Architectural guard: the import-linter contracts must actually pass.

`lint-imports` caches its import graph in `.import_linter_cache/`. A stale
cache makes it report KEPT for contracts that are in fact broken, which is
worse than having no guard at all. This test always runs with --no-cache.
"""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# The console script, not `python -m importlinter.cli` — that module has no
# __main__ hook, exits 0 and prints nothing, which would make this guard pass
# vacuously forever. Resolving it next to sys.executable keeps it venv-correct.
LINT_IMPORTS = Path(sys.executable).parent / "lint-imports"


def test_lint_imports_executable_is_present():
    """If the console script moves, the guard below must fail loudly, not skip."""
    assert LINT_IMPORTS.exists(), f"lint-imports not found at {LINT_IMPORTS}"


def test_import_linter_contracts_pass_without_cache():
    result = subprocess.run(
        [str(LINT_IMPORTS), "--config", "pyproject.toml", "--no-cache"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    output = result.stdout + result.stderr
    # A silent success is not a success — it means nothing was evaluated.
    assert "Contracts:" in output, (
        "lint-imports produced no contract report; the guard would be vacuous:\n"
        + output
    )
    assert result.returncode == 0, (
        "import-linter contracts are broken (run with --no-cache to reproduce):\n"
        + output
    )
```

The `Contracts:` assertion is the point. Without it, any invocation that exits 0 without evaluating anything would satisfy this test — which is the same class of defect the test exists to catch.

- [ ] **Step 5: Run it to confirm it fails**

```bash
.venv/bin/python -m pytest tests/unit/test_import_contracts.py -q
```
Expected: FAIL, with the two violating imports from Step 3 in the assertion message. Leave it failing — Task 2 is what makes it pass.

Verified 2026-07-31: `python -m importlinter.cli lint-imports` prints nothing and exits 0 — the package has no `__main__` hook, so that invocation evaluates zero contracts. Use the console script as written above.

- [ ] **Step 6: Stop CI from trusting the cache**

In `.github/workflows/ci.yml`, change line 31 from:

```yaml
        run: lint-imports --config pyproject.toml
```

to:

```yaml
        run: lint-imports --config pyproject.toml --no-cache
```

Append to `.gitignore`:

```
.import_linter_cache/
```

Remove the stale cache from the working tree:

```bash
git rm -r --cached .import_linter_cache 2>/dev/null || true
rm -rf .import_linter_cache
```

- [ ] **Step 7: Confirm the rest of the suite is unaffected**

```bash
.venv/bin/python -m pytest tests/unit/ tests/contract/ -q --deselect tests/unit/test_import_contracts.py
```
Expected: `1679 passed`. Adding `__init__.py` files must not change any behaviour.

- [ ] **Step 8: Stage**

```bash
git add scalpr/adapters/__init__.py scalpr/engine/__init__.py \
        tests/unit/test_import_contracts.py .github/workflows/ci.yml .gitignore
```

Do not commit. `AGENTS.md` requires every staged state to pass the suite, and Task 1 deliberately leaves one test red — so Task 1 and Task 2 stage together and are only committable as a pair. If the user asks for a commit, do Task 2 first.

---

## Task 2: Give `risk` and `market_data` a port instead of `DhanClient`

The two violations Task 1 exposed are both a production module importing the concrete adapter. `session_guard` needs exactly two methods; `historical` does not use the client at all (`load_history` returns `[]`). A narrow Protocol fixes both and makes the broker a replaceable detail for these callers.

**Files:**
- Modify: `scalpr/domain/contracts.py`
- Modify: `scalpr/risk/session_guard.py:7`, `:18`
- Modify: `scalpr/market_data/historical.py:5`, `:12`

**Interfaces:**
- Consumes: Task 1's live guard.
- Produces: `scalpr.domain.contracts.ExecutionGatewayProtocol` (methods `get_positions()`, `place_order(order)`) and `scalpr.domain.contracts.HistoricalSourceProtocol` (method `get_historical(symbol, exchange, timeframe, lookback_days)`). `DhanClient` already satisfies both structurally — no adapter change is needed.

- [ ] **Step 1: Add the two ports**

`scalpr/domain/contracts.py` already hosts `HttpClientProtocol` and `ResolverProtocol` and already imports `Protocol` and `runtime_checkable`. Append after the existing protocol block:

```python
@runtime_checkable
class ExecutionGatewayProtocol(Protocol):
    """Outward port for order placement and position enquiry.

    Consumers in risk/, oms/ and strategy/ depend on this, never on a
    concrete broker adapter — the broker is a replaceable detail.
    """

    def get_positions(self) -> list[Any]:
        """Return current broker positions."""
        ...

    def place_order(self, order: Any) -> str:
        """Submit an order; return the broker's order id."""
        ...


@runtime_checkable
class HistoricalSourceProtocol(Protocol):
    """Outward port for historical candle retrieval."""

    def get_historical(
        self,
        symbol: str,
        exchange: str,
        timeframe: str,
        lookback_days: int,
    ) -> list[dict[str, Any]]:
        """Return raw historical candles for the given instrument."""
        ...
```

`Any` for `Position`/`Order` is deliberate: `scalpr.domain.contracts` must not grow an import edge to `scalpr.domain.position`, and the `Domain independence` contract is the thing keeping `domain/` clean. The concrete types are asserted at the call sites.

- [ ] **Step 2: Point `session_guard` at the port**

In `scalpr/risk/session_guard.py`, replace line 7:

```python
from scalpr.adapters.dhan.client import DhanClient
```

with:

```python
from scalpr.domain.contracts import ExecutionGatewayProtocol
```

and change the constructor signature at line 18:

```python
    def __init__(self, gateway: ExecutionGatewayProtocol, max_losses: int = 3) -> None:
```

The body is unchanged — it already only calls `self._client.get_positions()` (line 77) and `self._client.place_order(...)` (line 82).

- [ ] **Step 3: Point `historical` at the port**

In `scalpr/market_data/historical.py`, replace line 5:

```python
from scalpr.adapters.dhan.client import DhanClient
```

with:

```python
from scalpr.domain.contracts import HistoricalSourceProtocol
```

and change line 12:

```python
    def __init__(self, client: HistoricalSourceProtocol):
```

- [ ] **Step 4: Run the guard test**

```bash
.venv/bin/python -m pytest tests/unit/test_import_contracts.py -q
```
Expected: PASS. Confirm directly too:

```bash
.venv/bin/lint-imports --config pyproject.toml --no-cache
```
Expected: `Contracts: 7 kept, 0 broken.`

- [ ] **Step 5: Run the full suite**

```bash
.venv/bin/python -m pytest tests/unit/ tests/contract/ -q
```
Expected: `1681 passed` (1679 + the two new guard tests).

- [ ] **Step 6: Stage**

```bash
git add scalpr/domain/contracts.py scalpr/risk/session_guard.py scalpr/market_data/historical.py
```

---

# Review package: Tasks 1-2 (staged, not committed)

Index tree 5c153f2fa0786dd1572986c7b2aece69832e8bee -> 5dd196d260d21a8bb5fa202c06ab4b8120c0dab5

## Stat
```
 .github/workflows/ci.yml            |  2 +-
 .gitignore                          |  2 ++
 scalpr/adapters/__init__.py         |  0
 scalpr/domain/contracts.py          | 32 +++++++++++++++++++++++++++++
 scalpr/engine/__init__.py           |  0
 scalpr/market_data/historical.py    |  4 ++--
 scalpr/risk/session_guard.py        |  6 +++---
 tests/unit/test_import_contracts.py | 41 +++++++++++++++++++++++++++++++++++++
 8 files changed, 81 insertions(+), 6 deletions(-)
```

## Full diff
```diff
diff --git a/.github/workflows/ci.yml b/.github/workflows/ci.yml
index 3f59385..6f52818 100644
--- a/.github/workflows/ci.yml
+++ b/.github/workflows/ci.yml
@@ -21,21 +21,21 @@ jobs:

       - name: Install
         run: |
           python -m pip install --upgrade pip
           pip install -e ".[dev]"

       - name: Lint (ruff)
         run: ruff check scalpr tests

       - name: Architecture contracts (import-linter)
-        run: lint-imports --config pyproject.toml
+        run: lint-imports --config pyproject.toml --no-cache

       - name: Unit + contract tests with coverage gate
         run: >
           pytest tests/unit tests/contract -q
           --cov=scalpr
           -p no:cacheprovider

   frontend:
     runs-on: ubuntu-latest
     timeout-minutes: 15
diff --git a/.gitignore b/.gitignore
index e810465..d7c42bd 100644
--- a/.gitignore
+++ b/.gitignore
@@ -48,10 +48,12 @@ node_modules/
 .vite/

 # OS
 .DS_Store
 Thumbs.db

 # IDE
 .idea/
 .vscode/
 *.swp
+
+.import_linter_cache/
diff --git a/scalpr/adapters/__init__.py b/scalpr/adapters/__init__.py
new file mode 100644
index 0000000..e69de29
diff --git a/scalpr/domain/contracts.py b/scalpr/domain/contracts.py
index 50da361..48ee7b8 100644
--- a/scalpr/domain/contracts.py
+++ b/scalpr/domain/contracts.py
@@ -87,20 +87,52 @@ class ResolverProtocol(Protocol):

     def wire_segment_of(self, symbol: str, exchange: str) -> str:
         """Get the wire-format segment string for an instrument."""
         ...

     def instrument_kind_of(self, symbol: str, exchange: str) -> str:
         """Get the instrument kind (EQ, FUT, OPT, etc.) for an instrument."""
         ...


+@runtime_checkable
+class ExecutionGatewayProtocol(Protocol):
+    """Outward port for order placement and position enquiry.
+
+    Consumers in risk/, oms/ and strategy/ depend on this, never on a
+    concrete broker adapter — the broker is a replaceable detail.
+    """
+
+    def get_positions(self) -> list[Any]:
+        """Return current broker positions."""
+        ...
+
+    def place_order(self, order: Any) -> str:
+        """Submit an order; return the broker's order id."""
+        ...
+
+
+@runtime_checkable
+class HistoricalSourceProtocol(Protocol):
+    """Outward port for historical candle retrieval."""
+
+    def get_historical(
+        self,
+        symbol: str,
+        exchange: str,
+        timeframe: str,
+        lookback_days: int,
+    ) -> list[dict[str, Any]]:
+        """Return raw historical candles for the given instrument."""
+        ...
+
+
 @dataclass(frozen=True)
 class Quote:
     """Canonical market quote model with all Dhan quote fields.

     Returned by Gateway.quote() and InstrumentHandle.quote().
     """

     symbol: str
     exchange: str
     ltp: Decimal
diff --git a/scalpr/engine/__init__.py b/scalpr/engine/__init__.py
new file mode 100644
index 0000000..e69de29
diff --git a/scalpr/market_data/historical.py b/scalpr/market_data/historical.py
index be73cf3..77eac04 100644
--- a/scalpr/market_data/historical.py
+++ b/scalpr/market_data/historical.py
@@ -1,22 +1,22 @@
 from __future__ import annotations

 from datetime import datetime

-from scalpr.adapters.dhan.client import DhanClient
+from scalpr.domain.contracts import HistoricalSourceProtocol
 from scalpr.domain.tick import OHLCV, Tick


 class HistoricalLoader:
     """Loads historical OHLCV candles from the broker."""

-    def __init__(self, client: DhanClient):
+    def __init__(self, client: HistoricalSourceProtocol):
         self.client = client

     def load_history(self, symbol: str, timeframe: str, lookback_days: int) -> list[OHLCV]:
         """Fetch historical bars from DhanHQ. (Mocked implementation for local run)."""
         # In actual production, calls REST client of the gateway and normalizes to list[OHLCV]
         return []


 class SeamStitcher:
     """Stitches historical and live data, preventing overlap and gaps."""
diff --git a/scalpr/risk/session_guard.py b/scalpr/risk/session_guard.py
index 3dc80a8..d22435d 100644
--- a/scalpr/risk/session_guard.py
+++ b/scalpr/risk/session_guard.py
@@ -1,28 +1,28 @@
 from __future__ import annotations

 import logging
 from datetime import datetime, timedelta, timezone
 from decimal import Decimal

-from scalpr.adapters.dhan.client import DhanClient
-from scalpr.domain.order import Order, OrderSide, OrderType
+from scalpr.domain.contracts import ExecutionGatewayProtocol
+from scalpr.domain.order import Order, OrderSide
 from scalpr.domain.position import PositionSide

 logger = logging.getLogger(__name__)
 IST = timezone(timedelta(hours=5, minutes=30))


 class SessionGuard:
     """Tracks consecutive session losses and manages IST intraday square-off times."""

-    def __init__(self, gateway: DhanClient, max_losses: int = 3) -> None:
+    def __init__(self, gateway: ExecutionGatewayProtocol, max_losses: int = 3) -> None:
         self._client = gateway
         self.max_losses = max_losses
         self.consecutive_losses = 0
         self.halted = False
         self._warned_nse = False
         self._warned_mcx = False
         self._squared_off_nse = False
         self._squared_off_mcx = False

     def record_pnl(self, pnl: Decimal) -> None:
diff --git a/tests/unit/test_import_contracts.py b/tests/unit/test_import_contracts.py
new file mode 100644
index 0000000..dbf2a11
--- /dev/null
+++ b/tests/unit/test_import_contracts.py
@@ -0,0 +1,41 @@
+"""Architectural guard: the import-linter contracts must actually pass.
+
+`lint-imports` caches its import graph in `.import_linter_cache/`. A stale
+cache makes it report KEPT for contracts that are in fact broken, which is
+worse than having no guard at all. This test always runs with --no-cache.
+"""
+
+import subprocess
+import sys
+from pathlib import Path
+
+REPO_ROOT = Path(__file__).resolve().parents[2]
+
+# The console script, not `python -m importlinter.cli` — that module has no
+# __main__ hook, exits 0 and prints nothing, which would make this guard pass
+# vacuously forever. Resolving it next to sys.executable keeps it venv-correct.
+LINT_IMPORTS = Path(sys.executable).parent / "lint-imports"
+
+
+def test_lint_imports_executable_is_present():
+    """If the console script moves, the guard below must fail loudly, not skip."""
+    assert LINT_IMPORTS.exists(), f"lint-imports not found at {LINT_IMPORTS}"
+
+
+def test_import_linter_contracts_pass_without_cache():
+    result = subprocess.run(
+        [str(LINT_IMPORTS), "--config", "pyproject.toml", "--no-cache"],
+        cwd=REPO_ROOT,
+        capture_output=True,
+        text=True,
+    )
+    output = result.stdout + result.stderr
+    # A silent success is not a success — it means nothing was evaluated.
+    assert "Contracts:" in output, (
+        "lint-imports produced no contract report; the guard would be vacuous:\n"
+        + output
+    )
+    assert result.returncode == 0, (
+        "import-linter contracts are broken (run with --no-cache to reproduce):\n"
+        + output
+    )
```

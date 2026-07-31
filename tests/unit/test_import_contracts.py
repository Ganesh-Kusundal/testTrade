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

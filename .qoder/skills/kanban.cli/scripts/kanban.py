#!/usr/bin/env python3
"""kanban.cli — living project board and digest.

Maintains .kanban/CONTEXT.md, a structured, always-current view of the project:
architecture & components, tasks and their status, test failures, drift since
the previous scan, recent commits, module dependencies, data flows, deps and
technical debt.

Truth is split in two:
  - curated  : .kanban/board.json  (tasks, project summary, flows, component
               descriptions) — edited via `task` commands or by hand.
  - derived  : .kanban/scan.json   (file index, drift, git, tests, import
               graph, dependency lists, graphify graph status) — recomputed
               by `scan`.

`render` combines both into .kanban/CONTEXT.md. `update` = scan + render.

Stdlib only. Runs with any python3 >= 3.11 (tomllib optional, degrades).
Every evidence source degrades gracefully: missing git / pytest cache /
pyproject never crashes the tool — sections render an honest "unavailable".

Exit codes: 0 ok, 1 error, 2 board validation failure.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

VERSION = "1.2.0"

# Directories pruned from the file inventory (any dot-directory is also pruned).
EXCLUDE_DIRS = {
    "node_modules", "__pycache__", "dist", "build", "graphify-out",
}
# Pruned only when directly under the project root (e.g. frontend/src/data stays).
ROOT_EXCLUDE_DIRS = {"data", "runtime-dev"}
EXCLUDE_FILES = {".DS_Store", ".coverage", ".stderr.txt"}

TYPE_PREFIX = {"task": "T", "bug": "B", "feature": "F", "debt": "D", "risk": "R"}
VALID_TYPES = set(TYPE_PREFIX)
VALID_STATUSES = {"planned", "backlog", "in_progress", "blocked", "done"}

# Render caps — keep the digest inside a small token budget.
CAP_FAILING_TESTS = 15
CAP_DRIFT_LINES = 20
CAP_COMMITS = 8
CAP_COMPLETED = 10
CAP_STALE_FILES = 10
CAP_HUBS = 8

# Extensions graphify tracks — used to flag new files missing from the graph.
GRAPH_TRACKED_EXTS = {".py", ".ts", ".tsx", ".js", ".jsx", ".md"}

QUERY_SECTIONS = ("tasks", "tests", "drift", "commits", "imports", "deps", "components",
                  "graphify")


# ── helpers ──────────────────────────────────────────────────────────────


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def find_root(explicit: str | None) -> Path:
    """Project root = --root if given, else walk up from this script, then CWD,
    looking for pyproject.toml."""
    if explicit:
        return Path(explicit).resolve()
    for start in (Path(__file__).resolve().parent, Path.cwd()):
        for candidate in (start, *start.parents):
            if (candidate / "pyproject.toml").exists():
                return candidate
    return Path.cwd()


def kanban_dir(root: Path) -> Path:
    return root / ".kanban"


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-kanban-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def save_json(path: Path, data: object) -> None:
    atomic_write(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def load_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


# ── board ────────────────────────────────────────────────────────────────


def empty_board() -> dict:
    return {"version": 1, "project_summary": "", "tasks": [], "flows": {}, "components": {}}


def load_board(root: Path) -> dict:
    board = load_json(kanban_dir(root) / "board.json")
    return board if isinstance(board, dict) else empty_board()


def save_board(root: Path, board: dict) -> None:
    save_json(kanban_dir(root) / "board.json", board)


def validate_board(board: dict) -> list[str]:
    """Return list of problems (empty = valid)."""
    problems: list[str] = []
    if not isinstance(board.get("tasks"), list):
        return ["board.tasks is not a list"]
    seen: set[str] = set()
    for t in board["tasks"]:
        tid = t.get("id", "?")
        if tid in seen:
            problems.append(f"duplicate task id {tid}")
        seen.add(tid)
        if t.get("type") not in VALID_TYPES:
            problems.append(f"{tid}: invalid type {t.get('type')!r}")
        if t.get("status") not in VALID_STATUSES:
            problems.append(f"{tid}: invalid status {t.get('status')!r}")
        if not str(t.get("title", "")).strip():
            problems.append(f"{tid}: empty title")
        prefix = TYPE_PREFIX.get(t.get("type", ""), "")
        if prefix and not re.fullmatch(rf"{prefix}-\d+", tid):
            problems.append(f"{tid}: id does not match type prefix {prefix}-NNN")
    for key in ("flows", "components"):
        if not isinstance(board.get(key, {}), dict):
            problems.append(f"board.{key} is not an object")
    return problems


def next_task_id(board: dict, task_type: str) -> str:
    prefix = TYPE_PREFIX[task_type]
    highest = 0
    for t in board["tasks"]:
        m = re.fullmatch(rf"{prefix}-(\d+)", t.get("id", ""))
        if m:
            highest = max(highest, int(m.group(1)))
    return f"{prefix}-{highest + 1:03d}"


# ── scan pipeline ────────────────────────────────────────────────────────


def file_inventory(root: Path) -> dict[str, list]:
    """Relative path -> [mtime, size] for every tracked file."""
    index: dict[str, list] = {}
    for dirpath, dirnames, filenames in os.walk(root):
        at_root = Path(dirpath) == root
        dirnames[:] = sorted(
            d for d in dirnames
            if not d.startswith(".") and d not in EXCLUDE_DIRS and not d.endswith(".egg-info")
            and not (at_root and d in ROOT_EXCLUDE_DIRS)
        )
        for name in filenames:
            if name in EXCLUDE_FILES:
                continue
            full = Path(dirpath) / name
            rel = full.relative_to(root).as_posix()
            try:
                st = full.stat()
            except OSError:
                continue
            index[rel] = [round(st.st_mtime, 3), st.st_size]
    return index


def compute_drift(previous: dict | None, current: dict[str, list]) -> dict:
    if not previous:
        return {"first_scan": True, "added": [], "removed": [], "modified": []}
    prev_index = previous.get("index", {})
    added = sorted(set(current) - set(prev_index))
    removed = sorted(set(prev_index) - set(current))
    modified = sorted(
        p for p in set(current) & set(prev_index) if current[p] != prev_index[p]
    )
    return {"first_scan": False, "added": added, "removed": removed, "modified": modified}


def git_info(root: Path) -> dict:
    def run(*args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=root, capture_output=True, text=True, timeout=10, check=True
        ).stdout
    try:
        log = run("log", "--oneline", f"-{CAP_COMMITS}")
        porcelain = run("status", "--porcelain")
        return {
            "available": True,
            "commits": [line for line in log.splitlines() if line.strip()],
            "uncommitted": len([line for line in porcelain.splitlines() if line.strip()]),
        }
    except (OSError, subprocess.SubprocessError):
        return {"available": False, "commits": [], "uncommitted": 0}


def test_results(root: Path) -> dict:
    cache = root / ".pytest_cache" / "v" / "cache" / "lastfailed"
    data = load_json(cache)
    if data is None:
        return {"available": False, "failing": 0, "tests": [], "as_of": None}
    # Filter out phantom entries: test IDs whose source file no longer exists
    # on disk (e.g. after files are deleted/moved). Without this, the failing
    # count lies about the current state of the suite.
    live_tests = []
    for test_id in data:
        file_part = test_id.split("::", 1)[0]
        if (root / file_part).is_file():
            live_tests.append(test_id)
    live_tests.sort()
    as_of = None
    try:
        as_of = datetime.fromtimestamp(cache.stat().st_mtime, timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
    except OSError:
        pass
    return {"available": True, "failing": len(live_tests), "tests": live_tests[:CAP_FAILING_TESTS],
            "as_of": as_of, "phantom_filtered": len(data) - len(live_tests)}


def import_graph(root: Path, package: str = "scalpr") -> dict[str, list[str]]:
    """Top-level module -> sorted cross-module imports within `package`."""
    pkg_dir = root / package
    graph: dict[str, set[str]] = {}
    if not pkg_dir.is_dir():
        return {}
    for py in sorted(pkg_dir.rglob("*.py")):
        rel_parts = py.relative_to(pkg_dir).with_suffix("").parts
        if len(rel_parts) < 2:  # files directly under the package root
            continue
        source_top = rel_parts[0]
        # package path containing this file (for resolving relative imports)
        containing = [package, *rel_parts[:-1]]
        try:
            tree = ast.parse(py.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        targets: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    targets.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.level == 0:
                    if node.module:
                        targets.add(node.module)
                else:
                    base = containing[: len(containing) - node.level + 1]
                    mod = node.module.split(".") if node.module else []
                    targets.add(".".join(base + mod))
        for target in targets:
            parts = target.split(".")
            if parts[0] == package and len(parts) > 1 and parts[1] != source_top:
                graph.setdefault(source_top, set()).add(f"{package}.{parts[1]}")
        graph.setdefault(source_top, set())
    return {f"{package}.{k}": sorted(v) for k, v in sorted(graph.items())}


def dependency_lists(root: Path) -> dict:
    deps: dict = {"runtime": [], "dev": [], "frontend": []}
    try:
        import tomllib
        project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8")).get(
            "project", {}
        )
        deps["runtime"] = list(project.get("dependencies", []))
        deps["dev"] = list(project.get("optional-dependencies", {}).get("dev", []))
    except Exception:  # tomllib missing, file absent, or TOML unparseable — degrade
        pass
    pkg = load_json(root / "frontend" / "package.json")
    if isinstance(pkg, dict):
        deps["frontend"] = sorted(pkg.get("dependencies", {}))
    return deps


def graphify_info(root: Path, index: dict[str, list]) -> dict:
    """Read-only status of the graphify knowledge graph: size, hub nodes, and
    staleness versus the current file inventory. Never rebuilds anything —
    reading graph.json takes milliseconds; degrades to available=False."""
    graph_path = root / "graphify-out" / "graph.json"
    graph = load_json(graph_path)
    if not isinstance(graph, dict) or not isinstance(graph.get("nodes"), list):
        return {"available": False}
    try:
        built_ts = graph_path.stat().st_mtime
    except OSError:
        return {"available": False}
    nodes = graph["nodes"]
    communities = {n.get("community") for n in nodes if n.get("community") is not None}
    sources = {n.get("source_file") for n in nodes if n.get("source_file")}
    modified = sorted(p for p in sources if p in index and index[p][0] > built_ts)
    deleted = sorted(p for p in sources if p not in index)
    new = sorted(
        p for p in index
        if p not in sources and Path(p).suffix in GRAPH_TRACKED_EXTS
    )
    analysis = load_json(root / "graphify-out" / ".graphify_analysis.json")
    gods = analysis.get("gods", []) if isinstance(analysis, dict) else []
    hubs = [{"label": g.get("label", "?"), "degree": g.get("degree", 0)}
            for g in gods[:CAP_HUBS]]
    return {
        "available": True,
        "built": datetime.fromtimestamp(built_ts, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "nodes": len(nodes),
        "edges": len(graph.get("links", [])),
        "communities": len(communities),
        "hubs": hubs,
        "fresh": not (modified or deleted or new),
        "stale": {
            "modified": modified[:CAP_STALE_FILES], "modified_total": len(modified),
            "deleted": deleted[:CAP_STALE_FILES], "deleted_total": len(deleted),
            "new": new[:CAP_STALE_FILES], "new_total": len(new),
        },
    }


def graphify_is_stale(root: Path) -> bool:
    """Lightweight staleness check: True iff the graphify graph exists but is
    behind the current file inventory (modified/deleted/new files). Used by
    `task status` to remind the agent to refresh the graph after closing a
    task — per AGENTS.md, a stale graphify must be auto-refreshed before
    continuing."""
    index = file_inventory(root)
    info = graphify_info(root, index)
    if not info.get("available"):
        return False  # nothing to refresh
    return not info.get("fresh", True)


def component_counts(index: dict[str, list], board: dict, root: Path) -> dict[str, dict]:
    """Component name -> {files, description}. Union of curated components and
    scalpr/* subpackages discovered on disk (flagged when undescribed)."""
    curated: dict[str, str] = board.get("components", {})
    names = set(curated)
    for rel in index:
        parts = rel.split("/")
        if parts[0] == "scalpr" and len(parts) > 2:
            names.add(f"scalpr/{parts[1]}")
    out: dict[str, dict] = {}
    for name in sorted(names):
        prefix = name + "/"
        count = sum(1 for rel in index if rel == name or rel.startswith(prefix))
        desc = curated.get(name) or "(no description — add via board.json)"
        out[name] = {"files": count, "description": desc}
    return out


def do_scan(root: Path) -> dict:
    previous = load_json(kanban_dir(root) / "scan.json")
    index = file_inventory(root)
    board = load_board(root)
    scan = {
        "version": 1,
        "timestamp": now_iso(),
        "index": index,
        "drift": compute_drift(previous, index),
        "git": git_info(root),
        "tests": test_results(root),
        "imports": import_graph(root),
        "deps": dependency_lists(root),
        "components": component_counts(index, board, root),
        "graphify": graphify_info(root, index),
    }
    save_json(kanban_dir(root) / "scan.json", scan)
    return scan


# ── render ───────────────────────────────────────────────────────────────


def task_line(t: dict) -> str:
    return f"- {t['id']} [{t['type']}/{t['status']}] {t['title']}"


def render_context(root: Path, board: dict, scan: dict) -> str:
    tasks = board.get("tasks", [])
    lines: list[str] = []
    add = lines.append

    def section(title: str, body: list[str]) -> None:
        add(f"## {title}")
        lines.extend(body if body else ["- none"])
        add("")

    add(f"# {root.name} — kanban digest ({scan.get('timestamp', now_iso())})")
    add("")
    summary = board.get("project_summary", "").strip()
    if summary:
        add(summary)
        add("")

    by_status = lambda *st: [task_line(t) for t in tasks if t["status"] in st]  # noqa: E731
    section("Work in progress", by_status("in_progress"))
    section("Blocked", by_status("blocked"))
    section("Planned / backlog", by_status("planned", "backlog"))

    done = [t for t in tasks if t["status"] == "done"]
    done.sort(key=lambda t: t.get("updated", ""), reverse=True)
    completed = []
    for t in done[:CAP_COMPLETED]:
        when = (t.get("updated") or "")[:10]
        suffix = f" (completed {when})" if when else ""
        completed.append(task_line(t) + suffix)
    section("Recently completed", completed)

    tests = scan.get("tests", {})
    if not tests.get("available"):
        body = ["- no pytest cache found — run the test suite to populate"]
    elif tests["failing"] == 0:
        body = ["- last pytest run: 0 failing"]
    else:
        as_of = f" (as of {tests['as_of']})" if tests.get("as_of") else ""
        body = [f"- last pytest run: {tests['failing']} failing{as_of}"]
        body += [f"  - {t}" for t in tests["tests"]]
        extra = tests["failing"] - len(tests["tests"])
        if extra > 0:
            body.append(f"  - … +{extra} more")
    section("Tests", body)

    drift = scan.get("drift", {})
    if drift.get("first_scan"):
        body = ["- first scan — no previous index to compare against"]
    else:
        entries = (
            [("added", p) for p in drift.get("added", [])]
            + [("removed", p) for p in drift.get("removed", [])]
            + [("modified", p) for p in drift.get("modified", [])]
        )
        body = [f"- {kind}: {p}" for kind, p in entries[:CAP_DRIFT_LINES]]
        if len(entries) > CAP_DRIFT_LINES:
            body.append(f"- … +{len(entries) - CAP_DRIFT_LINES} more")
    section("Drift since previous scan", body)

    git = scan.get("git", {})
    if not git.get("available"):
        body = ["- git unavailable"]
    else:
        body = [f"- {c}" for c in git["commits"]] or ["- no commits"]
        body += ["", f"({git['uncommitted']} uncommitted changes in working tree)"]
    section("Recent commits", body)

    components = scan.get("components", {})
    body = [
        f"- **{name}** ({info['files']} files): {info['description']}"
        for name, info in components.items()
    ]
    section("Architecture & components", body)

    imports = scan.get("imports", {})
    body = [f"- {mod} → {', '.join(targets)}" for mod, targets in imports.items() if targets]
    section("Module dependencies (scalpr, module → imports)", body)

    gf = scan.get("graphify", {})
    if not gf.get("available"):
        body = ["- knowledge graph not built — run `/graphify` for deep-structure tracking"]
    else:
        body = [f"- {gf['nodes']} nodes · {gf['edges']} edges · {gf['communities']} "
                f"communities (built {gf['built']})"]
        if gf.get("hubs"):
            body.append("- hubs: " + ", ".join(
                f"{h['label']}({h['degree']})" for h in gf["hubs"]))
        if gf.get("fresh"):
            body.append("- graph is in sync with the file inventory")
        else:
            stale = gf.get("stale", {})
            counts = [f"{stale.get(f'{kind}_total', 0)} {kind}"
                      for kind in ("modified", "deleted", "new")
                      if stale.get(f"{kind}_total", 0)]
            body.append(f"- STALE ({', '.join(counts)} since build) — "
                        "refresh with `/graphify update`")
            body += [f"  - modified: {p}" for p in stale.get("modified", [])]
            # Auto-refresh directive: per AGENTS.md, a stale graphify must be
            # refreshed before continuing. The agent reads CONTEXT.md at
            # session start; this instruction makes the next action
            # unambiguous. `task status <id> done` also emits the reminder
            # on stderr when it closes a task while the graph is stale.
            body.append(
                "- AUTO-REFRESH: run `/graphify update` now, then re-run "
                "`kanban.py update` to refresh this digest."
            )
    section("Knowledge graph (graphify)", body)

    flows = board.get("flows", {})
    section("Data / execution flows", [f"- **{k}**: {v}" for k, v in flows.items()])

    deps = scan.get("deps", {})
    body = [f"- {group}: {', '.join(items)}" for group, items in deps.items() if items]
    section("Dependencies", body or ["- unavailable"])

    debt = [task_line(t) for t in tasks if t["type"] in ("debt", "risk") and t["status"] != "done"]
    section("Technical debt & risks", debt)

    add("---")
    add(
        f"*Generated by kanban.cli v{VERSION}. Refresh: "
        "`python3 .qoder/skills/kanban.cli/scripts/kanban.py update`. Do not edit by hand.*"
    )
    add("")
    return "\n".join(lines)


def do_render(root: Path) -> Path:
    board = load_board(root)
    problems = validate_board(board)
    if problems:
        for p in problems:
            print(f"board.json invalid: {p}", file=sys.stderr)
        raise SystemExit(2)
    scan = load_json(kanban_dir(root) / "scan.json")
    if scan is None:
        print("no scan.json — running scan first", file=sys.stderr)
        scan = do_scan(root)
    out = kanban_dir(root) / "CONTEXT.md"
    atomic_write(out, render_context(root, board, scan))
    return out


# ── task commands ────────────────────────────────────────────────────────


def cmd_task_add(root: Path, task_type: str, title: str, status: str) -> int:
    board = load_board(root)
    tid = next_task_id(board, task_type)
    now = now_iso()
    board["tasks"].append(
        {"id": tid, "type": task_type, "status": status, "title": title,
         "created": now, "updated": now}
    )
    problems = validate_board(board)
    if problems:
        for p in problems:
            print(f"refusing to save: {p}", file=sys.stderr)
        return 2
    save_board(root, board)
    print(f"added {tid} [{task_type}/{status}] {title}")
    return 0


def cmd_task_status(root: Path, tid: str, status: str) -> int:
    board = load_board(root)
    found = False
    for t in board["tasks"]:
        if t["id"] == tid:
            t["status"] = status
            t["updated"] = now_iso()
            found = True
            break
    if not found:
        print(f"no task with id {tid}", file=sys.stderr)
        return 1
    save_board(root, board)
    print(f"{tid} → {status}")

    # Auto-graphify refresh on task completion.
    # Per AGENTS.md session-start protocol: "If kanban reports graphify STALE,
    # auto-run `/graphify update` to refresh the knowledge graph before
    # continuing." Closing a task is the natural trigger to re-check — the
    # agent just changed the board, so the file inventory may have moved.
    if status == "done" and graphify_is_stale(root):
        print(
            "graphify STALE — run `/graphify update` (or "
            "`python3 .qoder/skills/kanban.cli/scripts/kanban.py update` "
            "after the refresh) to keep the knowledge graph in sync.",
            file=sys.stderr,
        )
    return 0


def cmd_task_list(root: Path, status: str | None, as_json: bool) -> int:
    tasks = load_board(root).get("tasks", [])
    if status:
        tasks = [t for t in tasks if t["status"] == status]
    if as_json:
        print(json.dumps(tasks, indent=2, ensure_ascii=False))
    else:
        for t in tasks:
            print(task_line(t))
        if not tasks:
            print("(no tasks)")
    return 0


# ── query / selfcheck ────────────────────────────────────────────────────


def cmd_query(root: Path, section: str) -> int:
    scan = load_json(kanban_dir(root) / "scan.json")
    if section == "tasks":
        data: object = load_board(root).get("tasks", [])
    elif scan is None:
        print("no scan.json — run `scan` first", file=sys.stderr)
        return 1
    else:
        data = scan.get(section)
    print(json.dumps(data, indent=2, ensure_ascii=False))
    return 0


CONTRACT_SECTIONS = [
    "## Work in progress", "## Blocked", "## Planned / backlog", "## Recently completed",
    "## Tests", "## Drift since previous scan", "## Recent commits",
    "## Architecture & components", "## Module dependencies (scalpr, module → imports)",
    "## Knowledge graph (graphify)",
    "## Data / execution flows", "## Dependencies", "## Technical debt & risks",
]


def build_fixture(root: Path) -> None:
    """Tiny synthetic project used by selfcheck and the test suite."""
    (root / "scalpr" / "domain").mkdir(parents=True)
    (root / "scalpr" / "api").mkdir(parents=True)
    (root / "scalpr" / "__init__.py").write_text("", encoding="utf-8")
    (root / "scalpr" / "domain" / "__init__.py").write_text("", encoding="utf-8")
    (root / "scalpr" / "domain" / "order.py").write_text("X = 1\n", encoding="utf-8")
    (root / "scalpr" / "api" / "__init__.py").write_text("", encoding="utf-8")
    (root / "scalpr" / "api" / "main.py").write_text(
        "from scalpr.domain import order\nfrom ..domain.order import X\n", encoding="utf-8"
    )
    (root / "pyproject.toml").write_text(
        '[project]\nname = "fixture"\ndependencies = ["requests>=2"]\n'
        '[project.optional-dependencies]\ndev = ["pytest>=7"]\n',
        encoding="utf-8",
    )
    cache = root / ".pytest_cache" / "v" / "cache"
    cache.mkdir(parents=True)
    (cache / "lastfailed").write_text('{"tests/test_x.py::test_a": true}', encoding="utf-8")
    # The lastfailed entry points at this file — must exist so the phantom
    # filter doesn't drop it (see test_tests_section_reads_lastfailed).
    (root / "tests").mkdir(exist_ok=True)
    (root / "tests" / "test_x.py").write_text("def test_a(): pass\n", encoding="utf-8")
    board = empty_board()
    board["project_summary"] = "Fixture project."
    board["flows"] = {"demo": "a -> b"}
    board["components"] = {"scalpr/domain": "domain models", "scalpr/api": "api layer"}
    now = now_iso()
    board["tasks"] = [
        {"id": "T-001", "type": "task", "status": "in_progress", "title": "fixture wip",
         "created": now, "updated": now},
        {"id": "D-001", "type": "debt", "status": "backlog", "title": "fixture debt",
         "created": now, "updated": now},
    ]
    (root / ".kanban").mkdir()
    save_json(root / ".kanban" / "board.json", board)
    # minimal graphify output covering every fixture .py file (graph is fresh)
    gout = root / "graphify-out"
    gout.mkdir()
    # Include both scalpr/ and tests/ files so the graph covers every source
    # the fixture creates (including the lastfailed target tests/test_x.py).
    py_files = sorted(
        p.relative_to(root).as_posix()
        for p in list((root / "scalpr").rglob("*.py")) + list((root / "tests").rglob("*.py"))
    )
    gnodes = [{"id": f"n{i}", "label": Path(rel).stem, "source_file": rel, "community": 0}
              for i, rel in enumerate(py_files)]
    save_json(gout / "graph.json",
              {"nodes": gnodes, "links": [{"source": "n0", "target": "n1"}],
               "built_at_commit": "fixture"})
    save_json(gout / ".graphify_analysis.json",
              {"gods": [{"id": "n0", "label": "Order", "degree": 5}]})


def cmd_selfcheck(real_root: Path) -> int:
    failures: list[str] = []

    def check(cond: bool, label: str) -> None:
        print(f"  [{'ok' if cond else 'FAIL'}] {label}")
        if not cond:
            failures.append(label)

    print("selfcheck: real board validation")
    board_path = kanban_dir(real_root) / "board.json"
    if board_path.exists():
        problems = validate_board(load_board(real_root))
        check(not problems, f"board.json schema valid ({', '.join(problems) or 'no problems'})")
    else:
        print("  [skip] no board.json yet")

    print("selfcheck: end-to-end in temp fixture")
    with tempfile.TemporaryDirectory() as tmp:
        froot = Path(tmp)
        build_fixture(froot)
        do_scan(froot)
        out = do_render(froot)
        text = out.read_text(encoding="utf-8")
        for header in CONTRACT_SECTIONS:
            check(header in text, f"section present: {header}")
        check("- T-001 [task/in_progress] fixture wip" in text, "WIP task rendered")
        check("- D-001 [debt/backlog] fixture debt" in text, "debt task rendered")
        check("scalpr.api → scalpr.domain" in text, "import graph edge rendered")
        check("1 failing" in text, "failing test count rendered")
        check("runtime: requests>=2" in text, "runtime deps rendered")
        check("Order(5)" in text, "graphify hub rendered")
        check("graph is in sync" in text, "graphify freshness rendered")
        # second scan after modifying a file must report drift + graph staleness
        target = froot / "scalpr" / "api" / "main.py"
        target.write_text(target.read_text(encoding="utf-8") + "Y = 2\n", encoding="utf-8")
        os.utime(target, (target.stat().st_atime, target.stat().st_mtime + 5))
        scan2 = do_scan(froot)
        check("scalpr/api/main.py" in scan2["drift"]["modified"], "drift detects modified file")
        check("scalpr/api/main.py" in scan2["graphify"]["stale"]["modified"],
              "graphify staleness detects modified source")

    print("PASS" if not failures else f"FAIL ({len(failures)} checks failed)")
    return 0 if not failures else 1


# ── CLI ──────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="kanban.py", description=__doc__.splitlines()[0])
    parser.add_argument("--root", help="project root (default: auto-detect via pyproject.toml)")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("scan", help="collect evidence into .kanban/scan.json")
    sub.add_parser("render", help="render .kanban/CONTEXT.md from board + scan")
    sub.add_parser("update", help="scan + render")
    sub.add_parser("selfcheck", help="validate board and run end-to-end fixture check")

    p_query = sub.add_parser("query", help="print a machine-readable section as JSON")
    p_query.add_argument("section", choices=QUERY_SECTIONS)

    p_task = sub.add_parser("task", help="manage board tasks")
    task_sub = p_task.add_subparsers(dest="task_command", required=True)
    p_add = task_sub.add_parser("add", help="add a task with an auto-assigned id")
    p_add.add_argument("type", choices=sorted(VALID_TYPES))
    p_add.add_argument("title")
    p_add.add_argument("--status", default="planned", choices=sorted(VALID_STATUSES))
    p_status = task_sub.add_parser("status", help="change a task's status")
    p_status.add_argument("id")
    p_status.add_argument("new_status", choices=sorted(VALID_STATUSES))
    p_list = task_sub.add_parser("list", help="list tasks")
    p_list.add_argument("--status", choices=sorted(VALID_STATUSES))
    p_list.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)
    root = find_root(args.root)

    try:
        if args.command == "scan":
            do_scan(root)
            print(f"scan written to {kanban_dir(root) / 'scan.json'}")
            return 0
        if args.command == "render":
            out = do_render(root)
            print(f"rendered {out}")
            return 0
        if args.command == "update":
            do_scan(root)
            out = do_render(root)
            print(f"updated {out}")
            return 0
        if args.command == "selfcheck":
            return cmd_selfcheck(root)
        if args.command == "query":
            return cmd_query(root, args.section)
        if args.command == "task":
            if args.task_command == "add":
                return cmd_task_add(root, args.type, args.title, args.status)
            if args.task_command == "status":
                return cmd_task_status(root, args.id, args.new_status)
            if args.task_command == "list":
                return cmd_task_list(root, args.status, args.json)
    except SystemExit:
        raise
    except Exception as exc:  # honest failure, non-zero exit
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

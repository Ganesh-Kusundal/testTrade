#!/usr/bin/env python3
"""Standalone tests for kanban.py. Run directly:

    python3 .qoder/skills/kanban.cli/scripts/test_kanban.py

Lives outside the project's tests/ tree on purpose: project pytest
(testpaths=["tests"], coverage fail_under=80) must never collect it.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kanban  # noqa: E402


class KanbanFixtureTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        kanban.build_fixture(self.root)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_scan_render_produces_all_contract_sections(self) -> None:
        kanban.do_scan(self.root)
        out = kanban.do_render(self.root)
        text = out.read_text(encoding="utf-8")
        for header in kanban.CONTRACT_SECTIONS:
            self.assertIn(header, text)
        self.assertIn("Do not edit by hand.", text)

    def test_import_graph_resolves_absolute_and_relative(self) -> None:
        graph = kanban.import_graph(self.root)
        self.assertEqual(graph.get("scalpr.api"), ["scalpr.domain"])
        self.assertEqual(graph.get("scalpr.domain"), [])

    def test_drift_detects_added_removed_modified(self) -> None:
        kanban.do_scan(self.root)
        target = self.root / "scalpr" / "api" / "main.py"
        target.write_text(target.read_text(encoding="utf-8") + "Y = 2\n", encoding="utf-8")
        os.utime(target, (target.stat().st_atime, target.stat().st_mtime + 5))
        (self.root / "scalpr" / "api" / "new_module.py").write_text("Z = 3\n", encoding="utf-8")
        (self.root / "scalpr" / "domain" / "order.py").unlink()
        scan = kanban.do_scan(self.root)
        self.assertIn("scalpr/api/main.py", scan["drift"]["modified"])
        self.assertIn("scalpr/api/new_module.py", scan["drift"]["added"])
        self.assertIn("scalpr/domain/order.py", scan["drift"]["removed"])

    def test_tests_section_reads_lastfailed(self) -> None:
        scan = kanban.do_scan(self.root)
        self.assertTrue(scan["tests"]["available"])
        self.assertEqual(scan["tests"]["failing"], 1)
        self.assertEqual(scan["tests"]["tests"], ["tests/test_x.py::test_a"])

    def test_lastfailed_phantom_entries_are_filtered(self) -> None:
        # Seed a lastfailed entry whose source file does not exist on disk.
        # The phantom filter must drop it so the failing count reflects
        # only tests that could actually still fail.
        cache = self.root / ".pytest_cache" / "v" / "cache" / "lastfailed"
        cache.write_text(
            '{"tests/test_x.py::test_a": true, '
            '"tests/unit/api/test_deleted.py::TestGhost::test_nope": true}',
            encoding="utf-8",
        )
        scan = kanban.do_scan(self.root)
        self.assertEqual(scan["tests"]["failing"], 1)
        self.assertEqual(scan["tests"]["tests"], ["tests/test_x.py::test_a"])
        self.assertEqual(scan["tests"]["phantom_filtered"], 1)


    def test_task_add_allocates_next_id_and_status_moves_sections(self) -> None:
        self.assertEqual(kanban.cmd_task_add(self.root, "task", "second task", "planned"), 0)
        board = kanban.load_board(self.root)
        self.assertIn("T-002", [t["id"] for t in board["tasks"]])
        self.assertEqual(kanban.cmd_task_status(self.root, "T-002", "done"), 0)
        kanban.do_render(self.root)
        text = (self.root / ".kanban" / "CONTEXT.md").read_text(encoding="utf-8")
        self.assertIn("- T-002 [task/done] second task (completed", text)
        # unknown id → error exit
        self.assertEqual(kanban.cmd_task_status(self.root, "T-999", "done"), 1)

    def test_board_validation_rejects_bad_states(self) -> None:
        board = kanban.load_board(self.root)
        board["tasks"].append({"id": "T-001", "type": "task", "status": "planned", "title": "dup"})
        self.assertTrue(any("duplicate" in p for p in kanban.validate_board(board)))
        bad = kanban.empty_board()
        bad["tasks"] = [{"id": "X-1", "type": "task", "status": "nope", "title": ""}]
        problems = kanban.validate_board(bad)
        self.assertTrue(any("invalid status" in p for p in problems))
        self.assertTrue(any("empty title" in p for p in problems))
        self.assertTrue(any("prefix" in p for p in problems))

    def test_graceful_degradation_without_evidence_sources(self) -> None:
        # remove pytest cache and pyproject; render must still succeed
        (self.root / ".pytest_cache" / "v" / "cache" / "lastfailed").unlink()
        (self.root / "pyproject.toml").unlink()
        kanban.do_scan(self.root)
        out = kanban.do_render(self.root)
        text = out.read_text(encoding="utf-8")
        self.assertIn("no pytest cache found", text)
        for header in kanban.CONTRACT_SECTIONS:
            self.assertIn(header, text)

    def test_atomic_writes_leave_no_temp_files(self) -> None:
        kanban.do_scan(self.root)
        kanban.do_render(self.root)
        leftovers = list((self.root / ".kanban").glob(".tmp-kanban-*"))
        self.assertEqual(leftovers, [])

    def test_scan_json_is_valid_and_queryable(self) -> None:
        kanban.do_scan(self.root)
        scan = json.loads((self.root / ".kanban" / "scan.json").read_text(encoding="utf-8"))
        for key in ("index", "drift", "git", "tests", "imports", "deps", "components",
                    "graphify"):
            self.assertIn(key, scan)

    def test_graphify_fresh_then_stale_after_source_change(self) -> None:
        scan = kanban.do_scan(self.root)
        gf = scan["graphify"]
        self.assertTrue(gf["available"])
        self.assertTrue(gf["fresh"])
        self.assertEqual(gf["hubs"][0], {"label": "Order", "degree": 5})
        target = self.root / "scalpr" / "api" / "main.py"
        os.utime(target, (target.stat().st_atime, target.stat().st_mtime + 5))
        (self.root / "scalpr" / "domain" / "order.py").unlink()
        (self.root / "scalpr" / "api" / "fresh_module.py").write_text("A = 1\n", encoding="utf-8")
        gf = kanban.do_scan(self.root)["graphify"]
        self.assertFalse(gf["fresh"])
        self.assertIn("scalpr/api/main.py", gf["stale"]["modified"])
        self.assertIn("scalpr/domain/order.py", gf["stale"]["deleted"])
        self.assertIn("scalpr/api/fresh_module.py", gf["stale"]["new"])
        text = kanban.do_render(self.root).read_text(encoding="utf-8")
        self.assertIn("STALE", text)
        self.assertIn("/graphify update", text)

    def test_graphify_degrades_when_graph_missing(self) -> None:
        (self.root / "graphify-out" / "graph.json").unlink()
        scan = kanban.do_scan(self.root)
        self.assertEqual(scan["graphify"], {"available": False})
        text = kanban.do_render(self.root).read_text(encoding="utf-8")
        self.assertIn("knowledge graph not built", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)

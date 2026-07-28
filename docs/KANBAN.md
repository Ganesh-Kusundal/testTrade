# kanban.cli — living project board

The project's state digest lives in `.kanban/CONTEXT.md`: tasks and their
status, failing tests, drift since last scan, recent commits, module
dependency graph, data flows, and technical debt. It is maintained by a
stdlib-only tool — full skill doc at `.qoder/skills/kanban.cli/SKILL.md`.

```
python3 .qoder/skills/kanban.cli/scripts/kanban.py <command>
```

Works with any bare `python3 ≥ 3.11` — no venv, no pip installs.

## Session starts (agents and developers)

Read `.kanban/CONTEXT.md` first. It is the fastest complete picture of what
is done, in progress, broken, and planned — before opening code or planning
changes.

## Status updates

1. **Starting work** — `task status <id> in_progress`, or
   `task add <type> "title" --status in_progress` if no task exists yet
   (type: `task|bug|feature|debt|risk` → auto-ID `T-/B-/F-/D-/R-NNN`).
2. **Hitting a blocker** — `task status <id> blocked`.
3. **Finishing work** — `task status <id> done`, then `update`.
4. **After any significant code change or commit** — run `update` so drift,
   tests, imports, and commits stay current.

## Quick reference

| I want to… | Command |
|---|---|
| Understand project state | read `.kanban/CONTEXT.md` |
| Refresh everything | `update` |
| Log new work / bug / debt / risk | `task add <type> "title"` |
| Move a task through the board | `task status <id> <status>` |
| See failing tests as JSON | `query tests` |
| See what changed since last scan | `query drift` |
| Verify the tool works | `selfcheck` |

## Rules

- Never edit `.kanban/CONTEXT.md` or `.kanban/scan.json` by hand — both are
  regenerated. Curated prose (project summary, flows, component
  descriptions) is edited in `.kanban/board.json`.
- Never invent task IDs — `task add` allocates and validates them.
- Machine-readable data comes from `query <section>`
  (`tasks|tests|drift|commits|imports|deps|components`), not from parsing
  CONTEXT.md.

# Seeding & Sync: Populating the kanban board

## Seeding the Board

The kanban board is seeded from existing project tracking files. These are
**read once** during initial seeding; after that, the board is the source of
truth.

### Primary sources (in priority order)
1. **`docs/KANBAN.md`** — Project-level kanban documentation and workflow.
2. **`AGENTS.md`** — Agent rules, including the mandated graphify-staleness
   workflow (kanban must flag when the knowledge graph is stale).
3. **`board.legacy.json`** (if present) — Archived legacy board data. Its
   `components` and `flows` entries are the curated seed source.
4. Any existing `scalpr/*` package structure — provides the file inventory
   for scan.

### Components to seed
Map to the Clean Architecture layers present in `scalpr/`:
- `config` — `scalpr/config/`
- `domain` — `scalpr/domain/`
- `execution` — `scalpr/execution/`
- `market_data` — `scalpr/market_data/`
- `observability` — `scalpr/observability/`
- `oms` — `scalpr/oms/`
- `portfolio` — `scalpr/portfolio/`
- `risk` — `scalpr/risk/`
- `scanner` — `scalpr/scanner/`
- `signals` — `scalpr/signals/`
- `simulation` — `scalpr/simulation/`
- `strategy` — `scalpr/strategy/`
- `testing` — `scalpr/testing/`
- `brokers` — `scalpr/brokers/`
- `cli` — `scalpr/cli/`
- `api` — `scalpr/api/`

Adjust descriptions from the archived `board.legacy.json` or write fresh
one-liners.

### File purposes to seed (~20 key files)
TBD per component; seed the most important entry points first (e.g.,
`scalpr/domain/`, `scalpr/execution/`, `scalpr/cli.py`, `scalpr/api/`,
`scalpr/runtime/` if present). Use the archived `board.legacy.json` flow
descriptions as a starting point.

### Flows to seed (from project docs)
Map execution paths across components:
1. **live-trading** — CLI → OMS → broker → fill → position tracking (from
   `board.legacy.json` flows)
2. **auth-refresh** — token refresh → API fail-closed
3. **api-fail-closed** — API call → graceful degradation
4. **backtest** — strategy → simulation → signals → fill

Adjust based on `board.legacy.json` and current code.

## No progress-tracker.md

This repo does **not** have a `context/progress-tracker.md`. The
`sync-tracker` command emits markdown to stdout for the agent to paste
where appropriate (e.g., a session log or a docs file created on demand).
It is a one-time paste, not a persistent auto-edit.

## Seeding workflow

1. Run `python3 .qoder/skills/kanban.cli/scripts/kanban.py init --name tradexv2`
   to create an empty `state.json`.
2. Run `python3 .../kanban.py scan` to index all `scalpr/` files.
3. Use `component add` to register each architecture layer, pulling
   descriptions from `board.legacy.json` or `docs/KANBAN.md`.
4. Use `flow add` to register the project's execution flows.
5. Use `file set-purpose` for the ~20 key files listed above.
6. Run `python3 .../kanban.py board` to generate `BOARD.md`.
7. Run `python3 .../kanban.py stale` to verify annotations.

## Common mistakes

- **Don't create new status .md files** — use cards. The board is the
  single source of truth.
- **Don't skip `scan` after edits** — staleness warnings will fire.
- **Don't put code-structure facts in kanban** — use `graphify query` for
  "how does X work?".
- **Don't edit `state.json` by hand** — use the CLI commands; they re-render
  `BOARD.md` automatically.

# kanban.cli Command Reference

All commands invoked as:
```bash
python3 .claude/skills/kanban-cli/scripts/kanban.py <command> [args]
```

## Core Commands

### `init [--name NAME]`
Initialize a new kanban board. Creates `.kanban/state.json` and `.kanban/BOARD.md`, then runs an initial scan.

```bash
python3 .claude/skills/kanban-cli/scripts/kanban.py init --name tradex-v2
```

Refuses to overwrite an existing state. Run from the project root (v2/).

### `scan [--full-tests]`
Refresh deterministic facts: file inventory + hashes, git status, test counts, dependency list.

```bash
python3 .claude/skills/kanban-cli/scripts/kanban.py scan
python3 .claude/skills/kanban-cli/scripts/kanban.py scan --full-tests
```

- Without `--full-tests`: counts test files and test functions via regex (fast, ~1-2s).
- With `--full-tests`: runs `pytest --collect-only -q` (slow, ~30s+, may fail on dirty branches).
- Prints a delta: files added/removed/changed, stale annotations.

### `status [--json]`
Agent-facing digest. ~50-80 lines, capped at 90. Shows branch, scan freshness, in-progress/blocked cards, next-up backlog, open bugs, high risks, stale annotations, recent commits, and hints.

```bash
python3 .claude/skills/kanban-cli/scripts/kanban.py status
python3 .claude/skills/kanban-cli/scripts/kanban.py status --json
```

### `board [--print]`
Regenerate or view BOARD.md.

```bash
python3 .claude/skills/kanban-cli/scripts/kanban.py board
python3 .claude/skills/kanban-cli/scripts/kanban.py board --print
```

### `check [--selftest]`
Integrity validation. Exits 0 on success, 2 on integrity failure.

```bash
python3 .claude/skills/kanban-cli/scripts/kanban.py check
python3 .claude/skills/kanban-cli/scripts/kanban.py check --selftest
```

`--selftest` runs an embedded pytest-free self-test in a temp directory.

### `stale [--json]`
Show stale file annotations (hash changed since last annotation), cards with changed files, and scan freshness warnings.

```bash
python3 .claude/skills/kanban-cli/scripts/kanban.py stale
python3 .claude/skills/kanban-cli/scripts/kanban.py stale --json
```

### `sync-tracker`
Emit a markdown block for `context/progress-tracker.md`. The agent pastes the output between `<!-- kanban:begin -->` and `<!-- kanban:end -->` markers.

```bash
python3 .claude/skills/kanban-cli/scripts/kanban.py sync-tracker
```

## Card Commands

### `card add TITLE [options]`
Create a new card. Allocates `K-NNN` automatically.

```bash
python3 .claude/skills/kanban-cli/scripts/kanban.py card add "Fix C1 race" \
  --kind bug --priority P0 --lane in_progress \
  --detail "Repro: submit order then broker push hits duplicate dedup" \
  --files src/runtime/boot.py,src/application/execution/execution_engine.py \
  --tags c1-c5,execution \
  --links K-004
```

Options: `--kind` (feature|bug|task|debt|chore, default: task), `--lane` (backlog|in_progress|blocked|review|done, default: backlog), `--priority` (P0|P1|P2|P3, default: P2), `--detail`, `--files` (comma-separated), `--tags` (comma-separated), `--links` (comma-separated card IDs), `--blocked-by`.

### `card move ID LANE [--note]`
Move a card between lanes. Appends to history.

```bash
python3 .claude/skills/kanban-cli/scripts/kanban.py card move K-001 in_progress
python3 .claude/skills/kanban-cli/scripts/kanban.py card move K-001 blocked --note "waiting on broker sandbox"
python3 .claude/skills/kanban-cli/scripts/kanban.py card move K-001 done
```

Moving to `blocked` **requires** `--note` (the reason).

### `card update ID [options]`
Update card fields.

```bash
python3 .claude/skills/kanban-cli/scripts/kanban.py card update K-001 --detail "Updated repro steps" --files src/foo.py
```

Options: `--title`, `--detail`, `--priority`, `--kind`, `--files`, `--tags`, `--links`.

### `card list [--lane LANE] [--kind KIND] [--json]`
List cards in a compact table.

```bash
python3 .claude/skills/kanban-cli/scripts/kanban.py card list
python3 .claude/skills/kanban-cli/scripts/kanban.py card list --lane in_progress
python3 .claude/skills/kanban-cli/scripts/kanban.py card list --kind bug --json
```

### `card show ID [--json]`
Show full card details including history and per-file staleness flags.

```bash
python3 .claude/skills/kanban-cli/scripts/kanban.py card show K-001
```

## File Commands

### `file set-purpose PATH PURPOSE [--component COMPONENT]`
Set the purpose annotation for a file. Stamps `annotated_at` and `annotated_hash` to the current file hash, re-anchoring staleness.

```bash
python3 .claude/skills/kanban-cli/scripts/kanban.py file set-purpose src/runtime/boot.py "Composition root + boot sequence" --component runtime
```

### `file list [--component NAME] [--unannotated] [--json]`
List files with their component, purpose, and stale marker (`*`).

```bash
python3 .claude/skills/kanban-cli/scripts/kanban.py file list
python3 .claude/skills/kanban-cli/scripts/kanban.py file list --unannotated
python3 .claude/skills/kanban-cli/scripts/kanban.py file list --component domain
```

## Component Commands

### `component add NAME [--purpose TEXT] [--paths PATHS] [--depends-on DEPS] [--notes TEXT]`
```bash
python3 .claude/skills/kanban-cli/scripts/kanban.py component add domain \
  --purpose "Domain entities + ports (no inbound imports)" \
  --paths src/tradex/domain \
  --depends-on ""
```

### `component update NAME [options]`
Update component fields: `--purpose`, `--paths`, `--depends-on`, `--notes`.

### `component list [--json]`
List all components.

## Flow Commands

### `flow add NAME [--summary TEXT] [--steps STEPS] [--files FILES]`
```bash
python3 .claude/skills/kanban-cli/scripts/kanban.py flow add order-lifecycle \
  --summary "CLI → OMS → broker → fill" \
  --steps "cli;oms;broker;fill" \
  --files src/tradex/cli.py,src/application/oms
```

### `flow list [--json]`
List all flows.

## Risk Commands

### `risk add DESC [--severity SEV] [--area AREA] [--mitigation TEXT] [--status STATUS]`
```bash
python3 .claude/skills/kanban-cli/scripts/kanban.py risk add "C1 race condition in dedup" \
  --severity high --area runtime --mitigation "Use (order_id, status) tuple"
```

### `risk update ID [options]`
Update risk fields: `--desc`, `--severity`, `--area`, `--mitigation`, `--status`.

### `risk list [--json]`
List all risks, severity-sorted.

---
name: kanban-cli
description: "Use when starting a session in testTrade, before planning any work, or after changing code/tests — maintains the project state board (.kanban/) of tasks, bugs, file purposes, components, flows, and risks. Start with `python3 .qoder/skills/kanban.cli/scripts/kanban.py status`."
---

# kanban.cli — Project State Board

## Overview

`kanban.cli` is a **project state board** for testTrade. It complements graphify:

- **graphify** = code-structure graph (AST, imports, call graphs, community detection). Use it for "how does X work?" and "what calls Y?".
- **kanban.cli** = project state board (tasks, bugs, file purposes, components, flows, risks, staleness). Use it for "what's done?", "what's broken?", "what's in flight?".

Both are mandatory before code exploration: graphify first for structure, kanban first for state.

The board lives in `.kanban/state.json` (single source of truth) and `.kanban/BOARD.md` (generated, never hand-edited). Deterministic facts (files, hashes, git, tests, deps) are computed by `scan`; judgment fields (purposes, statuses, risks, flows) are curated by agents via CLI commands. Hash-anchored staleness makes rot **visible** instead of silent. Per AGENTS.md rule 3, the tool also reports **knowledge-graph (graphify) staleness** so agents know exactly when to run `/graphify update`.

## When to Use

- **Starting a session** → run `status` to see what's in flight, blocked, broken.
- **Before planning work** → check `status` for existing cards, stale annotations, open bugs.
- **After changing code/tests** → run `scan`, update touched cards, set purposes for new files.
- **Discovering a bug or debt** → create a card immediately (don't rely on memory).
- **Finishing work** → move card to `done`, add follow-up cards for discovered issues.
- **Ending a session** → run `sync-tracker` and paste the output where appropriate.

## Quick Reference

```bash
# Core workflow
python3 .qoder/skills/kanban.cli/scripts/kanban.py status          # agent digest
python3 .qoder/skills/kanban.cli/scripts/kanban.py scan             # refresh facts
python3 .qoder/skills/kanban.cli/scripts/kanban.py board            # view board
python3 .qoder/skills/kanban.cli/scripts/kanban.py check            # integrity check

# Cards (tasks, bugs, debt)
python3 .qoder/skills/kanban.cli/scripts/kanban.py card add "Fix C1" --kind bug --priority P0 --files scalpr/runtime/boot.py
python3 .qoder/skills/kanban.cli/scripts/kanban.py card move K-001 in_progress
python3 .qoder/skills/kanban.cli/scripts/kanban.py card move K-001 blocked --note "waiting on sandbox creds"
python3 .qoder/skills/kanban.cli/scripts/kanban.py card move K-001 done
python3 .qoder/skills/kanban.cli/scripts/kanban.py card list --lane in_progress

# File annotations
python3 .qoder/skills/kanban.cli/scripts/kanban.py file set-purpose scalpr/runtime/boot.py "Composition root + boot sequence"
python3 .qoder/skills/kanban.cli/scripts/kanban.py file list --unannotated

# Components, flows, risks
python3 .qoder/skills/kanban.cli/scripts/kanban.py component add domain --purpose "Domain entities + ports" --paths scalpr/domain
python3 .qoder/skills/kanban.cli/scripts/kanban.py flow add order-lifecycle --summary "CLI → OMS → broker" --steps "cli;oms;broker"
python3 .qoder/skills/kanban.cli/scripts/kanban.py risk add "C1 race condition" --severity high --area runtime

# Staleness + sync
python3 .qoder/skills/kanban.cli/scripts/kanban.py stale
python3 .qoder/skills/kanban.cli/scripts/kanban.py sync-tracker    # paste into progress log
```

Full command reference: see `references/commands.md`.

## Agent Workflow

### 1. Session Start
```bash
python3 .qoder/skills/kanban.cli/scripts/kanban.py status
```
- If scan is stale (>24h) or HEAD has moved → run `scan`.
- If the knowledge graph (graphify) is stale → auto-run `/graphify update` before
  code exploration per AGENTS.md rule 3.
- Review in-progress cards, blocked cards, open bugs, high risks.

### 2. Claiming Work
```bash
python3 .qoder/skills/kanban.cli/scripts/kanban.py card move K-001 in_progress
```

### 3. After Changes
```bash
python3 .qoder/skills/kanban.cli/scripts/kanban.py scan
```
- Run `scan` after any code/test changes.
- Update touched cards with `card update K-001 --detail "..."`.
- Set purposes for new/understood files: `file set-purpose src/foo.py "What it does"`.
- Re-anchor verified stale annotations by re-running `file set-purpose` on them.

### 4. Finishing
```bash
python3 .qoder/skills/kanban.cli/scripts/kanban.py card move K-001 done
```
- Move to `done`.
- Add follow-up cards for discovered debt/bugs.

### 5. Session End
```bash
python3 .qoder/skills/kanban.cli/scripts/kanban.py sync-tracker
```
- The output is a markdown block you can paste into any progress log.

## Curation Guidelines

- **File purposes** = one line, what the file/module does (not how). Example: "Order aggregate + state machine" not "Contains Order class with methods X, Y, Z".
- **Cards** = atomic units of work. One bug = one card. One feature = one card (break into sub-cards if needed).
- **Bugs** = carry repro steps in the `detail` field.
- **Components** = map to architecture layers (domain, application, infrastructure, runtime, etc.).
- **Flows** = describe data/execution paths across components.
- **Risks** = anything that could derail the project (technical debt, missing expertise, external dependencies).

## Common Mistakes & Red Flags

- **Hand-editing `state.json` or `BOARD.md`** — these are generated. Use the CLI.
- **Skipping `scan` after edits** — staleness warnings will fire every session.
- **Putting code-structure facts in kanban** — use `graphify query` for "how does X work?". Use kanban for "what's the status of X?".
- **Creating new ad-hoc status .md files** — use cards instead. The board is the single source of truth.
- **Forgetting `sync-tracker`** — the progress tracker goes stale without it.
- **Trusting the old tracker blindly** — it may be stale. Verify card statuses against actual branch code.

## See Also

- `references/commands.md` — full CLI reference
- `references/schema.md` — state.json schema
- `references/seeding-and-sync.md` — seeding from existing docs; tracker sync
- graphify skill — for code-structure queries

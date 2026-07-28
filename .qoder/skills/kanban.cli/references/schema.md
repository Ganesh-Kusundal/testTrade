# kanban.cli state.json Schema

`v2/.kanban/state.json` is the single source of truth. Written with `indent=2, sort_keys=True` for minimal git diffs.

## Top-level Structure

```jsonc
{
  "version": 1,                    // schema version
  "project": { "name": "str", "created": "iso8601", "updated": "iso8601" },
  "scan": { ... },                 // overwritten by `scan`
  "files": { ... },                // keyed by v2-relative path
  "components": { ... },
  "cards": { ... },                // keyed by K-NNN
  "flows": { ... },
  "risks": { ... },                // keyed by R-NNN
  "next_id": { "card": 1, "risk": 1 }
}
```

## `scan` Block (deterministic, overwritten by `scan`)

```jsonc
{
  "at": "iso8601",                 // when scan ran
  "git": {
    "branch": "str",
    "head": "short-sha",
    "dirty": ["path1", "path2"],   // git status --porcelain, scoped to v2
    "recent": [                    // last 10 commits
      { "sha": "abc1234", "date": "2026-07-28", "subject": "commit message" }
    ]
  },
  "counts": {
    "src_files": 216,              // .py files in src/
    "test_files": 199,             // test_*.py files in tests/
    "test_functions": 1234,        // regex-matched test functions
    "pytest_collected": null       // int if --full-tests, else null
  },
  "deps": {
    "runtime": { "pydantic": ">=2.0", ... },
    "dev": { "pytest": ">=8.0", ... }
  },
  "python_requires": ">=3.12",
  "changed_last_run": ["paths"]    // dirty files at scan time
}
```

## `files` Block (keyed by v2-relative path)

```jsonc
{
  "src/tradex/runtime/boot.py": {
    "hash": "sha1hex",             // sha1 of file content
    "loc": 214,                    // line count
    "purpose": "Composition root + boot sequence",  // agent-curated
    "component": "runtime",        // agent-curated
    "annotated_at": "iso8601",     // when purpose was last set
    "annotated_hash": "sha1hex"    // hash at annotation time (staleness anchor)
  }
}
```

**Staleness rule:** a file is stale if `purpose` is set AND `hash != annotated_hash`.

## `cards` Block (keyed by `K-NNN`)

```jsonc
{
  "K-001": {
    "title": "Fix C1 boot-order race",
    "kind": "bug",                 // feature|bug|task|debt|chore
    "lane": "in_progress",         // backlog|in_progress|blocked|review|done
    "priority": "P0",              // P0|P1|P2|P3
    "detail": "Repro: ...",
    "files": ["src/tradex/runtime/boot.py"],
    "blocked_by": "waiting on sandbox",  // reason when blocked
    "links": ["K-004"],            // related card IDs
    "tags": ["c1-c5", "execution"],
    "created": "iso8601",
    "updated": "iso8601",
    "history": [                   // lane transitions
      { "at": "iso8601", "from": "backlog", "to": "in_progress" }
    ]
  }
}
```

**Card staleness hint:** a non-done card is stale if any of its `files` appear in `scan.changed_last_run` after `card.updated`.

## `components` Block

```jsonc
{
  "domain": {
    "purpose": "Domain entities + ports (no inbound imports)",
    "paths": ["src/tradex/domain"],
    "depends_on": [],
    "notes": ""
  }
}
```

## `flows` Block

```jsonc
{
  "order-lifecycle": {
    "summary": "CLI → OMS → broker → fill",
    "steps": ["cli", "oms", "broker", "fill"],
    "files": ["src/tradex/cli.py", "src/application/oms"]
  }
}
```

## `risks` Block (keyed by `R-NNN`)

```jsonc
{
  "R-001": {
    "desc": "C1 race condition in dedup",
    "severity": "high",            // high|med|low
    "area": "runtime",
    "mitigation": "Use (order_id, status) tuple",
    "status": "open"              // open|accepted|resolved
  }
}
```

## Entity Semantics

### Card Lifecycle
```
backlog → in_progress → review → done
              ↓
            blocked → (unblocked) → in_progress
```
- `backlog`: planned, not started.
- `in_progress`: actively being worked.
- `blocked`: cannot proceed (requires `--note` with reason).
- `review`: code complete, awaiting review/merge.
- `done`: completed.

### Priority
- `P0`: Critical — blocks release or live safety.
- `P1`: High — must fix before next milestone.
- `P2`: Medium — normal work.
- `P3`: Low — nice to have.

### Risk Severity
- `high`: Could cause significant project failure.
- `med`: Could cause moderate delay or quality issue.
- `low`: Minor concern.

### Risk Status
- `open`: Identified, not yet addressed.
- `accepted`: Known, deliberately not fixing (document why).
- `resolved`: Mitigated or no longer relevant.

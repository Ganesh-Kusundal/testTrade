# Agent rules for this repository

Standing rules that apply to every agent session working in this repo.
Read this file at session start, before any other tool call.

## Session-start protocol

1. **Read `.kanban/CONTEXT.md` first.** It is the fastest complete picture
   of what is done, in progress, broken, and planned.
2. **Run `python3 .qoder/skills/kanban.cli/scripts/kanban.py update`**
   before any planning or module modification so drift, tests, imports,
   and commits are current.
3. **If kanban reports graphify STALE**, auto-run `/graphify update` to
   refresh the knowledge graph before continuing.
4. **After any code change or commit**, re-run `kanban.py update` so the
   digest does not silently go stale.

## Staging discipline

- **Stage, don't commit.** Use `git add` to stage changes; never run
  `git commit` unless the user explicitly asks for it.
- Keep the working tree committable at all times — every staged state
  must pass `pytest tests/unit/ tests/contract/` with 0 failures.

## Audit and planning protocols

- **Ultra-plan**: for any large, multi-step task, synthesise a phased,
  prioritised remediation plan (root causes → fixes → validation →
  risk mitigation) before touching code.
- **Parallel execution**: when 2+ independent workstreams exist, run
  them in parallel rather than sequentially.
- **Evidence-based findings**: every claim must be backed by source
  code, runtime verification, tests, logs, or configuration — never
  infer runtime behaviour from static code alone.

## Scope constraints

- **Dhan-only** for broker-specific audits unless explicitly widened.
- **`/graphify` v2 only** — do not rebuild v1 artefacts.

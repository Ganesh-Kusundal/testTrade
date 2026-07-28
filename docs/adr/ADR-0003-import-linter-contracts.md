# ADR-0003 — Layered Architecture Enforced by import-linter Contracts

## Date
2026-07-28

## Status
accepted

## Context
SCALPR follows a layered architecture where the domain core is dependency-free, infrastructure modules (brokers, OMS, risk, strategy) depend inward on domain but not on each other's internals, and presentation layers (API, CLI) sit at the outermost edge. Without automated enforcement, developers can accidentally introduce imports that violate these boundaries — for example, a risk module importing a CLI utility, or a broker adapter importing an API route handler. Such violations create hidden coupling and make modules untestable in isolation.

## Decision
The project uses [import-linter](https://import-linter.readthedocs.io/) (declared in `pyproject.toml` L36 as a dev dependency) to define **5 active architecture contracts** in `pyproject.toml` L215-246. These are checked in CI on every commit:

| # | Contract Name | Source Module | Forbidden Imports | Rationale |
|---|---|---|---|---|
| 1 | Domain independence | `scalpr.domain` | `scalpr.brokers`, `scalpr.api`, `scalpr.cli`, `scalpr.oms` | Domain must be pure — no infrastructure dependencies |
| 2 | Risk cannot import API | `scalpr.risk` | `scalpr.api`, `scalpr.cli` | Risk logic must not depend on presentation |
| 3 | OMS cannot import API | `scalpr.oms` | `scalpr.api`, `scalpr.cli` | Order management must not depend on presentation |
| 4 | Strategy cannot import API | `scalpr.strategy` | `scalpr.api`, `scalpr.cli` | Strategy logic must not depend on presentation |
| 5 | Broker Dhan isolation | `scalpr.brokers.dhan` | `scalpr.api`, `scalpr.cli` | Broker adapters must not depend on presentation |

**Verification**: As of this writing, all 5 contracts pass — confirmed by grepping for forbidden import patterns:
- `scalpr/domain/` — 0 imports from `scalpr.brokers`, `scalpr.api`, `scalpr.cli`, or `scalpr.oms`
- `scalpr/risk/` — 0 imports from `scalpr.api` or `scalpr.cli`
- `scalpr/oms/` — 0 imports from `scalpr.api` or `scalpr.cli`
- `scalpr/strategy/` — 0 imports from `scalpr.api` or `scalpr.cli`
- `scalpr/brokers/dhan/` — 0 imports from `scalpr.api` or `scalpr.cli`

**3 planned contracts** (pending module maturity):
- **REF-005**: `scalpr.signals` cannot import `scalpr.brokers` (signal computation must use domain events, not direct broker calls)
- **REF-013**: `scalpr.simulation` cannot import `scalpr.api` (simulation must be API-independent)
- **Cross-layer**: `scalpr.market_data` cannot import `scalpr.api` or `scalpr.cli`

## Consequences

### Positive
- Architectural decay is caught automatically in CI, not discovered during refactoring.
- New contributors learn the dependency rules from machine-enforced contracts rather than tribal knowledge.
- Domain layer remains portable and testable without any broker or infrastructure setup.

### Negative
- Adding a new contract requires understanding the dependency graph; overly strict contracts can block legitimate refactoring.
- import-linter checks add ~2-5 seconds to CI pipeline time.

## Alternatives Considered
- **Manual code review only** — Rejected: reviewers miss subtle import violations; enforcement is inconsistent.
- **ArchUnit (Java-style)** — Rejected: no mature Python equivalent with CI integration; import-linter is purpose-built.
- **Custom linting script** — Rejected: higher maintenance burden; import-linter provides declarative contract definitions and clear error messages.

# Agent rules for this repository

Standing rules that apply to every agent session working in this repo.
Read this file at session start, before any other tool call.

## Session-start protocol

> **Plan mode?** Skip steps 1, 3, 5 — they write to `.kanban/state.json`
> and will be denied. Use `Read` on `.kanban/BOARD.md` instead.
> See [Permission & Sandbox Guidance](#permission--sandbox-guidance).

1. **Run `python3 .qoder/skills/kanban.cli/scripts/kanban.py status`**
   to see the agent-facing digest — what's in flight, blocked, broken.
   If `BOARD.md` exists, you can also read it directly.
2. **Read the Runbook section** in the status output or board —
   these are operational procedures written by previous sessions.
   Use `python3 .qoder/skills/kanban.cli/scripts/kanban.py runbook show <id>`
   for detailed steps and code examples.
3. **Run `python3 .qoder/skills/kanban.cli/scripts/kanban.py scan`**
   before any planning or module modification so facts, drift, tests,
   imports, and graphify staleness are current.
4. **If kanban reports graphify STALE** (in `status` or `stale` output),
   auto-run `/graphify update` to refresh the knowledge graph before
   continuing.
5. **After any code change or commit**, re-run `scan` so the digest
   does not silently go stale.

## Post-edit validation

After **every material edit** to a core source file under `scalpr/**/*.py`,
run the smallest relevant pytest suite before continuing to the next task.

### Default command (full gate)

```bash
pytest tests/unit/ tests/contract/ -x --tb=short
```

### Narrowing to the changed module

When the edit is confined to a single module, narrow the run to the
corresponding test subtree so feedback is faster:

| Changed source path            | Narrowed test path                        |
|--------------------------------|-------------------------------------------|
| `scalpr/domain/<mod>.py`       | `tests/unit/domain/`                      |
| `scalpr/engine/<mod>.py`       | `tests/unit/engine/`                      |
| `scalpr/adapters/dhan/<m>.py`  | `tests/unit/adapters/dhan/`               |
| `scalpr/risk/<mod>.py`         | `tests/unit/risk/`                        |
| `scalpr/oms/<mod>.py`          | `tests/unit/oms/`                         |
| `scalpr/gateway/<mod>.py`      | `tests/unit/gateway/`                     |
| `scalpr/signals/<mod>.py`      | `tests/unit/signals/`                     |
| `scalpr/scanner/<mod>.py`      | `tests/unit/scanner/`                     |
| `scalpr/strategy/<mod>.py`     | `tests/unit/strategy/`                    |
| `scalpr/simulation/<mod>.py`   | `tests/unit/simulation/`                  |
| `scalpr/market_data/<mod>.py`  | `tests/unit/market_data/`                 |
| `scalpr/observability/<m>.py`  | `tests/unit/observability/`               |
| `scalpr/api/<mod>.py`          | `tests/unit/api/`                         |
| `scalpr/execution/<mod>.py`    | `tests/unit/execution/`                   |
| `scalpr/portfolio/<mod>.py`    | `tests/unit/` (no dedicated subtree)      |

**Narrowed example:**

```bash
# Edited scalpr/adapters/dhan/_mapper.py
pytest tests/unit/adapters/dhan/ tests/contract/ -x --tb=short
```

### Rules

1. **Always include `tests/contract/`** — contract tests prove cross-broker
   interchangeability and must run even for narrow changes.
2. **Fall back to the full gate** when the edit touches multiple modules,
   cross-cutting concerns (e.g. `domain/events.py`), or when a narrowed run
   itself fails.
3. **Fix before continuing.** If the validation fails, resolve the failure
   before editing the next file. Never accumulate test debt across edits.
4. **Re-run after fix.** After a fix, re-run the same scope (narrowed or full)
   to confirm green before moving on.
5. **Non-source edits** (docs, comments-only, frontend, config) do not
   trigger this step.

## Session-end / after operational tasks

After completing any task that involved *learning how to use* part of the
system (e.g. how to call an API, which files are involved, what the flow
is), add or update a runbook entry so the next session benefits:

```
python3 .qoder/skills/kanban.cli/scripts/kanban.py runbook add "intent" \
  --api "Class.method()" \
  --steps "step 1; step 2" \
  --example "code example" \
  --files "file1.py,file2.py" \
  --tags "tag1,tag2"
```

## Staging discipline

- **Stage, don't commit.** Use `git add` to stage changes; never run
  `git commit` unless the user explicitly asks for it.
- Keep the working tree committable at all times — every staged state
  must pass `pytest tests/unit/ tests/contract/` with 0 failures.
- **Post-edit validation** (see above) is the per-edit enforcement;
  this section is the per-commitment guarantee. Both use the same
  command; the post-edit step catches regressions earlier.

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

## Permission & Sandbox Guidance

Pre-authorised safe operations — these commands are read-only or confined to
project-local state and should never trigger a permission prompt:

```bash
# Kanban board status (read-only digest)
python3 .qoder/skills/kanban.cli/scripts/kanban.py status

# Kanban runbook lookup (read-only)
python3 .qoder/skills/kanban.cli/scripts/kanban.py runbook show <id>

# Kanban scan (reads project state, writes .kanban/ local cache)
python3 .qoder/skills/kanban.cli/scripts/kanban.py scan

# Test runs (read source, write nothing outside workspace)
pytest tests/unit/ tests/contract/ -x --tb=short

# Git status / diff (read-only)
git status && git diff --stat
```

### Plan mode restrictions

When the session is in **Plan mode**, only read-only shell commands are allowed.
Write operations (file edits, `git add`, `pytest` that creates `.pytest_cache`,
kanban `scan` that updates `.kanban/state.json`) are denied by the policy layer.

**Supported route in Plan mode:**

1. Use `Read`, `Grep`, `Glob`, `SearchCodebase`, `SearchSymbol` — these always
   work regardless of mode.
2. For Bash, restrict to truly read-only commands: `cat`, `ls`, `git log`,
   `git diff`, `git status`, `find`, `wc`, `head`, `tail`.
3. Do **not** attempt `pytest`, `kanban.py scan`, `git add`, or any command
   that writes files — these will be denied and waste turns.
4. If a write is needed, exit Plan mode first or ask the user to switch to
   Agent mode.

### Sandbox write boundary

The sandbox restricts writes to the workspace directory. Commands that write
outside the workspace (e.g. `/tmp`, `~/.config`, system paths) are denied.

**Supported route:**

- All project artefacts (`.kanban/`, `.qoder/`, `data/`, `runtime/`,
  `runtime-dev/`) are inside the workspace — no permission issue.
- If a tool needs a temporary file, write it inside the workspace:
  use `/tmp` only when the command is read-only.
- Never attempt to write to `~/.qoder/`, `~/.config/`, or system paths.

### Credential safety

Commands that may print secrets (JWT tokens, TOTP secrets, API keys, access
_tokens) to stdout are denied by the classifier.

**Supported route:**

- Never `cat`, `echo`, or `print` credential files (`config/dhan-pin.txt`,
  `config/dhan-totp-secret.txt`, `.env`) to stdout.
- Use `config/secrets_manager.py` to load secrets programmatically.
- If you need to verify a token exists, use `test -f <path>` instead of
  reading its contents.

---

## New Adapter Architecture

The system decouples broker-specific logic from strategy code via a message-bus mediator pattern.

### Core components

| Component | File | Role |
|---|---|---|
| `MessageBus` | `scalpr/engine/message_bus.py` | In-process pub/sub + req/rep. Strategies publish `exec.command.*`; brokers subscribe to `exec.command.*.<broker>`. |
| `RecordingBus` | `scalpr/engine/message_bus.py` | `MessageBus` subclass that records all published events for test assertions. |
| `Clock` (ABC) | `scalpr/engine/clock.py` | Abstract source-of-truth for time. `LiveClock` wraps `datetime.now()`; `StaticClock` is deterministic for tests. |
| `ExecutionEngine` | `scalpr/engine/execution_engine.py` | Mediates between strategy and broker. Subscribes to `exec.command.submit` → routes to `exec.command.submit.<broker>`. Maintains `EventStore` + `Cache`. |
| `DhanClient` | `scalpr/adapters/dhan/client.py` | Dhan-specific adapter. Subscribes to `exec.command.submit.dhan`. Publishes `exec.event.fill.dhan` / `exec.event.rejected.dhan`. |

### Data flow

```
Strategy
  → bus.publish("exec.command.submit", SubmitOrder(order, broker="dhan"))
    → ExecutionEngine._on_submit()
      → bus.publish("exec.command.submit.dhan", cmd)
        → DhanClient._on_submit()
          → HTTP POST /orders
          → bus.publish("exec.event.fill.dhan", OrderFilled(...))
```

### Broker routing convention

Topics use the pattern `{domain}.{verb}.{broker}`:

- `exec.command.submit.<broker>` — incoming order command
- `exec.command.cancel.<broker>` — cancel command
- `exec.command.modify.<broker>` — modify command
- `exec.event.fill.<broker>` — fill notification (broker → engine)
- `exec.event.rejected.<broker>` — rejection notification
- `exec.event.cancelled.<broker>` — cancellation confirmation
- `market.quote.<broker>` — tick/quote data

## File Layout

```
scalpr/
├── domain/                          # Pure domain objects (no I/O, no broker dependencies)
│   ├── __init__.py                  # Re-exports all domain types
│   ├── order.py                     # Order, OrderSide, OrderType, OrderState, FSM
│   ├── fill.py                      # Fill dataclass
│   ├── instrument.py                # Exchange, Instrument, SimpleInstrumentId, DerivativeInstrumentId
│   ├── position.py                  # Position, PositionSide, PositionState
│   ├── signal.py                    # Signal, SignalType, Gate
│   ├── tick.py                      # Tick, OHLCV
│   ├── events.py                    # DomainEvent subclasses (OrderPlaced, FillReceived, etc.)
│   └── values.py                    # Shared constants (ZERO, etc.)
│
├── engine/                          # Core orchestration (broker-agnostic)
│   ├── message_bus.py               # MessageBus, RecordingBus, Event
│   ├── clock.py                     # Clock (ABC), LiveClock, StaticClock
│   └── execution_engine.py          # ExecutionEngine, EventStore, Cache, command/event dataclasses
│
└── adapters/                        # Broker-specific implementations
    ├── dhan/                        # Dhan broker
    │   ├── client.py                # DhanClient — main adapter
    │   ├── _auth.py                 # TokenManager (TOTP + access token refresh)
    │   ├── _http.py                 # DhanHttpClient, RateLimiter
    │   ├── _ws.py                   # DhanWebSocket
    │   ├── _mapper.py               # domain↔JSON request/response mappers
    │   ├── _resolver.py             # Symbol → security_id resolution
    │   ├── _loader.py               # Instrument CSV loader
    │   ├── _historical.py           # Historical data adapter
    │   ├── _option_chain.py         # Option chain + strike selection
    │   ├── _greeks.py               # GreeksCalculator (Black-Scholes)
    │   └── _portfolio.py            # PortfolioAdapter (PnL, positions summary)
    │
    └── test_helpers/                # Test infrastructure
        ├── fake_exchange.py         # FakeExchange — in-memory broker for contract tests
        └── recording_bus.py         # (legacy; use engine.message_bus.RecordingBus)

tests/
├── conftest.py                      # Shared fixtures: RecordingBus, StaticClock, DhanClient (mocked), FakeExchange
├── contract/                        # Parametrized cross-broker contract tests
│   ├── test_execution_client.py     # Core interchangeability tests
│   ├── test_dhan_order_payload.py   # Dhan-specific payload shape validation
│   ├── test_resolution_api.py       # Symbol resolution contract
│   ├── test_gateway_contract.py     # Gateway interface contract
│   └── ...
├── e2e/                             # Live API smoke tests
│   └── test_dhan_live.py            # Full DhanClient lifecycle against real API
├── unit/                            # Unit tests mirroring the package structure
└── fixtures/dhan_responses/         # JSON fixtures mocked HTTP responses
```

## Import Conventions

Import from the canonical public API surface — never from private modules outside the owning package:

```python
# ✅ Domain objects — from scalpr.domain or its __init__
from scalpr.domain.order import Order, OrderSide, OrderType, OrderState
from scalpr.domain.fill import Fill
from scalpr.domain.instrument import Exchange, Instrument, SimpleInstrumentId
from scalpr.domain.position import Position, PositionSide
from scalpr.domain.values import ZERO

# ✅ Engine types
from scalpr.engine.clock import Clock, LiveClock, StaticClock
from scalpr.engine.message_bus import MessageBus, RecordingBus, Event
from scalpr.engine.execution_engine import (
    ExecutionEngine, SubmitOrder, CancelOrder, ModifyOrder,
    OrderFilled, OrderRejected, OrderCancelled,
)

# ✅ Broker adapters
from scalpr.adapters.dhan.client import DhanClient

# ✅ Test helpers
from scalpr.adapters.test_helpers.fake_exchange import FakeExchange
```

**Rules:**
- Never import from `scalpr.brokers.*` (legacy namespace).
- Never import private modules (prefixed with `_`) from outside their package — e.g. `scalpr.adapters.dhan._mapper` is internal to `DhanClient`.
- Use `scalpr.domain.__init__` re-exports for convenience when consuming multiple types.

## Contract Test Pattern

Contract tests prove broker interchangeability — every test runs against both `DhanClient` (mocked) and `FakeExchange` with the same assertions.

### Mechanism

```python
# tests/contract/test_execution_client.py

@pytest.mark.parametrize("client_fixture", ["dhan_client", "fake_exchange"])
def test_submit_and_fill(self, client_fixture: str, request, bus: RecordingBus):
    client = request.getfixturevalue(client_fixture)
    order = Order(order_id="test-1", symbol="RELIANCE", exchange=Exchange.NSE,
                  side=OrderSide.BUY, order_type=OrderType.LIMIT,
                  quantity=10, price=Decimal("2500.00"))

    bus.publish("exec.command.submit", SubmitOrder(order=order, broker=client.broker))

    fills = bus.filter("exec.event.fill")
    assert len(fills) >= 1
    assert fills[0].payload.order_id == "test-1"
```

### Fixture wiring (defined in `tests/conftest.py`)

| Fixture | Returns | Notes |
|---|---|---|
| `bus` | `RecordingBus` | Records all events; use `bus.filter("*.fill")` |
| `clock` | `StaticClock` | Deterministic; `clock.advance(n)` to simulate time |
| `engine` | `ExecutionEngine` | Pre-started; subscribes `exec.command.*` → routes to `*.<broker>` |
| `dhan_client` | `DhanClient` | Wired to `MagicMock` HTTP/WS — no real API calls |
| `fake_exchange` | `ContractFakeExchange` | In-memory broker — instant fills |

### Adding a new broker

1. Create `scalpr/adapters/<broker>/client.py` with the same duck-type interface (`submit_order`, `cancel_order`, `get_positions`, `subscribe_quotes`).
2. Add its fixture in `tests/conftest.py` — wire to mocked HTTP/WS if needed.
3. Add the fixture name to every parametrize list in `tests/contract/test_execution_client.py`.

### Guidelines

- Test **behaviour** (events on the bus), not implementation (internal method calls).
- Never call broker methods directly in parametrized tests — always go through the bus (matching strategy code paths).
- Use `bus.filter("exec.event.*")` for assertion — avoids hard-coding broker-specific topic suffixes.
- Keep `hold_next_order` for testing rejection/cancel flows deterministically.

## Live API Testing

E2E tests in `tests/e2e/test_dhan_live.py` exercise the real Dhan API.

### Required environment variables

```
DHAN_CLIENT_ID=your_client_id
DHAN_ACCESS_TOKEN=your_access_token
DHAN_TOTP_SECRET=your_totp_secret      # optional if using static token
DHAN_PIN=1111                           # default; only needed for TOTP refresh
```

### Running

```bash
# All E2E tests (skipped if DHAN_CLIENT_ID is unset)
pytest tests/e2e/ -v

# Single test
pytest tests/e2e/test_dhan_live.py::TestDhanLiveE2E::test_funds -v

# With .env file (loaded automatically by the fixture)
echo "DHAN_CLIENT_ID=..." >> .env
echo "DHAN_ACCESS_TOKEN=..." >> .env
pytest tests/e2e/ -v
```

### Secrets management

- Never commit `.env` or hardcode credentials in source.
- The E2E fixture uses `dotenv.load_dotenv()` so a `.env` file at the repo root is picked up automatically.
- CI pipelines inject secrets via environment variables (GitHub Actions secrets / equivalent).

### Best practices

- Tests are `pytest.mark.skipif(not os.environ.get("DHAN_CLIENT_ID"))` — CI-safe by default.
- Rate-limited endpoints are wrapped in try/except (the shared IP of a test environment may hit API limits).
- Scope E2E fixtures as `module` to avoid re-authenticating for every test.
- Keep E2E tests as smoke checks (not exhaustive) — the contract and unit suites provide coverage without live credentials.

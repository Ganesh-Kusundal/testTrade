# ADR-0005 — Split Gateway God-Class into a `brokers/gateway/` Package

## Date
2026-07-28

## Status
proposed

> *This ADR documents the TARGET state after REF-007 is implemented.*

## Context
The `Gateway` class in `scalpr/brokers/gateway.py` has grown to **753 lines of code** with **27 methods** (including `__init__`, 2 properties, and 7 private methods). It serves as the primary user-facing API for the entire framework, combining responsibilities across five distinct domains:

| Responsibility | Methods | Lines (approx.) |
|---|---|---|
| **Market Data** | `ltp()`, `quote()`, `depth()`, `history()` | L116-273 (~157) |
| **Portfolio** | `positions()`, `holdings()`, `funds()` | L275-329 (~55) |
| **Orders & Trades** | `orders()`, `trades()` | L331-367 (~37) |
| **Streaming** | `stream()`, `stop_stream()`, `is_streaming()`, `subscribe_feed()`, `unsubscribe()`, `_dispatch_tick()`, `_init_websocket_manager()` | L369-493 (~125) |
| **Lifecycle** | `connect()`, `disconnect()`, `close()`, `is_connected()` | L660-737 (~78) |
| **Instrument API** | `instrument()`, `option_chain()`, `_get_dhan_connection()` | L495-716 (~222) |
| **Config** | `_load_config_from_env()` | L83-114 (~32) |

A single 753-line file is difficult to navigate, hard to test in isolation (streaming logic entangled with market data), and blocks parallel development (two developers cannot work on streaming and orders without merge conflicts).

## Decision
Split `scalpr/brokers/gateway.py` into a **`scalpr/brokers/gateway/` package** with the following module structure:

```
scalpr/brokers/gateway/
├── __init__.py        # Re-exports Gateway class
├── facade.py          # Gateway class — public API, delegates to sub-modules
├── market_data.py     # ltp(), quote(), depth(), history()
├── orders.py          # orders(), trades()
├── streaming.py       # stream(), stop_stream(), subscribe_feed(), unsubscribe(), WS manager init
└── lifecycle.py       # connect(), disconnect(), close(), is_connected(), config loading
```

**Key constraints:**
- The `Gateway` class **remains the public facade** — no external API changes. All existing call sites (`Gateway()`, `gw.ltp()`, `gw.stream()`, etc.) continue to work unchanged.
- The `instrument()` and `option_chain()` methods remain on `Gateway` in `facade.py` (they are user-facing and cross-cutting).
- Internal implementation details (WebSocket thread management, config loading) move to their respective modules as mixin classes or composition delegates.
- The `IBrokerGateway` port interface (`scalpr/brokers/broker_port.py`) is unchanged.

## Consequences

### Positive
- Each sub-module is 100-200 LOC — easy to read, test, and review.
- Parallel development: streaming changes don't touch order files.
- Unit tests can mock individual concern areas without loading the entire Gateway.
- Clear ownership: each module has a single responsibility.

### Negative
- Internal refactoring risk: method extraction may reveal hidden state sharing (e.g., `_ws_manager` is accessed by both streaming and instrument methods).
- Import structure must be carefully managed to avoid circular imports within the package.
- The `_get_dhan_connection()` method (L707-716) already breaks the broker-agnostic contract; splitting doesn't fix this, it just relocates it.

## Alternatives Considered
- **Keep single file, add region comments** — Rejected: doesn't reduce complexity or enable parallel development; comments are not enforced.
- **Extract to separate top-level modules (e.g., `scalpr/streaming/`, `scalpr/market_data/`)** — Rejected: these are Gateway concerns, not independent modules; would require restructuring the public API.
- **Use composition (Gateway holds MarketDataAPI, OrdersAPI, etc.)** — Considered as part of the decision; the final design uses a hybrid: sub-modules provide implementation, `Gateway` facade delegates. This preserves the existing flat API (`gw.ltp()` not `gw.market_data.ltp()`).

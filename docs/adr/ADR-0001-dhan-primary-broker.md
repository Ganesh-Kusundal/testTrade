# ADR-0001 — Dhan as Primary (and Currently Only Production) Broker

## Date
2026-07-28

## Status
accepted

## Context
SCALPR is designed as a broker-agnostic algorithmic trading framework for Indian exchanges (`pyproject.toml` L3: *"broker-agnostic algorithmic trading framework for Indian exchanges"*). The architecture includes a broker port (`scalpr/brokers/broker_port.py` — `IBrokerGateway` ABC with 15 abstract methods), a registry (`scalpr/brokers/registry.py`), and canonical contract models (`scalpr/brokers/contracts.py`) to insulate application code from any specific broker.

Despite this multi-broker design, only one broker has a live, production-ready integration: **Dhan** (`scalpr/brokers/dhan/` — 16 modules covering auth, HTTP, WebSocket, market data, orders, option chain, instrument resolution, etc.).

Upstox has configuration templates (`config/upstox-live.properties.example`, `config/upstox-sandbox.properties.example`) and test markers in `pyproject.toml` (L66-72: `upstox`, `upstox_integration`, `upstox_sandbox`, etc.), but no implementation module exists under `scalpr/brokers/`. The broker entry-points in `pyproject.toml` L44-48 are all commented out.

## Decision
Dhan is designated as the **primary and only production-ready broker**. All active development, testing, and live trading targets Dhan. The broker-agnostic facade (`IBrokerGateway`, `BrokerRegistry`, canonical contracts) is retained to:

1. Allow future broker additions (Upstox, others) without refactoring application code.
2. Enable the `paper` broker (`scalpr/oms/paper_oms.py`) for simulation and backtesting.
3. Keep the domain layer free of broker-specific logic.

The `Gateway` class (`scalpr/brokers/gateway.py` L57) defaults to `broker="dhan"`. The `_load_config_from_env` method (L83-114) only handles the `"dhan"` case; any other broker name raises `ValueError`.

## Consequences

### Positive
- Focused development effort on a single broker reduces surface area for bugs.
- The broker-agnostic port/adapter pattern is validated by having one concrete implementation.
- Paper trading via `PaperOms` works without any live broker dependency.

### Negative
- The abstraction layer adds indirection that is currently only exercised by one adapter, making it harder to validate the design's generality.
- `_get_dhan_connection()` (`scalpr/brokers/gateway.py` L707-716) reaches into Dhan-specific internals, breaking the abstraction for `instrument()` and `option_chain()`.

## Alternatives Considered
- **Multi-broker from day one** — Rejected: would delay delivery; Dhan was the broker with active API access and trading accounts.
- **Drop the abstraction, hard-code Dhan** — Rejected: the paper broker and simulation engine need the port interface; future Upstox integration would require a costly rewrite.

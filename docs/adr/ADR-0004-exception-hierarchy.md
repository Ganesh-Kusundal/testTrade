# ADR-0004 — Unified Broker-Agnostic Exception Hierarchy

## Date
2026-07-28

## Status
proposed

> *This ADR documents the TARGET state after REF-002 is implemented.*

## Context
The codebase currently has **two parallel exception hierarchies** that serve overlapping purposes:

1. **Broker-agnostic exceptions** in `scalpr/brokers/errors.py` (L12-57): Rooted at `TradingError(Exception)` with 9 subclasses — `AuthenticationError`, `InstrumentNotFound`, `AmbiguousInstrument`, `InvalidInstrument`, `OptionChainNotSupported`, `InvalidOrder`, `InsufficientMargin`, `RateLimitExceeded`, `ProviderUnavailable`, `SubscriptionError`. These are used by the `Gateway` facade and the API layer.

2. **Dhan-specific exceptions** in `scalpr/brokers/dhan/exceptions.py` (L9-41): Rooted at `BrokerError(Exception)` with 6 subclasses — `InstrumentNotFoundError`, `MarketDataError`, `OrderError`, `AuthenticationError`, `ConfigurationError`, `RateLimitError`. These are used internally by the Dhan adapter.

The problem: the `Gateway` class must manually translate between the two hierarchies. For example, `scalpr/brokers/gateway.py` L24 imports `_DhanInstrumentNotFound` and L557-558 catches it to re-raise as the agnostic `InstrumentNotFound`. This translation is scattered, fragile, and incomplete — some Dhan exceptions (e.g., `MarketDataError`, `ConfigurationError`) have no agnostic counterpart and leak through.

## Decision
Adopt a **single broker-agnostic exception hierarchy** rooted at `TradingError` in `scalpr/brokers/errors.py`. Broker-specific exception modules (e.g., `scalpr/brokers/dhan/exceptions.py`) will define subclasses that **inherit from the agnostic base classes**, not from an independent `BrokerError`.

Target state for `scalpr/brokers/dhan/exceptions.py`:
```python
from scalpr.brokers.errors import (
    TradingError,
    AuthenticationError as _AuthError,
    InstrumentNotFound as _InstNotFound,
    RateLimitExceeded as _RateLimit,
)

class BrokerError(TradingError):
    """Base for Dhan-specific errors not covered by agnostic hierarchy."""

class InstrumentNotFoundError(_InstNotFound):
    """Dhan-specific instrument resolution failure with resolver context."""

class AuthenticationError(_AuthError):
    """Dhan token expired or rejected."""

class RateLimitError(_RateLimit):
    """Dhan rate limit exceeded."""

class MarketDataError(BrokerError):
    """Market data fetch failure (Dhan-specific)."""

class OrderError(BrokerError):
    """Order placement/modification/cancellation failure."""

class ConfigurationError(BrokerError):
    """Missing or invalid configuration."""
```

This means:
- `except TradingError` at the API/Gateway layer catches **all** broker errors.
- `except InstrumentNotFound` catches both agnostic and Dhan-specific instrument errors (via inheritance).
- Broker-specific exceptions can carry additional context (e.g., resolver cache state) without breaking the contract.

## Consequences

### Positive
- The `Gateway` no longer needs manual exception translation blocks (eliminates patterns like L24, L557-558).
- API layer can catch `TradingError` once and translate to HTTP status codes uniformly.
- Adding a new broker (e.g., Upstox) means adding a new exception sub-hierarchy under `TradingError`, not a parallel root.

### Negative
- Broker-specific exceptions must be designed to fit the agnostic categories; errors that don't map cleanly require a new agnostic base class.
- Migration requires updating all `except BrokerError` catch sites in Dhan adapter code.

## Alternatives Considered
- **Keep two hierarchies with explicit mapping** — Rejected: mapping is already scattered and incomplete; maintenance burden grows with each new broker.
- **Single flat hierarchy (no broker-specific subclasses)** — Rejected: loses broker-specific context (e.g., Dhan resolver state) that aids debugging.
- **Use exception wrapping (PEP 3134 `__cause__`) exclusively** — Rejected: works for chaining but doesn't allow catching by agnostic type without explicit `from` clauses at every raise site.

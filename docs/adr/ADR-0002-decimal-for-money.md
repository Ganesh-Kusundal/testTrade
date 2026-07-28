# ADR-0002 — Use `decimal.Decimal` for All Price, Money, and Quantity Values

## Date
2026-07-28

## Status
accepted

## Context
SCALPR trades on Indian exchanges (NSE, BSE, MCX) where the smallest currency unit is **paise** (1/100 of a rupee). Broker APIs return prices as strings or integers representing paise. Using IEEE 754 `float` for monetary values introduces representation errors — for example, `float("2435.70")` is actually `2435.6999999999998`. In a real-money trading system, even a single-paise discrepancy in order pricing, margin calculation, or PnL aggregation is unacceptable.

Additionally, lot sizes, quantities, and notional values must be computed exactly. A strategy computing `price * quantity` on floats can silently accumulate rounding errors across hundreds of trades per day.

## Decision
All price, money, and quantity-related values throughout the codebase use `decimal.Decimal`, **never** `float`. This is enforced at two levels:

1. **Type annotations**: Every domain model and contract dataclass declares price fields as `Decimal`:
   - `Order.price`, `Order.trigger_price`, `Order.avg_price` (`scalpr/domain/order.py` L79-83)
   - `Tick.ltp`, `Tick.bid`, `Tick.ask` (`scalpr/domain/tick.py` L12-14)
   - `OHLCV.open/high/low/close` (`scalpr/domain/tick.py` L37-40)
   - `Fill.price` (`scalpr/domain/fill.py` L18)
   - `Position.avg_price`, `Position.ltp`, `Position.unrealised_pnl`, `Position.realised_pnl` (`scalpr/domain/position.py` L31-34)
   - All canonical contract models in `scalpr/brokers/contracts.py` (Quote, DepthLevel, Holding, Funds, Trade)

2. **Runtime type guards**: Every frozen dataclass includes `__post_init__` validation that raises `TypeError` if a price field is not `Decimal`:
   - `Order.__post_init__` (`scalpr/domain/order.py` L90-96)
   - `Tick.__post_init__` (`scalpr/domain/tick.py` L19-25)
   - `Position.__post_init__` (`scalpr/domain/position.py` L38-48)
   - `Fill.__post_init__` (`scalpr/domain/fill.py` L22-24)

3. **Interface contract**: `IBrokerGateway.get_ltp()` returns `Decimal` (`scalpr/brokers/broker_port.py` L69); `modify_order()` accepts `Decimal` price (L22).

## Consequences

### Positive
- Zero precision loss in price arithmetic, margin calculations, and PnL aggregation.
- Type guards catch accidental `float` injection at construction time, not at trade time.
- Aligns with broker API conventions (Dhan returns prices as paise-denominated integers or strings).

### Negative
- `Decimal` is slower than `float` for arithmetic; in tight loops processing thousands of ticks per second this may matter (mitigated by the fact that the WebSocket layer batches ticks).
- Pandas DataFrames default to `float64`; the `history()` method in `Gateway` (L238-251) currently converts OHLCV values to `float` for DataFrame compatibility — this is a known exception to the rule that needs remediation.

## Alternatives Considered
- **Use `int` (paise) internally** — Rejected: loses expressiveness for averages and PnL percentages; requires conversion at every API boundary.
- **Use `float` with rounding** — Rejected: rounding is error-prone and must be applied at every operation; does not prevent intermediate precision loss.
- **Use a third-party money library** — Rejected: adds dependency; domain models are simple enough to use `Decimal` directly with explicit validation.

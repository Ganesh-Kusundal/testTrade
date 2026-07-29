# R5: 5-Day Replay Simulation Test — Report

**Status:** ✅ Done — 6/6 tests passing

## File Created

`tests/unit/simulation/test_e2e_5day_replay.py`

Placed under `tests/unit/simulation/` since integration tests require Dhan credentials.

## Design

| Concern | Approach |
|---------|----------|
| **Data** | Self-contained synthetic OHLCV generation via `_generate_5day_ohlcv()` — seeded random walk around ₹2500 base price, 376 × 1-min bars per day (9:15–15:30 IST / 3:45–10:00 UTC) |
| **Clock** | `SimulatedClock` — time set to each bar's `bar_open_time` before feeding, fully deterministic |
| **Broker** | `SimulatedGateway` with `starting_capital=1_000_000`, LTP updated via `set_ltp` on every tick |
| **Strategy** | `_ReplayTestStrategy` — buys 75 shares at session open (3:45 UTC), sells at session close (10:00 UTC), 5 round-trips |
| **Replay loop** | Simple synchronous `for bar, tick in zip(bars, ticks)` — no asyncio, no `ReplayEngine` dependency |

## Test Cases & Results

| Test | Assertion | Result |
|------|-----------|--------|
| `test_replay_runs_without_exceptions` | Strategy error list is empty | ✅ |
| `test_orders_fill_and_trades_execute` | 10 fills (5 buy + 5 sell) | ✅ |
| `test_positions_open_and_close_correctly` | Position list empty after replay | ✅ |
| `test_pnl_calculated_after_replay` | `total_balance` differs from `START_CAPITAL` (realised P&L changes equity) | ✅ |
| `test_no_unhandled_exceptions_across_five_days` | Stress: 1880 bars × 5 days processed without raising | ✅ |
| `test_deterministic_across_runs` | Same seed → identical trade list | ✅ |

## Invariants Verified

1. ✅ No unhandled exceptions through 1880 ticks
2. ✅ Orders submit and fill (MARKET orders with slippage via `FillSimulator`)
3. ✅ Positions open (long at session start) and close (sell at session end)
4. ✅ P&L calculated — realised PnL reflected in `get_margins().total_balance`
5. ✅ Deterministic — same seed yields identical output

## Command

```bash
pytest tests/unit/simulation/test_e2e_5day_replay.py -v --tb=short
```

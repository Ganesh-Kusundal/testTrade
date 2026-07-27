from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal


class GateState:
    """Represents the market state evaluated by the Gates."""
    def __init__(
        self,
        symbol: str,
        price: Decimal,
        cvd_falling: bool,
        is_at_lvn: bool,
        market_open: bool = True,
        trend_aligned: bool = True,
        vol_spike: bool = True,
        atr_ok: bool = True,
        spread_ok: bool = True,
        oi_ok: bool = True,
        under_daily_cap: bool = True,
        timestamp: datetime | None = None,
    ):
        self.symbol = symbol
        self.price = price
        self.cvd_falling = cvd_falling
        self.is_at_lvn = is_at_lvn
        self.market_open = market_open
        self.trend_aligned = trend_aligned
        self.vol_spike = vol_spike
        self.atr_ok = atr_ok
        self.spread_ok = spread_ok
        self.oi_ok = oi_ok
        self.under_daily_cap = under_daily_cap
        self.timestamp = timestamp or datetime.now(timezone.utc)


@dataclass(frozen=True)
class GateResult:
    """Result of evaluating a single filter gate."""
    gate_id: str
    passed: bool
    reason: str


class GateFSM:
    """Evaluates sequential filter Gates 01-08 for trade entry short-circuiting."""

    @staticmethod
    def evaluate(state: GateState) -> tuple[bool, str, list[GateResult]]:
        """Evaluate Gates 01 to 08 in strict sequential order. Short-circuits on failure."""
        results: list[GateResult] = []

        # Gate 01: Market Open Guard
        if not state.market_open:
            res = GateResult("Gate_01", False, "Market is closed")
            results.append(res)
            return False, "Gate_01 failed", results
        results.append(GateResult("Gate_01", True, "Market is open"))

        # Gate 02: Trend Alignment Guard
        if not state.trend_aligned:
            res = GateResult("Gate_02", False, "Trend is not aligned")
            results.append(res)
            return False, "Gate_02 failed", results
        results.append(GateResult("Gate_02", True, "Trend is aligned"))

        # Gate 03: CVD/Price Correlation Guard
        # BLOCK if: CVD falling AND price NOT at LVN
        # PASS if: CVD falling AND price IS at LVN (institutional absorption)
        if state.cvd_falling and not state.is_at_lvn:
            res = GateResult("Gate_03", False, "Block: CVD falling and price not at Low Volume Node (LVN)")
            results.append(res)
            return False, "Gate_03 failed", results
        results.append(GateResult("Gate_03", True, "CVD/Price correlation passed"))

        # Gate 04: Volume Spike Guard
        if not state.vol_spike:
            res = GateResult("Gate_04", False, "No volume spike detected")
            results.append(res)
            return False, "Gate_04 failed", results
        results.append(GateResult("Gate_04", True, "Volume spike validated"))

        # Gate 05: ATR Guard
        if not state.atr_ok:
            res = GateResult("Gate_05", False, "Volatility (ATR) below threshold")
            results.append(res)
            return False, "Gate_05 failed", results
        results.append(GateResult("Gate_05", True, "Volatility (ATR) check passed"))

        # Gate 06: Spread Guard
        if not state.spread_ok:
            res = GateResult("Gate_06", False, "Bid/Ask spread too wide")
            results.append(res)
            return False, "Gate_06 failed", results
        results.append(GateResult("Gate_06", True, "Spread verified"))

        # Gate 07: Open Interest (OI) Guard
        if not state.oi_ok:
            res = GateResult("Gate_07", False, "Open Interest below threshold")
            results.append(res)
            return False, "Gate_07 failed", results
        results.append(GateResult("Gate_07", True, "OI check passed"))

        # Gate 08: Daily Limit Guard
        if not state.under_daily_cap:
            res = GateResult("Gate_08", False, "Daily trade count/risk cap reached")
            results.append(res)
            return False, "Gate_08 failed", results
        results.append(GateResult("Gate_08", True, "Under daily limit"))

        return True, "Passed all 8 Gates", results

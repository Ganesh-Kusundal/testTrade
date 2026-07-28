"""Shared value constants — single source of truth for the SCALPR domain.

Pure module: only stdlib imports. ``scalpr.domain`` must not depend on
brokers, API, or any other outer layer (domain-independence rule).
"""
from decimal import Decimal

# ── Exchange defaults ────────────────────────────────────────────────
DEFAULT_EXCHANGE = "NSE"

# ── Numeric sentinels ────────────────────────────────────────────────
ZERO = Decimal("0")

# ── Timeout budgets (seconds) ────────────────────────────────────────
DEFAULT_TIMEOUT_S = 15
SHORT_TIMEOUT_S = 5
RECOVERY_TIMEOUT_S = 10

# ── Segment sets ─────────────────────────────────────────────────────
OPTIONABLE_SEGMENTS = frozenset({"NSE_FNO", "BSE_FNO", "IDX_I", "MCX_COMM"})

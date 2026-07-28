"""Kill switch — SCALPR_LIVE_ORDERS env var gates live order placement.

Safety-critical: default boot (no env var) MUST halt all orders. This is the
only way to stop live trading without killing the process.
"""
from __future__ import annotations

import os
from decimal import Decimal
from unittest.mock import MagicMock, patch


def _wire_with_env(live_orders_env: str | None):
    """Call bootstrap.wire() with SCALPR_LIVE_ORDERS set to the given value."""
    env_patch = {} if live_orders_env is None else {"SCALPR_LIVE_ORDERS": live_orders_env}
    with patch.dict(os.environ, env_patch, clear=False):
        # Remove the key entirely if None
        if live_orders_env is None:
            os.environ.pop("SCALPR_LIVE_ORDERS", None)

        from scalpr.api.bootstrap import wire

        gateway = MagicMock()
        gateway.get_positions.return_value = []
        # Pass empty watchlist to avoid strategy construction
        return wire(gateway=gateway, watchlist=[])


class TestKillSwitch:
    def test_default_boot_halts_all_orders(self):
        """Without SCALPR_LIVE_ORDERS, risk gate must be halted."""
        ctx = _wire_with_env(None)
        assert ctx.order_router.risk_gate.halted is True

    def test_env_zero_halts_all_orders(self):
        """SCALPR_LIVE_ORDERS=0 (or any non-'1' value) must halt."""
        for value in ("0", "false", "yes", ""):
            ctx = _wire_with_env(value)
            assert ctx.order_router.risk_gate.halted is True, f"env={value!r} should halt"

    def test_env_one_enables_orders(self):
        """SCALPR_LIVE_ORDERS=1 is the ONLY value that enables live trading."""
        ctx = _wire_with_env("1")
        assert ctx.order_router.risk_gate.halted is False

    def test_halted_gate_rejects_every_order(self):
        """A halted gate must reject any order, regardless of other inputs."""
        from scalpr.domain.order import Order, OrderSide, OrderType

        ctx = _wire_with_env(None)
        gate = ctx.order_router.risk_gate

        order = Order(
            order_id="o1",
            symbol="RELIANCE",
            exchange="NSE",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=10,
            price=Decimal("2500"),
        )
        allowed, reason = gate.check_order(
            order=order,
            positions=[],
            available_margin=Decimal("1000000"),
            required_margin=Decimal("25000"),
            daily_loss=Decimal("0"),
        )
        assert allowed is False
        assert "halt" in reason.lower()

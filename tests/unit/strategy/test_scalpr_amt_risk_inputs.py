"""C2: ScalprAmtStrategy must feed REAL risk inputs to the OrderRouter.

daily_loss comes from live position P&L, portfolio_value from broker
margins; missing risk data blocks the order (fail-closed).
"""
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from scalpr.domain.contracts import Funds
from scalpr.domain.tick import Tick
from scalpr.execution.order_router import OrderRouter
from scalpr.signals.gate_fsm import GateFSM
from scalpr.strategy.scalpr_amt import ScalprAmtStrategy


def _tick(symbol="RELIANCE", ltp="2500"):
    return Tick(
        symbol=symbol, ltp=Decimal(ltp), bid=Decimal(ltp), ask=Decimal(ltp),
        delta_volume=10, cumulative_volume=1000,
        exchange_timestamp=datetime.now(timezone.utc),
    )


def _losing_position(symbol="TCS", realised="-20000", unrealised="-20000"):
    # Different symbol than the strategy's so no "active position" short-circuit
    return SimpleNamespace(
        symbol=symbol, quantity=10,
        realised_pnl=Decimal(realised), unrealised_pnl=Decimal(unrealised),
    )


def _funds(available="500000", total="1000000"):
    return Funds(
        available_margin=Decimal(available),
        used_margin=Decimal("0"),
        total_balance=Decimal(total),
    )


@pytest.fixture
def router():
    r = MagicMock()
    r.gateway = MagicMock()
    return r


@pytest.fixture(autouse=True)
def force_signal(monkeypatch):
    monkeypatch.setattr(GateFSM, "evaluate", lambda state: (True, "test", {}))


def test_real_daily_loss_and_portfolio_value_reach_router(router):
    positions = [_losing_position()]  # 40k total loss > 3% of 1M
    router.gateway.get_positions.return_value = positions
    router.gateway.get_margins.return_value = _funds()

    ScalprAmtStrategy(router, "RELIANCE").on_tick(_tick())

    router.submit_order.assert_called_once()
    kwargs = router.submit_order.call_args.kwargs
    assert kwargs["daily_loss"] == Decimal("40000")
    assert kwargs["portfolio_value"] == Decimal("1000000")
    assert kwargs["available_margin"] == Decimal("500000")


def test_profitable_day_clamps_daily_loss_to_zero(router):
    router.gateway.get_positions.return_value = [
        _losing_position(realised="5000", unrealised="5000")
    ]
    router.gateway.get_margins.return_value = _funds()

    ScalprAmtStrategy(router, "RELIANCE").on_tick(_tick())

    assert router.submit_order.call_args.kwargs["daily_loss"] == Decimal("0")


def test_negative_total_balance_blocks_order(router, caplog):
    router.gateway.get_positions.return_value = []
    router.gateway.get_margins.return_value = _funds(total="-1")

    ScalprAmtStrategy(router, "RELIANCE").on_tick(_tick())

    router.submit_order.assert_not_called()
    assert "risk_inputs_unavailable" in caplog.text


def test_zero_total_balance_blocks_order(router):
    router.gateway.get_positions.return_value = []
    router.gateway.get_margins.return_value = _funds(total="0")

    ScalprAmtStrategy(router, "RELIANCE").on_tick(_tick())

    router.submit_order.assert_not_called()

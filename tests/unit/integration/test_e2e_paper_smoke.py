"""E2E paper smoke: proves the chain tick → strategy → risk → OMS → broker exists.

Everything real except the broker port (autospec'd) and the signal gate
(forced open). No network, runs in the normal suite.
"""
import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import create_autospec

import pytest

from scalpr.brokers.broker_port import IBrokerGateway
from scalpr.domain.fill import Fill
from scalpr.domain.order import OrderSide
from scalpr.domain.tick import Tick
from scalpr.execution.order_router import OrderRouter
from scalpr.oms.order_manager import OrderManager
from scalpr.risk.circuit_breaker import CircuitBreaker
from scalpr.risk.pre_trade import PreTradeRiskGate
from scalpr.signals.gate_fsm import GateFSM
from scalpr.strategy.executor import StrategyExecutor
from scalpr.strategy.scalpr_amt import ScalprAmtStrategy


def test_tick_to_broker_paper_smoke(monkeypatch):
    # Broker port is the only fake: returns a valid Fill for the order the
    # strategy will generate (amt_RELIANCE_1)
    gateway = create_autospec(IBrokerGateway, instance=True)
    gateway.get_positions.return_value = []
    gateway.get_margins.return_value = {
        "available_margin": Decimal("500000"),
        "total_balance": Decimal("1000000"),
    }
    gateway.place_order.return_value = Fill(
        fill_id="f1",
        order_id="amt_RELIANCE_1",
        symbol="RELIANCE",
        side=OrderSide.BUY,
        quantity=50,
        price=Decimal("100"),
        timestamp=datetime.now(timezone.utc),
        exchange="NSE",
    )

    # Force a signal — this test proves the wiring, not the alpha
    monkeypatch.setattr(GateFSM, "evaluate", staticmethod(lambda state: (True, "test", {})))

    order_manager = OrderManager()  # in-memory (repository=None)
    order_router = OrderRouter(
        gateway=gateway,
        risk_gate=PreTradeRiskGate(),
        circuit_breaker=CircuitBreaker(),
        order_manager=order_manager,
    )
    executor = StrategyExecutor()
    executor.register_strategy(ScalprAmtStrategy(order_router, "RELIANCE"))

    # ltp=100 keeps notional (50*100=5000) under the 1% capital-risk cap
    tick = Tick(
        symbol="RELIANCE", ltp=Decimal("100"), bid=Decimal("100"), ask=Decimal("100"),
        delta_volume=10, cumulative_volume=1000,
        exchange_timestamp=datetime.now(timezone.utc),
    )

    asyncio.run(executor.on_tick(tick))

    gateway.place_order.assert_called_once()
    placed = gateway.place_order.call_args.args[0]
    assert placed.symbol == "RELIANCE"
    assert placed.order_id == "amt_RELIANCE_1"

    # OMS persisted the order and its fill
    assert "amt_RELIANCE_1" in order_manager.orders
    assert len(order_manager.fills["amt_RELIANCE_1"]) == 1

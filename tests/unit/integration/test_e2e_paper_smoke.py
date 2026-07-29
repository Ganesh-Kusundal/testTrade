"""E2E paper smoke: proves the chain tick → strategy → risk → OMS → broker exists.

Uses a real SimulatedGateway (not an autospec mock) as the broker port,
so fills, positions, and margins come from the actual paper-trading path.
The signal gate is still forced open — this test proves wiring, not alpha.
No network, runs in the normal suite.
"""
import asyncio
from datetime import datetime, timezone
from decimal import Decimal

from scalpr.domain.clock import SimulatedClock
from scalpr.domain.order import OrderSide
from scalpr.domain.tick import Tick
from scalpr.execution.order_router import OrderRouter
from scalpr.oms.order_manager import OrderManager
from scalpr.risk.circuit_breaker import CircuitBreaker
from scalpr.risk.pre_trade import PreTradeRiskGate
from scalpr.signals.gate_fsm import GateFSM
from scalpr.simulation.simulated_gateway import SimulatedGateway
from scalpr.strategy.executor import StrategyExecutor
from scalpr.strategy.scalpr_amt import ScalprAmtStrategy

T0 = datetime(2026, 1, 5, 9, 15, tzinfo=timezone.utc)


def test_tick_to_broker_paper_smoke(monkeypatch):
    # Real SimulatedGateway — fills, positions, and margins are live
    gateway = SimulatedGateway(
        starting_capital=Decimal("1000000"),
        clock=SimulatedClock(T0),
    )
    gateway.connect()
    gateway.set_ltp("RELIANCE", Decimal("100"))

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

    # SimulatedGateway produced a real fill
    tradebook = gateway.get_tradebook()
    assert len(tradebook) == 1
    fill = tradebook[0]
    assert fill.order_id == "amt_RELIANCE_1"
    assert fill.symbol == "RELIANCE"
    assert fill.side == OrderSide.BUY
    assert fill.quantity == 100

    # OMS persisted the order and its fill
    assert "amt_RELIANCE_1" in order_manager.orders
    assert len(order_manager.fills["amt_RELIANCE_1"]) == 1

    # Position and margins are real (not mocked)
    positions = gateway.get_positions()
    assert len(positions) == 1
    assert positions[0].symbol == "RELIANCE"
    margins = gateway.get_margins()
    assert margins.total_balance > Decimal("0")

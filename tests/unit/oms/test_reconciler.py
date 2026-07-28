"""Broker position reconciliation heartbeat — Bloomberg plan Module 4 (OMS).

Local truth (PortfolioManager) is compared against broker truth
(IBrokerGateway.get_positions) every N seconds; every divergence is
surfaced — never silently corrected.
"""

import asyncio
from decimal import Decimal

from scalpr.domain.instrument import Exchange
from scalpr.domain.position import Position
from scalpr.oms.reconciler import PositionDiscrepancy, PositionReconciler
from scalpr.portfolio.portfolio import PortfolioManager


def _pos(symbol: str, qty: int, avg: str = "100") -> Position:
    return Position(
        symbol=symbol,
        exchange=Exchange.NSE,
        quantity=qty,
        avg_price=Decimal(avg),
        ltp=Decimal(avg),
    )


class _FakeGateway:
    def __init__(self, positions: list[Position]) -> None:
        self._positions = positions
        self.calls = 0
        self.raise_on_call: Exception | None = None

    def get_positions(self) -> list[Position]:
        self.calls += 1
        if self.raise_on_call:
            raise self.raise_on_call
        return self._positions


def _portfolio_with(*positions: Position) -> PortfolioManager:
    pm = PortfolioManager()
    for p in positions:
        pm.positions[p.symbol] = p
    return pm


class TestReconcileOnce:
    def test_matching_books_produce_no_discrepancies(self):
        gw = _FakeGateway([_pos("RELIANCE", 50)])
        rec = PositionReconciler(gw, _portfolio_with(_pos("RELIANCE", 50)))
        assert rec.reconcile_once() == []

    def test_quantity_mismatch_detected(self):
        gw = _FakeGateway([_pos("RELIANCE", 50)])
        rec = PositionReconciler(gw, _portfolio_with(_pos("RELIANCE", 25)))
        result = rec.reconcile_once()
        assert result == [
            PositionDiscrepancy(symbol="RELIANCE", local_quantity=25, broker_quantity=50, kind="QTY_MISMATCH")
        ]

    def test_position_missing_locally_detected(self):
        gw = _FakeGateway([_pos("TCS", 10)])
        rec = PositionReconciler(gw, _portfolio_with())
        assert rec.reconcile_once() == [
            PositionDiscrepancy(symbol="TCS", local_quantity=0, broker_quantity=10, kind="MISSING_LOCAL")
        ]

    def test_position_missing_at_broker_detected(self):
        gw = _FakeGateway([])
        rec = PositionReconciler(gw, _portfolio_with(_pos("TCS", 10)))
        assert rec.reconcile_once() == [
            PositionDiscrepancy(symbol="TCS", local_quantity=10, broker_quantity=0, kind="MISSING_BROKER")
        ]

    def test_flat_on_both_sides_is_not_a_discrepancy(self):
        gw = _FakeGateway([_pos("TCS", 0)])
        rec = PositionReconciler(gw, _portfolio_with(_pos("TCS", 0)))
        assert rec.reconcile_once() == []

    def test_on_discrepancy_callback_invoked(self):
        seen: list[PositionDiscrepancy] = []
        gw = _FakeGateway([_pos("RELIANCE", 50)])
        rec = PositionReconciler(
            gw, _portfolio_with(_pos("RELIANCE", 25)), on_discrepancy=seen.append
        )
        rec.reconcile_once()
        assert len(seen) == 1
        assert seen[0].kind == "QTY_MISMATCH"

    def test_broker_error_does_not_raise(self):
        gw = _FakeGateway([])
        gw.raise_on_call = ConnectionError("broker down")
        rec = PositionReconciler(gw, _portfolio_with(_pos("TCS", 10)))
        # Fail-safe: heartbeat must never crash the trading loop
        assert rec.reconcile_once() == []


class TestHeartbeat:
    async def test_heartbeat_reconciles_periodically(self):
        gw = _FakeGateway([_pos("RELIANCE", 50)])
        rec = PositionReconciler(gw, _portfolio_with(_pos("RELIANCE", 50)), interval_s=0.01)
        rec.start()
        try:
            await asyncio.sleep(0.05)
        finally:
            await rec.stop()
        assert gw.calls >= 2

    async def test_stop_cancels_heartbeat(self):
        gw = _FakeGateway([])
        rec = PositionReconciler(gw, _portfolio_with(), interval_s=0.01)
        rec.start()
        await rec.stop()
        calls_after_stop = gw.calls
        await asyncio.sleep(0.03)
        assert gw.calls == calls_after_stop

    async def test_heartbeat_survives_broker_errors(self):
        gw = _FakeGateway([])
        gw.raise_on_call = ConnectionError("broker down")
        rec = PositionReconciler(gw, _portfolio_with(), interval_s=0.01)
        rec.start()
        try:
            await asyncio.sleep(0.05)
        finally:
            await rec.stop()
        assert gw.calls >= 2  # kept beating despite errors

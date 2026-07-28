"""Broker position reconciliation heartbeat — Bloomberg plan Module 4 (OMS).

Compares local position truth (PortfolioManager) against broker truth
(IBrokerGateway.get_positions) on a periodic heartbeat. Discrepancies
are surfaced via callback + log — NEVER silently auto-corrected: with
real money, a divergent book demands a human/risk-engine decision.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Callable
from dataclasses import dataclass

from scalpr.brokers.broker_port import IBrokerGateway
from scalpr.portfolio.portfolio import PortfolioManager

logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class PositionDiscrepancy:
    """A single local-vs-broker position divergence."""

    symbol: str
    local_quantity: int
    broker_quantity: int
    kind: str  # QTY_MISMATCH | MISSING_LOCAL | MISSING_BROKER


class PositionReconciler:
    """Periodic local-vs-broker position reconciliation (default every 30s)."""

    def __init__(
        self,
        gateway: IBrokerGateway,
        portfolio: PortfolioManager,
        interval_s: float = 30.0,
        on_discrepancy: Callable[[PositionDiscrepancy], None] | None = None,
    ) -> None:
        self._gateway = gateway
        self._portfolio = portfolio
        self._interval_s = interval_s
        self._on_discrepancy = on_discrepancy
        self._task: asyncio.Task | None = None

    def reconcile_once(self) -> list[PositionDiscrepancy]:
        """Compare books once. Fail-safe: a broker error yields [] and a log,
        never an exception into the trading loop."""
        try:
            broker_positions = self._gateway.get_positions()
        except Exception as exc:
            logger.error("Reconciliation skipped: broker positions unavailable: %s", exc)
            return []

        broker_qty = {p.symbol: p.quantity for p in broker_positions}
        local_qty = {p.symbol: p.quantity for p in self._portfolio.positions.values()}

        discrepancies: list[PositionDiscrepancy] = []
        for symbol in sorted(set(broker_qty) | set(local_qty)):
            local = local_qty.get(symbol, 0)
            broker = broker_qty.get(symbol, 0)
            if local == broker:
                continue
            if symbol not in local_qty:
                kind = "MISSING_LOCAL"
            elif symbol not in broker_qty:
                kind = "MISSING_BROKER"
            else:
                kind = "QTY_MISMATCH"
            disc = PositionDiscrepancy(
                symbol=symbol, local_quantity=local, broker_quantity=broker, kind=kind
            )
            discrepancies.append(disc)
            logger.error(
                f"Position discrepancy [{kind}] {symbol}: local={local} broker={broker}"
            )
            if self._on_discrepancy:
                try:
                    self._on_discrepancy(disc)
                except Exception as exc:
                    logger.error("on_discrepancy callback failed for %s: %s", symbol, exc)

        return discrepancies

    def start(self) -> None:
        """Start the reconciliation heartbeat task on the running loop."""
        if self._task is not None and not self._task.done():
            return
        self._task = asyncio.get_event_loop().create_task(self._heartbeat())

    async def stop(self) -> None:
        """Cancel the heartbeat and wait for clean shutdown."""
        if self._task is None:
            return
        self._task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._task
        self._task = None

    async def _heartbeat(self) -> None:
        while True:
            self.reconcile_once()
            await asyncio.sleep(self._interval_s)

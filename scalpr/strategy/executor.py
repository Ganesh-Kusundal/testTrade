from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from scalpr.domain.tick import OHLCV, Tick
from scalpr.observability.metrics import metrics
from scalpr.strategy.strategy_port import IStrategy

logger = logging.getLogger(__name__)


class StrategyExecutor:
    """Orchestrates strategy execution by routing market ticks and bars to registered strategies.

    Features:
    - Async execution with per-strategy timeouts
    - Error isolation (one strategy failure doesn't block others)
    - Metrics tracking for latency and errors
    """

    def __init__(self, timeout_seconds: float = 0.5) -> None:
        self.strategies: list[IStrategy] = []
        self.timeout = timeout_seconds

    def get_strategy_info(self) -> list[dict[str, Any]]:
        """Return list of registered strategies with their identifiers."""
        result = []
        for s in self.strategies:
            info = {"name": s.__class__.__name__, "symbol": getattr(s, "symbol", "unknown")}
            if hasattr(s, "get_status"):
                info.update(s.get_status())
            result.append(info)
        return result

    def register_strategy(self, strategy: IStrategy) -> None:
        self.strategies.append(strategy)

    async def on_tick(self, tick: Tick) -> None:
        """Route incoming tick to all strategies with timeout protection."""
        if not self.strategies:
            return

        # Launch all strategies in parallel with timeouts
        tasks = [
            asyncio.create_task(self._safe_on_tick(strategy, tick))
            for strategy in self.strategies
        ]

        # Wait for all strategies (errors handled per-strategy)
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _safe_on_tick(self, strategy: IStrategy, tick: Tick) -> None:
        """Execute single strategy with timeout and error isolation."""
        start_time = time.time()
        strategy_name = strategy.__class__.__name__

        try:
            # Check if strategy has async on_tick
            if hasattr(strategy, "on_tick_async") and asyncio.iscoroutinefunction(strategy.on_tick_async):
                await asyncio.wait_for(
                    strategy.on_tick_async(tick),
                    timeout=self.timeout
                )
            else:
                # Run sync strategy in thread pool to avoid blocking
                await asyncio.wait_for(
                    asyncio.to_thread(strategy.on_tick, tick),
                    timeout=self.timeout
                )

            # Record success metrics
            latency_ms = (time.time() - start_time) * 1000
            hist = metrics.get_histogram("strategy_execution_latency_ms")
            if hist:
                hist.observe(latency_ms)

        except asyncio.TimeoutError:
            logger.error("Strategy %s timed out after %ss", strategy_name, self.timeout)
            counter = metrics.get_counter("strategy_timeouts")
            if counter:
                counter.increment()

        except Exception as exc:
            logger.exception("Strategy %s error: %s", strategy_name, exc)
            counter = metrics.get_counter("strategy_errors")
            if counter:
                counter.increment()

    async def on_bar(self, bar: OHLCV) -> None:
        """Route incoming candle bar to all strategies with timeout protection."""
        if not self.strategies:
            return

        # Launch all strategies in parallel with timeouts
        tasks = [
            asyncio.create_task(self._safe_on_bar(strategy, bar))
            for strategy in self.strategies
        ]

        # Wait for all strategies (errors handled per-strategy)
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _safe_on_bar(self, strategy: IStrategy, bar: OHLCV) -> None:
        """Execute single strategy bar handler with timeout and error isolation."""
        start_time = time.time()
        strategy_name = strategy.__class__.__name__

        try:
            # Check if strategy has async on_bar
            if hasattr(strategy, "on_bar_async") and asyncio.iscoroutinefunction(strategy.on_bar_async):
                await asyncio.wait_for(
                    strategy.on_bar_async(bar),
                    timeout=self.timeout
                )
            else:
                # Run sync strategy in thread pool to avoid blocking
                await asyncio.wait_for(
                    asyncio.to_thread(strategy.on_bar, bar),
                    timeout=self.timeout
                )

            # Record success metrics
            latency_ms = (time.time() - start_time) * 1000
            hist = metrics.get_histogram("strategy_execution_latency_ms")
            if hist:
                hist.observe(latency_ms)

        except asyncio.TimeoutError:
            logger.error("Strategy %s on_bar timed out after %ss", strategy_name, self.timeout)
            counter = metrics.get_counter("strategy_timeouts")
            if counter:
                counter.increment()

        except Exception as exc:
            logger.exception("Strategy %s on_bar error: %s", strategy_name, exc)
            counter = metrics.get_counter("strategy_errors")
            if counter:
                counter.increment()

"""Historical tick replayer for backtesting and logic debugging.

Extended to support:
- Loading ticks from EventStore for replay
- Session-based replay with checkpoints
- Integration with observability (metrics, tracing)
"""
from __future__ import annotations

import asyncio
import logging

from scalpr.domain.tick import Tick
from scalpr.strategy.executor import StrategyExecutor

logger = logging.getLogger(__name__)


class ReplayEngine:
    """Historical tick replayer for backtesting and logic debugging."""

    def __init__(self, executor: StrategyExecutor, ticks: list[Tick] | None = None, speed_multiplier: float = 1.0) -> None:
        self.executor = executor
        self.ticks = ticks or []
        self.speed_multiplier = speed_multiplier
        self.cursor = 0
        self.is_running = False

    def load_from_events(
        self,
        events: list[tuple[int, object]],
        event_types: tuple[str, ...] = ("TickReceived",),
    ) -> int:
        """Load ticks from event store for replay.

        Args:
            events: List of (sequence_num, event) tuples from EventStore
            event_types: Which event types to extract ticks from

        Returns:
            Number of ticks loaded
        """
        self.ticks = []

        for seq_num, event in events:
            event_type = event.__class__.__name__

            if event_type in event_types and hasattr(event, "tick"):
                self.ticks.append(event.tick)

        self.cursor = 0
        logger.info(f"ReplayEngine: Loaded {len(self.ticks)} ticks from {len(events)} events")
        return len(self.ticks)

    def save_checkpoint(self) -> int:
        """Checkpoint index saving."""
        return self.cursor

    def restore_checkpoint(self, cursor: int) -> None:
        """Checkpoint restoring."""
        if 0 <= cursor < len(self.ticks):
            self.cursor = cursor
            logger.info(f"ReplayEngine: Restored checkpoint to index {cursor}")
        else:
            raise ValueError("Invalid cursor checkpoint position")

    async def start(self) -> None:
        """Start streaming ticks to strategy executor."""
        self.is_running = True
        logger.info(f"ReplayEngine: Starting tick replay of {len(self.ticks)} ticks at {self.speed_multiplier}x speed.")

        while self.is_running and self.cursor < len(self.ticks):
            tick = self.ticks[self.cursor]

            # Send tick to strategy executor (async)
            await self.executor.on_tick(tick)

            # Calculate sleep delay based on tick timestamps (if available)
            if self.cursor < len(self.ticks) - 1:
                next_tick = self.ticks[self.cursor + 1]
                time_delta = (next_tick.exchange_timestamp - tick.exchange_timestamp).total_seconds()

                # Apply speed multiplier
                sleep_delay = max(0.0, time_delta / self.speed_multiplier)
                if sleep_delay > 0:
                    await asyncio.sleep(sleep_delay)

            self.cursor += 1

        self.is_running = False
        logger.info("ReplayEngine: Tick replay finished.")

    def stop(self) -> None:
        self.is_running = False

from __future__ import annotations

from abc import ABC, abstractmethod

from scalpr.domain.tick import OHLCV, Tick


class IStrategy(ABC):
    """Abstract Port representing the contract every strategy must satisfy."""

    @abstractmethod
    def on_tick(self, tick: Tick) -> None:
        """Handle incoming real-time market tick."""
        pass

    @abstractmethod
    def on_bar(self, bar: OHLCV) -> None:
        """Handle completed historical/live candle bar."""
        pass

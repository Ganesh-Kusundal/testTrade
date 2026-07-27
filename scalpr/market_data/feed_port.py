from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable

from scalpr.domain.tick import Tick


class IMarketDataFeed(ABC):
    """Abstract interface defining the market data stream provider (WebSocket)."""

    @abstractmethod
    def connect(self) -> bool:
        """Establish connection with the market data server."""
        pass

    @abstractmethod
    def disconnect(self) -> bool:
        """Terminate connection with the market data server."""
        pass

    @abstractmethod
    def subscribe(self, symbols: list[str]) -> bool:
        """Subscribe to real-time tick feeds for the specified symbols."""
        pass

    @abstractmethod
    def unsubscribe(self, symbols: list[str]) -> bool:
        """Unsubscribe from tick feeds for the specified symbols."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if WebSocket connection is active."""
        pass

    @abstractmethod
    def on_tick(self, callback: Callable[[Tick], None]) -> None:
        """Register callback for incoming tick packets."""
        pass

from __future__ import annotations

from dataclasses import dataclass, field

from scalpr.domain.instrument import MarketFeed


@dataclass
class Subscription:
    """Handle for an active market-data subscription.

    Returned by Gateway.subscribe_feed() and Instrument.subscribe().
    Call Gateway.unsubscribe(subscription) to tear it down.
    """

    id: str
    instruments: list[str]
    mode: MarketFeed
    is_active: bool = True

    def deactivate(self) -> None:
        """Mark this subscription as inactive (does not unsubscribe from broker)."""
        self.is_active = False

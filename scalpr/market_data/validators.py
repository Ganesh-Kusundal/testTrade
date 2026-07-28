from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from scalpr.domain.tick import Tick

logger = logging.getLogger(__name__)


class TickValidator:
    """Validates real-time market ticks for deduplication, staleness, and price sanity."""

    def __init__(self, staleness_threshold_seconds: float = 5.0, price_deviation_limit: float = 0.05):
        self.staleness_threshold = timedelta(seconds=staleness_threshold_seconds)
        self.price_deviation_limit = Decimal(str(price_deviation_limit))

        # State tracking: symbol -> last processed state
        self._last_timestamps: dict[str, datetime] = {}
        self._last_ltps: dict[str, Decimal] = {}

    def validate_tick(self, tick: Tick) -> bool:
        """Validate tick. Returns True if valid, False if rejected."""
        symbol = tick.symbol
        now = datetime.now(timezone.utc)

        # 1. Deduplication by exchange_timestamp
        last_ts = self._last_timestamps.get(symbol)
        if last_ts is not None and tick.exchange_timestamp <= last_ts:
            logger.debug("Tick rejected (duplicate/older timestamp): %s", tick)
            return False

        # 2. Staleness check
        if now - tick.exchange_timestamp > self.staleness_threshold:
            logger.debug("Tick rejected (stale): %s, age: %s", tick, now - tick.exchange_timestamp)
            return False

        # 3. Price sanity check (ltp deviates > 5% from last ltp)
        last_ltp = self._last_ltps.get(symbol)
        if last_ltp is not None and last_ltp > 0:
            deviation = abs(tick.ltp - last_ltp) / last_ltp
            if deviation > self.price_deviation_limit:
                logger.warning("Tick rejected (price anomaly): %s, deviation: %.2%%", tick, deviation)
                return False

        # Update tracking state
        self._last_timestamps[symbol] = tick.exchange_timestamp
        self._last_ltps[symbol] = tick.ltp
        return True

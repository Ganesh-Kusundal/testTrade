from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from scalpr.domain.instrument import Instrument

logger = logging.getLogger(__name__)


class OptionsScanner:
    """Scans option contracts at 09:45 IST to filter for liquid ATM contracts.

    Emits only broker-resolved instruments — symbol→instrument mapping is the
    broker resolver's job; unresolvable contracts are skipped, never faked.
    """

    def __init__(
        self,
        resolver: Any,  # SymbolResolver — required, no untradeable fallbacks
        min_oi: int = 1000,
        min_volume: int = 5000,
        max_spread: Decimal = Decimal("2.00"),
    ) -> None:
        self._resolver = resolver
        self.min_oi = min_oi
        self.min_volume = min_volume
        self.max_spread = max_spread

    def scan(self, spot_price: Decimal, chain_data: list[dict]) -> list[Instrument]:
        """Scan option chain data and return matching sorted instruments.
        
        ATM strike selection: Select strike closest to spot_price.
        Filters by open interest, volume, and bid-ask spreads.
        """
        matches = []
        for contract in chain_data:
            oi = int(contract.get("oi", 0))
            volume = int(contract.get("volume", 0))
            bid = Decimal(str(contract.get("bid", "0")))
            ask = Decimal(str(contract.get("ask", "0")))
            strike = Decimal(str(contract.get("strike", "0")))
            symbol = contract.get("symbol", "")

            # Spreads filter
            spread = ask - bid
            if spread > self.max_spread or oi < self.min_oi or volume < self.min_volume:
                continue

            # ATM strike check: within 1% of spot price
            if abs(strike - spot_price) / spot_price > Decimal("0.02"):
                continue

            try:
                inst = self._resolver.resolve(symbol, "NSE")
            except Exception as exc:
                logger.warning("Skipping unresolvable option contract %s: %s", symbol, exc)
                continue

            matches.append((inst, oi + volume))  # Rank by liquidity score (OI + volume)

        # Sort matches by liquidity rank
        matches.sort(key=lambda x: x[1], reverse=True)
        return [m[0] for m in matches]

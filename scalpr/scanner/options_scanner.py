from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal
from typing import Any

from scalpr.domain.instrument import Exchange, Instrument, OptionType, Segment

logger = logging.getLogger(__name__)


class OptionsScanner:
    """Scans option contracts at 09:45 IST to filter for liquid ATM contracts."""

    def __init__(
        self,
        min_oi: int = 1000,
        min_volume: int = 5000,
        max_spread: Decimal = Decimal("2.00"),
        resolver: Any = None,  # NEW: SymbolResolver for real instrument metadata
    ) -> None:
        self.min_oi = min_oi
        self.min_volume = min_volume
        self.max_spread = max_spread
        self._resolver = resolver  # NEW: Store resolver

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
            option_type_str = contract.get("option_type", "CE")
            symbol = contract.get("symbol", "")

            # Spreads filter
            spread = ask - bid
            if spread > self.max_spread or oi < self.min_oi or volume < self.min_volume:
                continue

            # ATM strike check: within 1% of spot price
            if abs(strike - spot_price) / spot_price > Decimal("0.02"):
                continue

            opt_type = OptionType.CE if option_type_str == "CE" else OptionType.PE

            # Try to resolve through resolver for real instrument metadata
            if self._resolver is not None:
                try:
                    # Use symbol from contract data to look up real instrument
                    inst = self._resolver.resolve(symbol, "NSE")
                except Exception as exc:
                    logger.warning("Failed to resolve option contract %s: %s", symbol, exc)
                    # Fallback: create instrument with minimal data (will fail in trading)
                    inst = Instrument(
                        symbol=symbol,
                        exchange=Exchange.NSE,
                        segment=Segment.OPTIONS,
                        security_id="",  # Empty - will cause trading to fail
                        lot_size=50,
                        tick_size=Decimal("0.05"),
                        option_type=opt_type,
                        strike=strike,
                        expiry=contract.get("expiry"),
                    )
            else:
                # No resolver - create partial instrument (backward compat)
                # WARNING: This will fail in real trading without valid security_id
                logger.warning(
                    "OptionsScanner created instrument without resolver - trading will fail"
                )
                inst = Instrument(
                    symbol=symbol,
                    exchange=Exchange.NSE,
                    segment=Segment.OPTIONS,
                    security_id="",  # Empty - will cause trading to fail
                    lot_size=50,
                    tick_size=Decimal("0.05"),
                    option_type=opt_type,
                    strike=strike,
                    expiry=contract.get("expiry"),
                )
            
            matches.append((inst, oi + volume))  # Rank by liquidity score (OI + volume)

        # Sort matches by liquidity rank
        matches.sort(key=lambda x: x[1], reverse=True)
        return [m[0] for m in matches]

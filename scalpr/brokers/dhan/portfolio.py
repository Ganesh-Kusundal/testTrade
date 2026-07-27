"""Portfolio adapter — positions, holdings, and fund limits.

Provides a clean boundary between Dhan portfolio/positions API responses
and SCALPR domain Position objects. All reads use http_client.get().

As Uncle Bob says: "Clean boundaries between strategy, signals, orders, and risk."
This adapter owns the portfolio boundary — nothing more, nothing less.
"""

from __future__ import annotations

import logging
from decimal import Decimal

from scalpr.brokers.dhan.exceptions import BrokerError
from scalpr.brokers.dhan.http_client import DhanHttpClient
from scalpr.brokers.dhan.mapper import DhanMapper
from scalpr.brokers.dhan.resolver import SymbolResolver
from scalpr.brokers.dhan.segments import SEGMENT_TO_EXCHANGE
from scalpr.domain.instrument import Exchange
from scalpr.domain.position import Position, PositionSide, PositionState

logger = logging.getLogger(__name__)


class PortfolioAdapter:
    """Adapter for Dhan portfolio/positions API to SCALPR domain types.

    Responsibilities:
    - Fetch and convert positions to SCALPR Position domain objects
    - Fetch long-term holdings
    - Fetch fund/margin limits
    - Look up individual positions by symbol + exchange

    Single responsibility: portfolio data access only.
    No order placement, no risk evaluation, no signal generation.
    """

    def __init__(self, client: DhanHttpClient, resolver: SymbolResolver):
        self._client = client
        self._resolver = resolver

    # ------------------------------------------------------------------
    # Public read operations
    # ------------------------------------------------------------------

    def get_positions(self) -> list[Position]:
        """Fetch active (intraday/F&O) positions with P&L.

        Returns:
            List of Position domain objects. Empty list only when the
            broker truthfully reports no positions.

        Raises:
            BrokerError: On API failure — an outage must never look like
            an empty book (C3 fail-closed).
        """
        try:
            data = self._client.get("/positions")
        except Exception as exc:
            logger.warning("get_positions_failed", extra={"error": str(exc)})
            raise BrokerError(f"positions fetch failed: {exc}") from exc

        raw_positions = self._extract_list(data)
        return [self._map_position(p) for p in raw_positions if self._is_open(p)]

    def get_holdings(self) -> list[Position]:
        """Fetch long-term holdings (delivery positions).

        Returns:
            List of Position domain objects for holdings. Empty list only
            when the broker truthfully reports no holdings.

        Raises:
            BrokerError: On API failure (C3 fail-closed).
        """
        try:
            data = self._client.get("/holdings")
        except Exception as exc:
            logger.warning("get_holdings_failed", extra={"error": str(exc)})
            raise BrokerError(f"holdings fetch failed: {exc}") from exc

        raw_holdings = self._extract_list(data)
        return [self._map_holding(h) for h in raw_holdings]

    def get_fund_limits(self) -> dict:
        """Fetch available margin, used margin, and total balance.

        Returns:
            Dict with keys:
            - available_margin (Decimal): Margin available for new trades
            - used_margin (Decimal): Margin currently in use
            - total_balance (Decimal): Total account balance
            - collateral (Decimal): Collateral/margin from holdings
            - realtime (bool): Whether data is real-time or delayed

        Raises:
            BrokerError: On API failure (C3 fail-closed).
        """
        try:
            data = self._client.get("/fundlimit")
        except Exception as exc:
            logger.warning("get_fund_limits_failed", extra={"error": str(exc)})
            raise BrokerError(f"fund limits fetch failed: {exc}") from exc

        return self._map_fund_limits(data)

    def get_position(self, symbol: str, exchange: str) -> Position | None:
        """Look up a single position by symbol and exchange.

        Args:
            symbol: Trading symbol (e.g., "RELIANCE", "NIFTY25JUN22000CE")
            exchange: Exchange code (e.g., "NSE", "MCX")

        Returns:
            Position if found, None if not held or on error.
        """
        positions = self.get_positions()
        exchange_normalized = self._normalise_exchange(exchange)

        for pos in positions:
            if pos.symbol.upper() == symbol.upper() and pos.exchange == exchange_normalized:
                return pos

        return None

    # ------------------------------------------------------------------
    # Mapping helpers
    # ------------------------------------------------------------------

    def _map_position(self, raw: dict) -> Position:
        """Convert a raw Dhan position dict to a SCALPR Position.

        Delegates to DhanMapper for domain conversion, falling back
        to manual mapping if the mapper fails (defensive).
        """
        result = DhanMapper.dhan_position_to_domain(raw)
        if result.is_ok:
            return result.value

        # Fallback: manual mapping if mapper fails
        logger.warning(
            "position_mapper_fallback",
            extra={"error": result.error, "raw_keys": list(raw.keys())},
        )
        return self._map_position_manual(raw)

    def _map_position_manual(self, raw: dict) -> Position:
        """Manual position mapping as fallback.

        Dr. Venkat: "A system that is fast and wrong is more dangerous
        than a system that is slow and right." — better to map manually
        than to lose position data entirely.
        """
        symbol = str(raw.get("symbol", ""))
        exchange = self._normalise_exchange(raw.get("exchange", "NSE"))
        quantity = int(raw.get("quantity", 0))
        avg_price = Decimal(str(raw.get("avgPrice", raw.get("buyPrice", "0"))))
        ltp = Decimal(str(raw.get("ltp", raw.get("lastPrice", "0"))))
        realised_pnl = Decimal(str(raw.get("realizedPnl", raw.get("realisedProfit", "0"))))

        side, state = self._derive_side_and_state(quantity)
        unrealised_pnl = self._calculate_unrealised_pnl(quantity, avg_price, ltp)

        return Position(
            symbol=symbol,
            exchange=exchange,
            quantity=quantity,
            avg_price=avg_price,
            ltp=ltp,
            unrealised_pnl=unrealised_pnl,
            realised_pnl=realised_pnl,
            position_side=side,
            state=state,
        )

    def _map_holding(self, raw: dict) -> Position:
        """Convert a raw Dhan holding dict to a SCALPR Position.

        Holdings are long-term delivery positions. They are treated as
        LONG positions with state OPEN.
        """
        symbol = str(raw.get("symbol", ""))
        exchange = self._normalise_exchange(raw.get("exchange", "NSE"))

        quantity = int(raw.get("quantity", raw.get("totalQty", 0)))
        avg_price = Decimal(str(raw.get("avgPrice", raw.get("buyPrice", "0"))))
        ltp = Decimal(str(raw.get("ltp", raw.get("lastPrice", "0"))))

        # Holdings are always long in delivery
        side = PositionSide.LONG if quantity > 0 else PositionSide.FLAT
        state = PositionState.OPEN if quantity != 0 else PositionState.FLAT

        unrealised_pnl = self._calculate_unrealised_pnl(quantity, avg_price, ltp)
        realised_pnl = Decimal("0")  # Holdings don't have realised P&L

        return Position(
            symbol=symbol,
            exchange=exchange,
            quantity=quantity,
            avg_price=avg_price,
            ltp=ltp,
            unrealised_pnl=unrealised_pnl,
            realised_pnl=realised_pnl,
            position_side=side,
            state=state,
        )

    def _map_fund_limits(self, data: dict) -> dict:
        """Convert Dhan fund limit response to a clean dict.

        Dhan API returns fund limits with various field names.
        We normalise to a consistent SCALPR format.
        """
        # Note: "availabelMargin" is a known Dhan API typo (missing "i") kept for backward compat
        available = Decimal(str(
            data.get("availableBalance", data.get("availabelMargin",
            data.get("availablemargin", "0")))
        ))
        used = Decimal(str(
            data.get("utilizedMargin", data.get("utilisedMargin",
            data.get("usedMargin", data.get("blockedPayoutAmount", "0"))))
        ))
        total = Decimal(str(
            data.get("totalBalance", data.get("totalMargin",
            data.get("totalBalance", "0")))
        ))
        collateral = Decimal(str(
            data.get("collateral", data.get("collateralAmount",
            data.get("collateralValue", "0")))
        ))

        return {
            "available_margin": available,
            "used_margin": used,
            "total_balance": total,
            "collateral": collateral,
            "realtime": data.get("realtime", True),
        }

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_list(data: dict) -> list[dict]:
        """Safely extract a list of records from API response.

        Dhan API may return data in various structures:
        - Direct list: [{...}, {...}]
        - Wrapped: {"data": [{...}, {...}]}
        - Status wrapped: {"status": "success", "data": [{...}]}

        Returns empty list if structure is unexpected.
        """
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            # Try common wrapper keys
            for key in ("data", "positions", "holdings", "records", "result"):
                value = data.get(key)
                if isinstance(value, list):
                    return value
        return []

    @staticmethod
    def _is_open(raw: dict) -> bool:
        """Check if a position record represents an open (non-flat) position."""
        quantity = raw.get("quantity", 0)
        try:
            return int(quantity) != 0
        except (TypeError, ValueError):
            return False

    @staticmethod
    def _derive_side_and_state(quantity: int) -> tuple[PositionSide, PositionState]:
        """Derive PositionSide and PositionState from signed quantity."""
        if quantity > 0:
            return PositionSide.LONG, PositionState.OPEN
        elif quantity < 0:
            return PositionSide.SHORT, PositionState.OPEN
        else:
            return PositionSide.FLAT, PositionState.FLAT

    @staticmethod
    def _calculate_unrealised_pnl(quantity: int, avg_price: Decimal, ltp: Decimal) -> Decimal:
        """Calculate unrealised P&L using Decimal arithmetic.

        Long:  qty * (ltp - avg)
        Short: abs(qty) * (avg - ltp)
        Flat:  0

        Dr. Venkat: precision matters — never use float for P&L.
        """
        if quantity > 0:
            return Decimal(quantity) * (ltp - avg_price)
        elif quantity < 0:
            return Decimal(abs(quantity)) * (avg_price - ltp)
        return Decimal("0")

    @staticmethod
    def _normalise_exchange(exchange: str) -> Exchange:
        """Normalise exchange string to Exchange enum.

        Uses segment mapping for Dhan wire segments, falls back to NSE.
        """
        exchange_str = str(exchange).strip().upper()
        try:
            return Exchange(exchange_str)
        except ValueError:
            mapped = SEGMENT_TO_EXCHANGE.get(exchange_str)
            if mapped:
                try:
                    return Exchange(mapped)
                except ValueError:
                    pass
            return Exchange.NSE

"""Option chain adapter — fetches and flattens Dhan option chain data.

Produces scanner-compatible list[dict] with keys:
symbol, security_id, strike, bid, ask, oi, volume, delta.

Wire contract (verified live 2026-07-27): Dhan v2 expects
``UnderlyingScrip`` / ``UnderlyingSeg`` — ``securityId`` /
``exchangeSegment`` are rejected with HTTP 400 "Invalid SecurityId".
"""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal
from typing import Any

from scalpr.brokers.dhan.http_client import DhanHttpClient
from scalpr.brokers.dhan.resolver import SymbolResolver
from scalpr.brokers.errors import OptionChainNotSupported

logger = logging.getLogger(__name__)

# Wire segments that support option chain queries
_OPTIONABLE_SEGMENTS = frozenset({"NSE_FNO", "BSE_FNO", "IDX_I", "MCX_COMM"})


class OptionChainAdapter:
    """Adapter for fetching option chain data from Dhan API.

    Resolves the underlying instrument, fetches the option chain via
    POST /optionchain, and flattens Dhan's nested response into the
    scanner-compatible ``list[dict]`` shape.
    """

    def __init__(self, client: DhanHttpClient, resolver: SymbolResolver) -> None:
        self._client = client
        self._resolver = resolver
        self._expiry_cache: dict[str, list[date]] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_option_chain(
        self,
        underlying_symbol: str,
        exchange: str,
        expiry: date | None = None,
    ) -> list[dict]:
        """Fetch and flatten the option chain for an underlying.

        Args:
            underlying_symbol: Symbol of the underlying (e.g. "NIFTY", "SENSEX").
            exchange: Exchange code (e.g. "NSE", "BSE").
            expiry: Specific expiry date. If *None*, the next available expiry
                    is resolved automatically via ``/optionchain/expirylist``.

        Returns:
            Flat list of dicts with keys:
            ``symbol, security_id, strike, bid, ask, oi, volume, delta``.
        """
        security_id, segment = self._resolve_underlying(underlying_symbol, exchange)

        if segment not in _OPTIONABLE_SEGMENTS:
            raise OptionChainNotSupported(
                f"Option chain not supported for {underlying_symbol} ({exchange}) "
                f"— only available for indices and F&O instruments"
            )

        if expiry is None:
            expiry = self._resolve_next_expiry(security_id, segment)

        payload = {
            "UnderlyingScrip": security_id,
            "UnderlyingSeg": segment,
            "Expiry": expiry.isoformat(),
        }

        raw = self._client.post("/optionchain", json=payload)
        chain = self._flatten_chain(raw)

        logger.info(
            "option_chain_fetched",
            extra={
                "underlying": underlying_symbol,
                "expiry": expiry.isoformat(),
                "strikes": len(chain),
            },
        )
        return chain

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_underlying(self, symbol: str, exchange: str) -> tuple[int, str]:
        """Resolve underlying to (security_id, wire_segment)."""
        resolved = self._resolver.resolve_full(symbol, exchange)
        return int(resolved.security_id), resolved.wire_segment

    def _resolve_next_expiry(self, security_id: int, segment: str) -> date:
        """Fetch expiry list and return the earliest future expiry."""
        cache_key = f"{security_id}:{segment}"
        today = date.today()

        expiries = self._expiry_cache.get(cache_key)
        if expiries is None:
            raw = self._client.post(
                "/optionchain/expirylist",
                json={"UnderlyingScrip": security_id, "UnderlyingSeg": segment},
            )
            raw_list = raw.get("data", [])
            expiries = sorted({date.fromisoformat(e) for e in raw_list})
            self._expiry_cache[cache_key] = expiries

        # Pick the first expiry that is >= today
        for exp in expiries:
            if exp >= today:
                return exp

        # Fallback: return the last available (may be past expiry)
        if expiries:
            return expiries[-1]

        raise ValueError(f"No expiry dates available for security_id={security_id}")

    @staticmethod
    def _to_decimal(value: Any) -> Decimal:
        """Normalize a wire value to Decimal, defaulting to 0 on bad input.

        Dhan occasionally returns ``None`` for prices on thinly-traded legs;
        coercing to ``Decimal("0")`` keeps downstream math well-defined
        without masking the absence of data (delta stays None).
        """
        if value is None:
            return Decimal("0")
        try:
            return Decimal(str(value))
        except (TypeError, ValueError, ArithmeticError):
            return Decimal("0")

    @staticmethod
    def _to_security_id(value: Any) -> int | None:
        """Normalize security_id to int, or None if absent/malformed."""
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _flatten_chain(raw: dict[str, Any]) -> list[dict]:
        """Flatten Dhan's nested option-chain response to ``list[dict]``.

        Dhan returns ``data.oc`` as a dict keyed by strike price (as string),
        each value containing ``ce`` and ``pe`` sub-dicts with option data
        including greeks. Live responses carry ``security_id`` per leg but
        no ``trading_symbol``, so ``symbol`` may be empty.
        """
        oc = raw.get("data", {}).get("oc", {})
        result: list[dict] = []

        for strike_str, legs in oc.items():
            strike = Decimal(strike_str)
            for leg_key, side in (("ce", "CE"), ("pe", "PE")):
                leg = legs.get(leg_key)
                if leg is None:
                    continue
                greeks = leg.get("greeks", {})
                result.append({
                    "symbol": leg.get("trading_symbol") or "",
                    "security_id": OptionChainAdapter._to_security_id(
                        leg.get("security_id")
                    ),
                    "strike": strike,
                    "bid": OptionChainAdapter._to_decimal(
                        leg.get("top_bid_price")
                    ),
                    "ask": OptionChainAdapter._to_decimal(
                        leg.get("top_ask_price")
                    ),
                    "oi": int(leg.get("oi", 0)),
                    "volume": int(leg.get("volume", 0)),
                    "delta": greeks.get("delta"),  # May be None — leave as-is
                })

        return result

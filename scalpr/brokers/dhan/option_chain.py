"""Option chain adapter — fetches and flattens Dhan option chain data.

Produces scanner-compatible list[dict[str, Any]] with keys:
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
from scalpr.brokers.dhan.resolution import SymbolResolver
from scalpr.brokers.errors import OptionChainNotSupported
from scalpr.domain.values import OPTIONABLE_SEGMENTS, ZERO

logger = logging.getLogger(__name__)


class OptionChainAdapter:
    """Adapter for fetching option chain data from Dhan API.

    Resolves the underlying instrument, fetches the option chain via
    POST /optionchain, and flattens Dhan's nested response into the
    scanner-compatible ``list[dict[str, Any]]`` shape.
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
    ) -> list[dict[str, Any]]:
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

        if segment not in OPTIONABLE_SEGMENTS:
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
        chain = self._flatten_chain(raw, self._resolver)

        logger.info(
            "option_chain_fetched",
            extra={
                "underlying": underlying_symbol,
                "expiry": expiry.isoformat(),
                "strikes": len(chain),
            },
        )
        return chain

    def get_future_symbol(
        self,
        underlying_symbol: str,
        exchange: str,
        expiry_idx: int = 0,
    ) -> str:
        """Get the trading symbol for a future contract.

        Uses the resolver's in-memory instrument index — no API calls.

        Args:
            underlying_symbol: Underlying symbol (e.g. "NIFTY", "RELIANCE").
            exchange: Exchange code (e.g. "NSE").
            expiry_idx: 0 = nearest (next) expiry, 1 = next month, etc.

        Returns:
            Trading symbol string (e.g. "NIFTY 25 JUL 26 FUT").

        Raises:
            ValueError: If no futures exist or expiry_idx is out of range.
        """
        futures = self._resolver.get_futures_for_underlying(
            underlying_symbol, exchange
        )
        if not futures:
            raise ValueError(
                f"No futures found for {underlying_symbol} ({exchange})"
            )
        if expiry_idx >= len(futures):
            raise ValueError(
                f"expiry_idx {expiry_idx} out of range "
                f"(only {len(futures)} future contracts available for "
                f"{underlying_symbol})"
            )
        return futures[expiry_idx].symbol

    def select_strikes(
        self,
        underlying_symbol: str,
        exchange: str,
        expiry: date | None = None,
        mode: str = "ATM",
        count: int = 10,
        spot_price: Decimal | None = None,
    ) -> list[Decimal]:
        """Select option strikes by moneyness (ATM/ITM/OTM).

        Args:
            underlying_symbol: Underlying symbol (e.g. "NIFTY").
            exchange: Exchange code.
            expiry: Specific expiry date (None = next expiry).
            mode: "ATM", "ITM", "OTM", or comma-separated ("ITM,OTM").
            count: Number of strikes per mode direction.
            spot_price: Current spot price. If None, approximated from chain.

        Returns:
            Sorted list of unique Decimal strike prices.
        """
        chain = self.get_option_chain(underlying_symbol, exchange, expiry=expiry)
        if not chain:
            return []

        strikes = sorted({Decimal(str(leg["strike"])) for leg in chain})

        # Determine spot price
        if spot_price is None or spot_price <= 0:
            spot_price = self._approximate_spot_from_chain(chain)

        if spot_price <= 0:
            return strikes[:count]

        # Find ATM strike
        atm = min(strikes, key=lambda s: abs(s - spot_price))
        atm_idx = strikes.index(atm)

        modes = {m.strip().upper() for m in mode.split(",")}
        selected: list[Decimal] = []

        if "ATM" in modes:
            selected.append(atm)

        if "ITM" in modes:
            # ITM calls = strikes below ATM; ITM puts = strikes above ATM
            itm_strikes = strikes[:atm_idx]
            selected.extend(itm_strikes[-count:])

        if "OTM" in modes:
            otm_strikes = strikes[atm_idx + 1:]
            selected.extend(otm_strikes[:count])

        return sorted(set(selected))

    def get_option_greeks(
        self,
        underlying_symbol: str,
        exchange: str,
        strike: Decimal,
        expiry: date,
        option_type: str,
    ) -> dict[str, Any] | None:
        """Get greeks for a specific option leg from the option chain.

        Reuses the existing option chain data which already includes
        delta, theta, gamma, vega — no additional API call needed.

        Args:
            underlying_symbol: Underlying symbol (e.g. "NIFTY").
            exchange: Exchange code.
            strike: Strike price.
            expiry: Expiry date.
            option_type: "CE" or "PE".

        Returns:
            Dict with keys: underlying, strike, expiry, option_type,
            delta, theta, gamma, vega, iv, ltp, oi, volume, bid, ask.
            None if the specific leg is not found.
        """
        chain = self.get_option_chain(underlying_symbol, exchange, expiry=expiry)
        strike_dec = Decimal(str(strike))
        ot = option_type.upper()

        for leg in chain:
            if (
                Decimal(str(leg.get("strike", 0))) == strike_dec
                and leg.get("option_type", "").upper() == ot
            ):
                return {
                    "underlying": underlying_symbol,
                    "strike": strike_dec,
                    "expiry": expiry,
                    "option_type": ot,
                    "delta": leg.get("delta"),
                    "theta": leg.get("theta"),
                    "gamma": leg.get("gamma"),
                    "vega": leg.get("vega"),
                    "iv": leg.get("iv"),
                    "ltp": leg.get("ltp"),
                    "oi": leg.get("oi"),
                    "volume": leg.get("volume"),
                    "bid": leg.get("bid"),
                    "ask": leg.get("ask"),
                }
        return None

    @staticmethod
    def _approximate_spot_from_chain(chain: list[dict[str, Any]]) -> Decimal:
        """Approximate spot price via put-call parity.

        Finds the strike where |CE LTP - PE LTP| is minimised,
        which approximates the ATM strike.
        """
        by_strike: dict[Decimal, dict[str, Decimal]] = {}
        for leg in chain:
            s = Decimal(str(leg["strike"]))
            ot = leg.get("option_type", "")
            ltp_raw = leg.get("ltp", ZERO)
            ltp = ltp_raw if isinstance(ltp_raw, Decimal) else Decimal(str(ltp_raw or 0))
            if s not in by_strike:
                by_strike[s] = {}
            by_strike[s][ot] = ltp

        if not by_strike:
            return ZERO

        return min(
            by_strike.keys(),
            key=lambda s: abs(
                by_strike[s].get("CE", ZERO) - by_strike[s].get("PE", ZERO)
            ),
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_underlying(self, symbol: str, exchange: str) -> tuple[int, str]:
        """Resolve underlying to (security_id, wire_segment).

        Delegates to the resolver, which owns the lookup strategy (direct
        symbol, with a futures-contract fallback for commodity underlyings
        like MCX ``SILVER``). Keeps the fallback logic in one place rather
        than duplicated across adapter code.
        """
        return self._resolver.resolve_underlying_for_options(symbol, exchange)

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
        coercing to ``ZERO`` keeps downstream math well-defined
        without masking the absence of data (delta stays None).
        """
        if value is None:
            return ZERO
        try:
            return Decimal(str(value))
        except (TypeError, ValueError, ArithmeticError):
            return ZERO

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
    def _flatten_chain(
        raw: dict[str, Any], resolver: SymbolResolver | None = None
    ) -> list[dict[str, Any]]:
        """Flatten Dhan's nested option-chain response to ``list[dict[str, Any]]``.

        Dhan returns ``data.oc`` as a dict keyed by strike price (as string),
        each value containing ``ce`` and ``pe`` sub-dicts with option data
        including greeks. Live responses carry ``security_id`` per leg but
        no ``trading_symbol``. To keep the flat form usable for
        ``gw.instrument(leg["symbol"], ...)`` lookups, ``symbol`` is backfilled
        from the resolver by ``security_id`` (falling back to ``""`` when the
        contract is absent from the instrument master).
        """
        oc = raw.get("data", {}).get("oc", {})
        result: list[dict[str, Any]] = []

        for strike_str, legs in oc.items():
            strike = Decimal(strike_str)
            for leg_key, side in (("ce", "CE"), ("pe", "PE")):
                leg = legs.get(leg_key)
                if leg is None:
                    continue
                greeks = leg.get("greeks", {})
                sid = OptionChainAdapter._to_security_id(leg.get("security_id"))
                # Backfill the trading symbol from the resolver so callers can
                # resolve the leg directly via gw.instrument(symbol, exchange).
                symbol = ""
                if sid is not None and resolver is not None:
                    inst = resolver.get_by_security_id(str(sid))
                    if inst is not None:
                        symbol = inst.symbol
                result.append({
                    "symbol": symbol,
                    "security_id": sid,
                    "strike": strike,
                    "option_type": side,
                    "bid": OptionChainAdapter._to_decimal(
                        leg.get("top_bid_price")
                    ),
                    "bid_qty": int(leg.get("top_bid_quantity", 0) or 0),
                    "ask": OptionChainAdapter._to_decimal(
                        leg.get("top_ask_price")
                    ),
                    "ask_qty": int(leg.get("top_ask_quantity", 0) or 0),
                    "oi": int(leg.get("oi", 0)),
                    "previous_oi": int(leg.get("previous_oi", 0) or 0),
                    "volume": int(leg.get("volume", 0)),
                    "iv": leg.get("implied_volatility"),
                    "ltp": OptionChainAdapter._to_decimal(
                        leg.get("last_price")
                    ),
                    "delta": greeks.get("delta"),
                    "theta": greeks.get("theta"),
                    "gamma": greeks.get("gamma"),
                    "vega": greeks.get("vega"),
                })

        return result

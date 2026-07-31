"""Option chain adapter — wraps Dhan's option chain API.

Provides strike selection (ATM/OTM/ITM), expiry listing, and option chain
data retrieval using the adapter-layer DhanHttpClient and SymbolResolver.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

import pandas as pd

from scalpr.adapters.dhan._http import DhanHttpClient
from scalpr.adapters.dhan._resolver import INDEX_STEP_SIZES, SymbolResolver

logger = logging.getLogger(__name__)


class OptionChainError(Exception):
    """Base error for option chain operations."""


class StrikeNotFoundError(OptionChainError):
    """Raised when a strike cannot be found in the option chain."""


# Step sizes now centralized in _resolver.py (INDEX_STEP_SIZES)


class OptionChainAdapter:
    """Adapter for Dhan option chain operations.

    Wraps the Dhan REST API endpoints for option chains, expiry lists,
    and strike selection.
    """

    def __init__(self, http_client: DhanHttpClient, resolver: SymbolResolver) -> None:
        self._http = http_client
        self._resolver = resolver

    # ── Public API ──────────────────────────────────────────────────────────

    def get_option_chain(
        self,
        symbol: str,
        exchange: str,
        expiry: str | None = None,
        as_df: bool = False,
        num_strikes: int = 0,
        debug: bool = False,
    ) -> dict[str, Any] | pd.DataFrame:
        """Fetch the option chain for an underlying symbol.

        Args:
            symbol: Underlying symbol (e.g. "NIFTY", "RELIANCE").
            exchange: Exchange code (e.g. "NSE", "BSE", "MCX").
            expiry: Expiry date string (ISO format). If None, the nearest
                    expiry is resolved automatically.
            as_df: If True, return a DataFrame instead of a dict.
            num_strikes: If > 0, return only this many strikes above and
                         below the ATM strike. 0 returns all.
            debug: If True, log extra details about the chain fetch.

        Returns:
            Dict with keys: ``underlying``, ``exchange``, ``expiry``,
            ``strikes`` (list of strike dicts with ``ce`` and ``pe`` legs).
            If ``as_df=True``, returns a DataFrame with flat columns.
        """
        security_id, segment = self._resolver.resolve_underlying_for_options(
            symbol, exchange
        )

        if expiry is None:
            expiry = self._resolve_nearest_expiry(symbol, exchange)

        payload = {
            "UnderlyingScrip": security_id,
            "UnderlyingSeg": segment,
            "Expiry": expiry,
        }

        if debug:
            logger.info("get_option_chain: symbol=%s exchange=%s expiry=%s num_strikes=%d", symbol, exchange, expiry, num_strikes)

        raw = self._http.post("/optionchain", data=payload)

        chain = self._build_chain(raw, symbol, exchange)

        if num_strikes > 0:
            ltp = self._ltp_for(symbol, exchange)
            sorted_entries = sorted(chain, key=lambda x: x["strike"])
            strike_vals = [e["strike"] for e in sorted_entries]
            atm_idx = min(range(len(strike_vals)), key=lambda i: abs(strike_vals[i] - ltp))
            start = max(0, atm_idx - num_strikes)
            end = min(len(sorted_entries), atm_idx + num_strikes + 1)
            chain = sorted_entries[start:end]
            if debug:
                logger.info("num_strikes_filter: ltp=%s atm_idx=%s start=%s end=%s total_after=%s", ltp, atm_idx, start, end, len(chain))

        if debug:
            logger.info("get_option_chain_result: strikes=%d", len(chain))

        if as_df:
            cols = [
                "strike",
                "ce_ltp", "ce_bid", "ce_ask", "ce_iv",
                "ce_delta", "ce_gamma", "ce_theta", "ce_vega",
                "pe_ltp", "pe_bid", "pe_ask", "pe_iv",
                "pe_delta", "pe_gamma", "pe_theta", "pe_vega",
            ]
            rows = []
            for s in chain:
                row = {"strike": s["strike"]}
                for side, prefix in (("ce", "ce_"), ("pe", "pe_")):
                    leg = s.get(side)
                    for field in ("ltp", "bid", "ask", "iv", "delta", "gamma", "theta", "vega"):
                        row[f"{prefix}{field}"] = leg.get(field) if leg else None
                rows.append(row)
            return pd.DataFrame(rows, columns=cols)

        return {
            "underlying": symbol,
            "exchange": exchange,
            "expiry": expiry,
            "strikes": chain,
        }

    def get_expiry_list(self, symbol: str, exchange: str, as_series: bool = False) -> list[str] | pd.Series:
        """Get list of available expiry dates for an option symbol.

        Args:
            symbol: Underlying symbol.
            exchange: Exchange code.
            as_series: If True, return a pandas Series instead of a list.

        Returns:
            List of ISO-formatted expiry date strings, sorted ascending.
        """
        security_id, segment = self._resolver.resolve_underlying_for_options(
            symbol, exchange
        )

        raw = self._http.post(
            "/optionchain/expirylist",
            data={"UnderlyingScrip": security_id, "UnderlyingSeg": segment},
        )

        expiries: list[str] = raw.get("data", [])
        result = sorted(expiries)
        if as_series:
            return pd.Series(result)
        return result

    def atm_strike_selection(
        self,
        symbol: str,
        expiry_idx: int = 0,
        exchange: str = "NSE",
    ) -> tuple[str, str, float]:
        """Select ATM strike for a symbol.

        Steps: get LTP, round to nearest step, find CE/PE at that strike.

        Args:
            symbol: Underlying symbol.
            expiry_idx: Index into expiry list (0 = nearest).

        Returns:
            Tuple of (ce_symbol, pe_symbol, atm_strike_price).

        Raises:
            StrikeNotFoundError: If the ATM strike cannot be resolved.
        """
        ltp = self._ltp_for(symbol, exchange)
        step = self._step_size_for(symbol)
        atm_strike = self._round_to_step(ltp, step)

        expiry = self._resolve_expiry_at(symbol, expiry_idx)
        chain = self.get_option_chain(symbol, exchange, expiry=expiry)
        return self._extract_strike(chain, atm_strike)

    def otm_strike_selection(
        self,
        symbol: str,
        expiry_idx: int = 0,
        count: int = 1,
        exchange: str = "NSE",
    ) -> tuple[str, str, float, float]:
        """Select OTM strikes.

        OTM call = strike above ATM, OTM put = strike below ATM.

        Returns:
            Tuple of (ce_symbol, pe_symbol, ce_strike, pe_strike).
        """
        ltp = self._ltp_for(symbol)
        step = self._step_size_for(symbol)
        atm_strike = self._round_to_step(ltp, step)

        expiry = self._resolve_expiry_at(symbol, expiry_idx)
        chain = self.get_option_chain(symbol, "NSE", expiry=expiry)

        strikes = sorted({s["strike"] for s in chain.get("strikes", [])})
        atm_idx = self._find_nearest_index(strikes, atm_strike)

        ce_idx = min(atm_idx + count, len(strikes) - 1)
        pe_idx = max(atm_idx - count, 0)

        ce_strike = strikes[ce_idx]
        pe_strike = strikes[pe_idx]

        ce_sym = self._symbol_for_strike(chain, ce_strike, "ce")
        pe_sym = self._symbol_for_strike(chain, pe_strike, "pe")

        return (ce_sym, pe_sym, ce_strike, pe_strike)

    def itm_strike_selection(
        self,
        symbol: str,
        expiry_idx: int = 0,
        count: int = 1,
        exchange: str = "NSE",
    ) -> tuple[str, str, float, float]:
        """Select ITM strikes.

        ITM call = strike below ATM, ITM put = strike above ATM.

        Returns:
            Tuple of (ce_symbol, pe_symbol, ce_strike, pe_strike).
        """
        ltp = self._ltp_for(symbol, exchange)
        step = self._step_size_for(symbol)
        atm_strike = self._round_to_step(ltp, step)

        expiry = self._resolve_expiry_at(symbol, expiry_idx)
        chain = self.get_option_chain(symbol, exchange, expiry=expiry)

        strikes = sorted({s["strike"] for s in chain.get("strikes", [])})
        atm_idx = self._find_nearest_index(strikes, atm_strike)

        ce_idx = max(atm_idx - count, 0)
        pe_idx = min(atm_idx + count, len(strikes) - 1)

        ce_strike = strikes[ce_idx]
        pe_strike = strikes[pe_idx]

        ce_sym = self._symbol_for_strike(chain, ce_strike, "ce")
        pe_sym = self._symbol_for_strike(chain, pe_strike, "pe")

        return (ce_sym, pe_sym, ce_strike, pe_strike)

    def get_option_greeks(
        self,
        security_id: str,
        exchange_segment: str,
        strike: float | None = None,
        expiry: str | None = None,
        option_type: str | None = None,
    ) -> dict[str, Any]:
        """Get option greeks for a specific contract.

        Args:
            security_id: Dhan security ID.
            exchange_segment: Wire segment (e.g. "NSE_FNO").
            strike: Strike price for filtering.
            expiry: Expiry date string.
            option_type: "CE" or "PE".

        Returns:
            Dict with keys: delta, gamma, theta, vega, iv.
            Empty dict if greeks are not available.
        """
        payload: dict[str, Any] = {
            "UnderlyingScrip": security_id,
            "UnderlyingSeg": exchange_segment,
        }
        if expiry:
            payload["Expiry"] = expiry

        try:
            raw = self._http.post("/optionchain", data=payload)
        except Exception:
            return {}

        oc = raw.get("data", {}).get("oc", {})
        for strike_str, legs in oc.items():
            if strike is not None and abs(float(strike_str) - strike) > 0.001:
                continue
            for leg_key, ot in (("ce", "CE"), ("pe", "PE")):
                if option_type is not None and ot != option_type.upper():
                    continue
                leg = legs.get(leg_key)
                if leg is None:
                    continue
                greeks = leg.get("greeks", {})
                return {
                    "delta": greeks.get("delta"),
                    "gamma": greeks.get("gamma"),
                    "theta": greeks.get("theta"),
                    "vega": greeks.get("vega"),
                    "iv": leg.get("implied_volatility"),
                }
        return {}

    # ── Internal helpers ────────────────────────────────────────────────────

    def _step_size_for(self, symbol: str) -> float:
        """Get the strike interval step size for a symbol.

        Uses centralized INDEX_STEP_SIZES from _resolver.py.
        Falls back to resolver's tick_size for unknown symbols.
        """
        sym_upper = symbol.upper().strip()
        known = INDEX_STEP_SIZES.get(sym_upper)
        if known is not None:
            return known

        try:
            inst = self._resolver.resolve(symbol, "NSE")
            tick = inst.tick_size
            if tick is not None:
                return float(tick)
        except Exception:
            logger.debug("option_chain_fetch_failed", exc_info=True)

        return 5.0

    def _ltp_for(self, symbol: str, exchange: str = "NSE") -> float:
        """Get current last traded price via the market feed quote endpoint."""
        resolved = self._resolver.resolve_full(symbol, exchange)
        raw = self._http.post(
            "/marketfeed/quote",
            data={
                "security_ids": [resolved.security_id],
                "exchangeSegment": resolved.wire_segment,
            },
            bucket="market_data",
        )

        ltp_str = raw.get("last_price")
        if ltp_str is None:
            raise OptionChainError(f"No LTP available for {symbol}")
        return float(ltp_str)

    def _resolve_nearest_expiry(self, symbol: str, exchange: str) -> str:
        """Fetch and return the nearest expiry date."""
        expiries = self.get_expiry_list(symbol, exchange)
        if not expiries:
            raise OptionChainError(f"No expiries available for {symbol} ({exchange})")
        return expiries[0]

    def _resolve_expiry_at(self, symbol: str, expiry_idx: int) -> str:
        """Resolve expiry at a given index from the expiry list."""
        expiries = self.get_expiry_list(symbol, "NSE")
        if not expiries:
            raise OptionChainError(f"No expiries available for {symbol}")
        idx = min(expiry_idx, len(expiries) - 1)
        return expiries[idx]

    def _build_chain(
        self,
        raw: dict[str, Any],
        symbol: str,
        exchange: str,
    ) -> list[dict[str, Any]]:
        """Flatten Dhan's nested option chain response into a structured list."""
        oc = raw.get("data", {}).get("oc", {})
        result: list[dict[str, Any]] = []

        for strike_str, legs in oc.items():
            strike_val = float(strike_str)
            ce_leg = legs.get("ce")
            pe_leg = legs.get("pe")

            entry: dict[str, Any] = {"strike": strike_val}

            for side, leg in (("ce", ce_leg), ("pe", pe_leg)):
                if leg is None:
                    continue
                greeks = leg.get("greeks", {})
                entry[side] = {
                    "security_id": leg.get("security_id"),
                    "ltp": float(leg.get("last_price", 0) or 0),
                    "bid": float(leg.get("top_bid_price", 0) or 0),
                    "ask": float(leg.get("top_ask_price", 0) or 0),
                    "oi": int(leg.get("oi", 0)),
                    "volume": int(leg.get("volume", 0)),
                    "iv": leg.get("implied_volatility"),
                    "delta": greeks.get("delta"),
                    "theta": greeks.get("theta"),
                    "gamma": greeks.get("gamma"),
                    "vega": greeks.get("vega"),
                }

            result.append(entry)

        return result

    def _extract_strike(
        self,
        chain: dict[str, Any],
        strike: float,
    ) -> tuple[str, str, float]:
        """Extract CE and PE symbols for a given strike from the chain.

        Returns:
            Tuple of (ce_symbol, pe_symbol, strike_price).
        """
        for entry in chain.get("strikes", []):
            if abs(entry["strike"] - strike) < 0.001:
                ce_sym = self._resolve_symbol(entry, "ce")
                pe_sym = self._resolve_symbol(entry, "pe")
                return (ce_sym, pe_sym, entry["strike"])

        raise StrikeNotFoundError(
            f"Strike {strike} not found in option chain"
        )

    def _symbol_for_strike(
        self,
        chain: dict[str, Any],
        strike: float,
        side: str,
    ) -> str:
        """Resolve a single option symbol at a given strike and side."""
        for entry in chain.get("strikes", []):
            if abs(entry["strike"] - strike) < 0.001:
                return self._resolve_symbol(entry, side)
        return ""

    def _resolve_symbol(self, entry: dict[str, Any], side: str) -> str:
        """Resolve a trading symbol from a security_id in the chain entry."""
        leg = entry.get(side)
        if leg is None:
            return ""
        sid = leg.get("security_id")
        if sid is None:
            return ""
        inst = self._resolver.get_by_security_id(str(sid))
        return inst.symbol if inst else ""

    @staticmethod
    def _filter_strikes(
        data: list[dict[str, Any]],
        condition_fn: Callable[[dict[str, Any]], bool],
    ) -> list[dict[str, Any]]:
        """Filter option chain data by a condition function."""
        return [entry for entry in data if condition_fn(entry)]

    @staticmethod
    def _round_to_step(value: float, step: float) -> float:
        """Round a value to the nearest step interval (half up)."""
        return int(value / step + 0.5) * step

    @staticmethod
    def _find_nearest_index(strikes: list[float], target: float) -> int:
        """Find index of the strike closest to target."""
        return min(range(len(strikes)), key=lambda i: abs(strikes[i] - target))

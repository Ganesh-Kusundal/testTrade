"""Instrument handle — scoped operations on a resolved instrument.

Returned by Gateway.instrument(). Bundles a ResolvedInstrument with
references to the adapter stack for data operations.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from scalpr.brokers.errors import OptionChainNotSupported
from scalpr.domain.instrument import ResolvedInstrument
from scalpr.domain.values import DEFAULT_TIMEOUT_S, OPTIONABLE_SEGMENTS


class InstrumentHandle:
    """Scoped operations on a single resolved instrument.

    Usage::

        tcs = gw.instrument("TCS:NSE")
        candles = tcs.historical(interval="1D", start="2025-01-01")
        quote = tcs.quote()
        price = tcs.ltp()
    """

    def __init__(
        self,
        resolved: ResolvedInstrument,
        market_data_adapter: Any,
        historical_adapter: Any,
        option_chain_adapter: Any = None,
        ws_manager: Any = None,
        ws_loop: Any = None,
    ) -> None:
        self._resolved = resolved
        self._market_data = market_data_adapter
        self._historical = historical_adapter
        self._option_chain = option_chain_adapter
        self._ws_manager = ws_manager
        self._ws_loop = ws_loop

    @property
    def resolved(self) -> ResolvedInstrument:
        return self._resolved

    @property
    def symbol(self) -> str:
        return self._resolved.trading_symbol

    @property
    def exchange(self) -> str:
        return self._resolved.exchange.value

    @property
    def security_id(self) -> str:
        return self._resolved.security_id

    @property
    def id(self):
        """Instrument identity (SimpleInstrumentId or DerivativeInstrumentId)."""
        return self._resolved.instrument_id

    def ltp(self) -> Decimal:
        """Get current last traded price (uses pre-resolved security_id)."""
        return self._market_data.get_ltp_by_id(
            self._resolved.security_id,
            self._resolved.wire_segment,
            symbol=self.symbol,
        )

    def quote(self) -> dict[str, Any]:
        """Get full quote with all fields (uses pre-resolved security_id)."""
        return self._market_data.get_quote_by_id(
            self._resolved.security_id,
            self._resolved.wire_segment,
            symbol=self.symbol,
        )

    def ohlc(self) -> dict[str, Any]:
        """Get today's OHLC from the live quote.

        Returns:
            Dict with keys: open, high, low, close, ltp, volume, change, change_percent
        """
        q = self.quote()
        return {
            "open": q.get("open"),
            "high": q.get("high"),
            "low": q.get("low"),
            "close": q.get("close"),
            "ltp": q.get("ltp"),
            "volume": q.get("volume"),
            "change": q.get("change"),
            "change_percent": q.get("change_percent"),
        }

    def depth(self, levels: int = 5) -> dict[str, Any]:
        """Get market depth (REST supports exactly 5 levels; use the
        WebSocket full mode for 20-level depth)."""
        if levels != 5:
            raise ValueError(
                f"REST depth supports exactly 5 levels, got {levels}. "
                "Use subscribe_feed(MarketFeed.FULL, ...) for 20-level depth."
            )
        return self._market_data.get_depth_by_id(
            self._resolved.security_id,
            self._resolved.wire_segment,
            symbol=self.symbol,
        )

    def historical(
        self,
        interval: str = "1D",
        start: date | datetime | str | None = None,
        end: date | datetime | str | None = None,
        as_json: bool = False,
    ) -> Any:
        """Fetch historical OHLCV candles.

        Args:
            interval: Candle interval (e.g. "1D", "5m", "1h")
            start: Start date (defaults to 90 days ago)
            end: End date (defaults to today)
            as_json: If True, return list[dict]. Default returns pandas DataFrame
                     with IST-indexed timestamps.

        Returns:
            pandas.DataFrame (default) with columns:
                open, high, low, close, volume — indexed by timestamp (IST).
            Or list[dict] if as_json=True.
        """
        import pandas as pd

        # Parse string dates FIRST so defaults derive from the real end date
        if isinstance(start, str):
            start = date.fromisoformat(start)
        if isinstance(end, str):
            end = date.fromisoformat(end)

        if end is None:
            end = date.today()
        if start is None:
            end_d = end.date() if isinstance(end, datetime) else end
            start = end_d - timedelta(days=90)

        candles = self._historical.get_ohlcv(
            self.symbol,
            self.exchange,
            interval,
            start,
            end,
        )

        if as_json:
            return candles

        if not candles:
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

        df = pd.DataFrame(candles)
        df.set_index("timestamp", inplace=True)
        df.sort_index(inplace=True)
        return df

    def option_chain(
        self,
        expiry: date | None = None,
        moneyness: str = "all",
        strikes_around: int | None = None,
        option_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch the option chain with optional moneyness filtering.

        Only available for indices and F&O instruments. Raises
        OptionChainNotSupported for plain equities (NSE_EQ / BSE_EQ).

        Args:
            expiry: Specific expiry date. If None, next expiry is used.
            moneyness: Filter by moneyness relative to current spot price.
                "all" (default) — return every leg.
                "ATM" — strikes within 0.5% of spot.
                "ITM" — in-the-money legs only.
                "OTM" — out-of-the-money legs only.
                Combinations: "ATM,ITM", "ITM,OTM", etc.
            strikes_around: If set, return only N strikes on each side of ATM.
                E.g. strikes_around=3 returns 3 ITM + ATM + 3 OTM per type.
            option_type: Filter by leg type: "CE", "PE", or None for both.

        Returns:
            List of dicts with keys:
            symbol, security_id, strike, bid, ask, oi, volume, delta,
            option_type (CE/PE), moneyness (ATM/ITM/OTM), spot_price
        """
        wire_seg = self._resolved.wire_segment
        if wire_seg not in OPTIONABLE_SEGMENTS:
            raise OptionChainNotSupported(
                f"Option chain not supported for {self.symbol} ({self.exchange}) "
                f"— only available for indices and F&O instruments"
            )
        if self._option_chain is None:
            raise OptionChainNotSupported(
                f"Option chain adapter not available for {self.symbol}"
            )

        chain = self._option_chain.get_option_chain(
            self.symbol,
            self.exchange,
            expiry=expiry,
        )

        # No filtering requested — return raw chain
        if moneyness == "all" and strikes_around is None and option_type is None:
            return chain

        # Get spot price for moneyness classification
        try:
            spot = Decimal(str(self._market_data.get_ltp_by_id(
                self._resolved.security_id,
                self._resolved.wire_segment,
                symbol=self.symbol,
            )))
        except Exception:
            # If we can't get spot price, return unfiltered chain
            return chain

        # Parse moneyness filter
        requested = {m.strip().upper() for m in moneyness.split(",")} if moneyness != "all" else {"ATM", "ITM", "OTM"}

        # Classify each leg
        enriched: list[dict[str, Any]] = []
        for leg in chain:
            strike = Decimal(str(leg.get("strike", 0)))
            opt_type = leg.get("option_type", "")

            # Determine moneyness of this leg
            if spot <= 0:
                leg_moneyness = "ATM"
            else:
                pct = abs(strike - spot) / spot
                if pct <= Decimal("0.005"):  # within 0.5% = ATM
                    leg_moneyness = "ATM"
                elif opt_type == "CE":
                    leg_moneyness = "ITM" if strike < spot else "OTM"
                else:  # PE
                    leg_moneyness = "ITM" if strike > spot else "OTM"

            if leg_moneyness not in requested:
                continue

            # Enrich the leg with classification
            enriched_leg = dict(leg)
            enriched_leg["moneyness"] = leg_moneyness
            enriched_leg["spot_price"] = spot
            enriched_leg["option_type"] = opt_type
            enriched.append(enriched_leg)

        # Apply strikes_around filter: N strikes each side of ATM
        if strikes_around is not None and enriched:
            # Group by option_type, sort by distance from ATM
            atm_strike = min(
                (Decimal(str(leg["strike"])) for leg in enriched),
                key=lambda s: abs(s - spot),
            )
            # Get unique strikes sorted by distance from ATM
            unique_strikes = sorted(
                {Decimal(str(leg["strike"])) for leg in enriched},
                key=lambda s: (abs(s - spot), s),
            )
            # Pick N around ATM
            atm_idx = next(
                (i for i, s in enumerate(unique_strikes) if s == atm_strike),
                len(unique_strikes) // 2,
            )
            lo = max(0, atm_idx - strikes_around)
            hi = min(len(unique_strikes), atm_idx + strikes_around + 1)
            selected_strikes = set(unique_strikes[lo:hi])
            enriched = [leg for leg in enriched if Decimal(str(leg["strike"])) in selected_strikes]

        # Apply option_type filter
        if option_type is not None:
            ot = option_type.upper()
            enriched = [leg for leg in enriched if leg.get("option_type", "").upper() == ot]

        return enriched

    def subscribe(
        self,
        mode: Any,
        on_event: Any,
    ) -> None:
        """Subscribe to live market data for this instrument.

        Args:
            mode: MarketFeed enum (LTP, QUOTE, or FULL)
            on_event: Callback for market events
        """
        if self._ws_manager is None or self._ws_loop is None:
            raise RuntimeError(
                "WebSocket manager not available. "
                "Ensure the Gateway was initialised with streaming support."
            )
        import asyncio
        pair = (self.symbol, self.exchange)
        asyncio.run_coroutine_threadsafe(
            self._ws_manager.subscribe_pairs(
                [pair],
                mode=mode.value if hasattr(mode, "value") else str(mode),
            ),
            self._ws_loop,
        ).result(timeout=DEFAULT_TIMEOUT_S)
        if on_event:
            self._ws_manager.add_subscriber(on_event)

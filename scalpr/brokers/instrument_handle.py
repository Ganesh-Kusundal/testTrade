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

    @property
    def lot_size(self) -> int | None:
        """Lot size for this instrument (from resolver at resolve time)."""
        return self._resolved.lot_size

    @property
    def expiry(self) -> date | None:
        """Expiry date for derivative instruments, None for cash."""
        return self._resolved.expiry

    def expiry_list(self) -> list[date]:
        """Fetch available expiry dates for this instrument.

        Only available for optionable instruments (indices, F&O).
        Returns sorted list of future expiry dates.

        Raises:
            OptionChainNotSupported: If instrument is not optionable.
        """
        if self._option_chain is None:
            raise OptionChainNotSupported(
                f"Expiry list not available for {self.symbol} "
                f"— only available for indices and F&O instruments"
            )
        # Access the adapter's cached expiry list
        cache_key = f"{self._resolved.security_id}:{self._resolved.wire_segment}"
        cached = self._option_chain._expiry_cache.get(cache_key)
        if cached:
            return list(cached)
        # Force a fetch by resolving next expiry (populates cache)
        self._option_chain._resolve_next_expiry(
            int(self._resolved.security_id),
            self._resolved.wire_segment,
        )
        return list(self._option_chain._expiry_cache.get(cache_key, []))

    def future_script(self, expiry_idx: int = 0) -> str:
        """Get the future trading symbol for this underlying instrument.

        Args:
            expiry_idx: Index into sorted future expiry list.
                0 = nearest (next) month, 1 = next month, etc.

        Returns:
            Trading symbol string (e.g. "NIFTY 25 JUL 26 FUT").

        Raises:
            OptionChainNotSupported: If instrument is not optionable.
            ValueError: If expiry_idx is out of range.
        """
        if self._option_chain is None:
            raise OptionChainNotSupported(
                f"Future script not available for {self.symbol} "
                f"— only available for indices and F&O instruments"
            )
        return self._option_chain.get_future_symbol(
            self.symbol, self.exchange, expiry_idx
        )

    def strike_selection(
        self,
        expiry_idx: int = 0,
        mode: str = "ATM",
        count: int = 10,
    ) -> list:
        """Select option strikes by moneyness (ATM/ITM/OTM).

        Args:
            expiry_idx: 0=nearest expiry, 1=next, etc.
            mode: "ATM", "ITM", "OTM", or combined ("ITM,OTM").
            count: Strikes per mode direction.

        Returns:
            Sorted list of Decimal strike prices.
        """
        if self._option_chain is None:
            raise OptionChainNotSupported(
                f"Strike selection not available for {self.symbol}"
            )
        # Get spot price from market data
        spot = self._get_spot_for_chain()
        # Resolve expiry from the adapter's expiry cache
        wire_seg = self._resolved.wire_segment
        cache_key = f"{self._resolved.security_id}:{wire_seg}"
        self._option_chain._resolve_next_expiry(
            int(self._resolved.security_id), wire_seg
        )
        expiries = self._option_chain._expiry_cache.get(cache_key, [])
        if expiry_idx >= len(expiries):
            raise ValueError(
                f"expiry_idx {expiry_idx} out of range "
                f"(only {len(expiries)} expiries available)"
            )
        expiry = expiries[expiry_idx]
        return self._option_chain.select_strikes(
            self.symbol, self.exchange, expiry=expiry,
            mode=mode, count=count, spot_price=spot,
        )

    def option_greeks(
        self,
        strike: Decimal,
        expiry: date,
        option_type: str,
    ) -> dict[str, Any] | None:
        """Get greeks for a specific option on this underlying.

        Args:
            strike: Strike price.
            expiry: Expiry date.
            option_type: "CE" or "PE".

        Returns:
            Dict with greeks (delta, theta, gamma, vega, iv) and market
            data, or None if the leg is not found.
        """
        if self._option_chain is None:
            raise OptionChainNotSupported(
                f"Option greeks not available for {self.symbol}"
            )
        return self._option_chain.get_option_greeks(
            self.symbol, self.exchange, strike, expiry, option_type
        )

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
            start: Start date (defaults to 365 days ago — matches Tradehull)
            end: End date (defaults to today)
            as_json: If True, return list[dict]. Default returns pandas DataFrame
                     with IST-indexed timestamps.

        Returns:
            pandas.DataFrame (default) with columns:
                open, high, low, close, volume — indexed by timestamp (IST).
            Or list[dict] if as_json=True.

        Note:
            For daily candles, today's partial session is appended from the
            live quote when the API hasn't produced today's candle yet (i.e.
            market is still open or just opened).
        """
        import pandas as pd

        # Track whether user provided end explicitly
        _end_explicit = end is not None

        # Parse string dates FIRST so defaults derive from the real end date
        if isinstance(start, str):
            start = date.fromisoformat(start)
        if isinstance(end, str):
            end = date.fromisoformat(end)

        if end is None:
            end = date.today()
        if start is None:
            end_d = end.date() if isinstance(end, datetime) else end
            start = end_d - timedelta(days=365)

        candles = self._historical.get_ohlcv(
            self.symbol,
            self.exchange,
            interval,
            start,
            end,
        )

        # ── Append today's partial candle for daily timeframe ──────────
        # When the API hasn't produced today's candle yet (market still open),
        # synthesise one from the live quote so the DataFrame includes today.
        if (
            not _end_explicit
            and interval == "1D"
            and candles
            and end == date.today()
        ):
            last_ts = candles[-1].get("timestamp")
            if isinstance(last_ts, datetime):
                last_date = last_ts.date()
            elif isinstance(last_ts, date):
                last_date = last_ts
            else:
                last_date = None  # string or unknown — skip today-candle logic
            if last_date is not None and last_date < date.today():
                today_candle = self._today_candle_from_quote()
                if today_candle is not None:
                    candles.append(today_candle)

        if as_json:
            return candles

        if not candles:
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

        df = pd.DataFrame(candles)
        df.set_index("timestamp", inplace=True)
        df.sort_index(inplace=True)
        return df

    def _today_candle_from_quote(self) -> dict[str, Any] | None:
        """Build today's partial candle from the live quote.

        Returns None if the quote cannot be fetched (market closed, error, etc).
        """
        from zoneinfo import ZoneInfo

        _IST = ZoneInfo("Asia/Kolkata")
        try:
            q = self._market_data.get_quote_by_id(
                self._resolved.security_id,
                self._resolved.wire_segment,
                symbol=self.symbol,
            )
        except Exception:
            return None

        today = date.today()
        now_ist = datetime.now(tz=_IST)
        ts = datetime(today.year, today.month, today.day,
                      now_ist.hour, now_ist.minute, now_ist.second,
                      tzinfo=_IST)

        o = q.get("open")
        h = q.get("high")
        lo = q.get("low")
        c = q.get("ltp") or q.get("close")
        v = q.get("volume", 0)

        if o is None or c is None:
            return None

        return {
            "timestamp": ts,
            "open": Decimal(str(o)) if not isinstance(o, Decimal) else o,
            "high": Decimal(str(h)) if h is not None and not isinstance(h, Decimal) else (h or Decimal("0")),
            "low": Decimal(str(lo)) if lo is not None and not isinstance(lo, Decimal) else (lo or Decimal("0")),
            "close": Decimal(str(c)) if not isinstance(c, Decimal) else c,
            "volume": int(v) if v else 0,
        }

    def option_chain(
        self,
        expiry: date | None = None,
        moneyness: str = "all",
        strikes_around: int | None = None,
        option_type: str | None = None,
        as_df: bool = True,
    ) -> Any:
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
                Ignored when as_df=True (use strikes_around instead).
            strikes_around: If set, return only N strikes on each side of ATM.
                E.g. strikes_around=10 returns 10 ITM + ATM + 10 OTM.
                Default when as_df=True is 10 (matches Tradehull).
            option_type: Filter by leg type: "CE", "PE", or None for both.
                Ignored when as_df=True (DataFrame always has both sides).
            as_df: If True (default), return Tradehull-compatible format:
                ``(atm_strike, pd.DataFrame)`` with 27 columns (CE data |
                Strike Price | PE data). If False, return ``list[dict]``
                with moneyness filtering.

        Returns:
            When as_df=True:
                Tuple of (atm_strike: Decimal, df: pd.DataFrame) where
                DataFrame has columns: CE OI, CE Chg in OI, CE Volume,
                CE IV, CE LTP, CE Bid Qty, CE Bid, CE Ask, CE Ask Qty,
                CE Delta, CE Theta, CE Gamma, CE Vega, Strike Price,
                PE Bid Qty, PE Bid, PE Ask, PE Ask Qty, PE LTP, PE IV,
                PE Volume, PE Chg in OI, PE OI, PE Delta, PE Theta,
                PE Gamma, PE Vega.
            When as_df=False:
                List of dicts with keys: symbol, security_id, strike,
                bid, ask, oi, volume, delta, option_type, moneyness,
                spot_price, and all greeks.
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

        # ── Tradehull-compatible DataFrame output ──────────────────────
        if as_df:
            return self._option_chain_as_df(chain, strikes_around)

        # ── Legacy list[dict] output with moneyness filtering ──────────
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
            atm_strike = min(
                (Decimal(str(leg["strike"])) for leg in enriched),
                key=lambda s: abs(s - spot),
            )
            unique_strikes = sorted(
                {Decimal(str(leg["strike"])) for leg in enriched},
                key=lambda s: (abs(s - spot), s),
            )
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

    def _option_chain_as_df(
        self,
        chain: list[dict[str, Any]],
        strikes_around: int | None = None,
    ) -> tuple[Decimal, Any]:
        """Pivot flat option chain into Tradehull-compatible DataFrame.

        Returns:
            (atm_strike, DataFrame) tuple matching Tradehull's
            ``get_option_chain()`` return format.
        """
        import pandas as pd

        if not chain:
            return Decimal("0"), pd.DataFrame()

        # Compute ATM strike from spot price
        spot = self._get_spot_for_chain()
        strikes = sorted({Decimal(str(leg["strike"])) for leg in chain})
        if spot > 0 and strikes:
            atm_strike = min(strikes, key=lambda s: abs(s - spot))
        else:
            atm_strike = strikes[len(strikes) // 2] if strikes else Decimal("0")

        # Apply strikes_around filter (default 10 like Tradehull)
        n = strikes_around if strikes_around is not None else 10
        if strikes and atm_strike:
            atm_idx = strikes.index(atm_strike) if atm_strike in strikes else len(strikes) // 2
            lo = max(0, atm_idx - n)
            hi = min(len(strikes), atm_idx + n + 1)
            selected = set(strikes[lo:hi])
            chain = [leg for leg in chain if Decimal(str(leg["strike"])) in selected]

        # Pivot: group by strike, CE on left, PE on right
        by_strike: dict[Decimal, dict[str, dict]] = {}
        for leg in chain:
            strike = Decimal(str(leg["strike"]))
            opt_type = leg.get("option_type", "")
            if strike not in by_strike:
                by_strike[strike] = {}
            by_strike[strike][opt_type] = leg

        rows: list[dict[str, Any]] = []
        for strike in sorted(by_strike.keys()):
            ce = by_strike[strike].get("CE", {})
            pe = by_strike[strike].get("PE", {})
            rows.append({
                # CE side
                "CE OI": ce.get("oi"),
                "CE Chg in OI": (ce.get("oi", 0) or 0) - (ce.get("previous_oi", 0) or 0),
                "CE Volume": ce.get("volume"),
                "CE IV": ce.get("iv"),
                "CE LTP": ce.get("ltp"),
                "CE Bid Qty": ce.get("bid_qty"),
                "CE Bid": ce.get("bid"),
                "CE Ask": ce.get("ask"),
                "CE Ask Qty": ce.get("ask_qty"),
                "CE Delta": ce.get("delta"),
                "CE Theta": ce.get("theta"),
                "CE Gamma": ce.get("gamma"),
                "CE Vega": ce.get("vega"),
                # Center
                "Strike Price": strike,
                # PE side
                "PE Bid Qty": pe.get("bid_qty"),
                "PE Bid": pe.get("bid"),
                "PE Ask": pe.get("ask"),
                "PE Ask Qty": pe.get("ask_qty"),
                "PE LTP": pe.get("ltp"),
                "PE IV": pe.get("iv"),
                "PE Volume": pe.get("volume"),
                "PE Chg in OI": (pe.get("oi", 0) or 0) - (pe.get("previous_oi", 0) or 0),
                "PE OI": pe.get("oi"),
                "PE Delta": pe.get("delta"),
                "PE Theta": pe.get("theta"),
                "PE Gamma": pe.get("gamma"),
                "PE Vega": pe.get("vega"),
            })

        df = pd.DataFrame(rows)
        return atm_strike, df

    def _get_spot_for_chain(self) -> Decimal:
        """Get spot price for option chain ATM calculation."""
        try:
            return Decimal(str(self._market_data.get_ltp_by_id(
                self._resolved.security_id,
                self._resolved.wire_segment,
                symbol=self.symbol,
            )))
        except Exception:
            return Decimal("0")

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

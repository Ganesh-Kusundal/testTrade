from __future__ import annotations

import logging
from collections.abc import Callable
from decimal import Decimal
from typing import Any

import pandas as pd

from scalpr.adapters.dhan._protocols import HttpProvider, ResolveFn, TokenProvider, WsProvider
from scalpr.domain.contracts import DepthLevel, MarketDepth
from scalpr.domain.instrument import (
    DerivativeInstrumentId,
    InstrumentId,
    SimpleInstrumentId,
)
from scalpr.domain.tick import Tick as QuoteTick
from scalpr.market_data.charting import heikin_ashi as _heikin_ashi
from scalpr.market_data.charting import renko_bricks as _renko_bricks
from scalpr.market_data.charting import resample_timeframe as _resample_timeframe

logger = logging.getLogger(__name__)


def _list_to_df(data: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(data)


class MarketDataClient:
    def __init__(
        self,
        http_provider: Callable[[], HttpProvider],
        token_provider: Callable[[], TokenProvider],
        ws_provider: Callable[[], WsProvider],
        historical_provider: Any,
        option_chain_provider: Any,
        greeks_provider: Any,
        bus: Any,
        resolve_fn: ResolveFn,
    ) -> None:
        self._http_provider = http_provider
        self._token_provider = token_provider
        self._ws_provider = ws_provider
        self._historical_provider = historical_provider
        self._option_chain_provider = option_chain_provider
        self._greeks_provider = greeks_provider
        self._bus = bus
        self._resolve = resolve_fn

    @property
    def _http(self):
        return self._http_provider()

    @property
    def _token_manager(self):
        return self._token_provider()

    @property
    def _ws(self):
        return self._ws_provider()

    @property
    def _historical(self):
        return self._historical_provider()

    @property
    def _option_chain(self):
        return self._option_chain_provider()

    @property
    def _greeks(self):
        return self._greeks_provider()

    # ── Helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _instrument_id_to_symbol_exchange(instrument_id: InstrumentId) -> tuple[str, str]:
        if isinstance(instrument_id, SimpleInstrumentId):
            return instrument_id.symbol, instrument_id.exchange.value
        if isinstance(instrument_id, DerivativeInstrumentId):
            # Prefer the specific contract's trading symbol (e.g. "BANKNIFTY24JULFUT")
            # over the underlying, so we subscribe to the right instrument.
            symbol = instrument_id.trading_symbol or instrument_id.underlying
            return symbol, instrument_id.exchange.value
        raise TypeError(f"Unsupported InstrumentId type: {type(instrument_id).__name__}")

    # ── Market data ────────────────────────────────────────────────────

    def subscribe_quotes(self, instrument_id: InstrumentId) -> None:
        symbol, exchange = self._instrument_id_to_symbol_exchange(instrument_id)
        security_id, segment = self._resolve(symbol, exchange)
        self._ws.subscribe([(security_id, segment)], mode="quote")

    def unsubscribe_quotes(self, instrument_id: InstrumentId) -> None:
        symbol, exchange = self._instrument_id_to_symbol_exchange(instrument_id)
        security_id, segment = self._resolve(symbol, exchange)
        self._ws.unsubscribe([(security_id, segment)])

    def get_quote(self, instrument_id: InstrumentId) -> dict[str, Any]:
        from scalpr.adapters.dhan.client import to_quote

        symbol, exchange = self._instrument_id_to_symbol_exchange(instrument_id)
        security_id, segment = self._resolve(symbol, exchange)
        data = self._http.post(
            "/marketfeed/quote",
            data={"security_ids": [security_id], "exchangeSegment": segment},
            bucket="market_data",
        )
        return to_quote(data, instrument_id)

    def on_ws_tick(self, tick: QuoteTick) -> None:
        self._bus.publish("market.quote.dhan", tick)

    # ── Market depth ────────────────────────────────────────────────────

    def subscribe_market_depth(self, instrument_id: InstrumentId, level: int = 20) -> None:
        symbol, exchange = self._instrument_id_to_symbol_exchange(instrument_id)
        security_id, segment = self._resolve(symbol, exchange)
        self._ws.subscribe_depth([(security_id, segment)], level=level)

    # ── High-level subscribe API ─────────────────────────────────────────

    def subscribe(self, symbol: str, exchange: str = "NSE", type: str = "quote", level: int | None = None) -> None:
        from scalpr.domain.instrument import Exchange, SimpleInstrumentId
        instrument_id = SimpleInstrumentId(symbol=symbol, exchange=Exchange(exchange))
        if type == "quote":
            self.subscribe_quotes(instrument_id)
        elif type == "depth":
            self.subscribe_market_depth(instrument_id, level or 20)
        else:
            raise ValueError(f"unknown subscription type: {type}")

    def subscribe_batch(self, specs: list[tuple[str, str, str, int | None]]) -> None:
        for symbol, exchange, type_, level in specs:
            self.subscribe(symbol, exchange, type_, level)

    def subscription_status(self) -> dict:
        ws = self._ws
        return {
            "quote_subscriptions": ws.subscription_count,
            "depth_subscriptions": ws.depth_subscription_count,
            "depth_20_remaining": ws.depth_capacity_remaining_20,
            "depth_200_remaining": ws.depth_capacity_remaining_200,
            "total_capacity": ws.MAX_SUBSCRIBERS,
            "remaining": ws.subscription_capacity_remaining,
        }

    def unsubscribe_market_depth(self, instrument_id: InstrumentId, level: int = 20) -> None:
        symbol, exchange = self._instrument_id_to_symbol_exchange(instrument_id)
        security_id, segment = self._resolve(symbol, exchange)
        self._ws.unsubscribe_depth([(security_id, segment)], level=level)

    def _depth_to_domain(
        self,
        snapshot: dict,
        *,
        symbol: str = "",
        exchange: str = "",
    ) -> MarketDepth:
        """Convert raw SDK depth response to canonical MarketDepth domain model."""
        depth = snapshot.get("depth") or {}
        bids_raw = depth.get("bid") or []
        asks_raw = depth.get("ask") or []

        bid_levels = [
            DepthLevel(
                price=Decimal(str(b.get("price", "0"))),
                quantity=int(b.get("quantity", 0)),
                orders=int(b.get("orders", 1)),
            )
            for b in bids_raw
        ]
        ask_levels = [
            DepthLevel(
                price=Decimal(str(a.get("price", "0"))),
                quantity=int(a.get("quantity", 0)),
                orders=int(a.get("orders", 1)),
            )
            for a in asks_raw
        ]

        return MarketDepth(
            symbol=symbol or str(snapshot.get("security_id", "")),
            exchange=exchange or str(snapshot.get("exchange", "")),
            bid_levels=bid_levels,
            ask_levels=ask_levels,
            timestamp=None,
        )

    def get_market_depth_snapshot(self, instrument_id: InstrumentId) -> dict:
        symbol, exchange = self._instrument_id_to_symbol_exchange(instrument_id)
        security_id, segment = self._resolve(symbol, exchange)
        data = self._http.post(
            "/marketfeed/depth",
            data={"security_ids": [security_id], "exchangeSegment": segment},
            bucket="market_data",
        )
        return data

    def get_market_depth_df(self, instrument_id: InstrumentId, as_df: bool = False) -> list[dict] | pd.DataFrame:
        return self._market_depth_df(self.get_market_depth_snapshot(instrument_id), as_df=as_df)

    def get_market_depth(self, instrument_id: InstrumentId) -> MarketDepth:
        """Return canonical MarketDepth domain model for the instrument."""
        symbol, exchange = self._instrument_id_to_symbol_exchange(instrument_id)
        snapshot = self.get_market_depth_snapshot(instrument_id)
        return self._depth_to_domain(snapshot, symbol=symbol, exchange=exchange)

    @staticmethod
    def _market_depth_df(raw: dict, as_df: bool = False) -> list[dict] | pd.DataFrame:
        depth = raw.get("depth") or {}
        bids = depth.get("bid") or []
        asks = depth.get("ask") or []

        bid_sorted = sorted(bids, key=lambda x: float(x.get("price", 0)), reverse=True)
        ask_sorted = sorted(asks, key=lambda x: float(x.get("price", 0)))

        out: list[dict] = []
        max_len = max(len(bid_sorted), len(ask_sorted))
        for i in range(max_len):
            b = bid_sorted[i] if i < len(bid_sorted) else None
            a = ask_sorted[i] if i < len(ask_sorted) else None
            out.append({
                "level": i + 1,
                "bid_price": float(b.get("price", 0)) if b else None,
                "bid_qty": int(b.get("quantity", 0)) if b else None,
                "bid_orders": int(b.get("orders", 0)) if b else None,
                "ask_price": float(a.get("price", 0)) if a else None,
                "ask_qty": int(a.get("quantity", 0)) if a else None,
                "ask_orders": int(a.get("orders", 0)) if a else None,
            })
        if as_df:
            return _list_to_df(out)
        return out

    # ── Historical data ────────────────────────────────────────────────

    def get_historical_batch(
        self,
        symbols: list[tuple[str, str]],
        timeframe: str = "DAY",
        interval: int = 5,
        from_date: str | None = None,
        to_date: str | None = None,
        max_workers: int = 5,
    ) -> dict[str, pd.DataFrame | list[dict] | Exception]:
        return self._historical.get_historical_batch(
            symbols, timeframe, interval, from_date, to_date, max_workers,
        )

    def get_historical(
        self,
        symbol: str,
        exchange: str = "NSE",
        timeframe: str = "DAY",
        interval: int = 5,
        from_date: str | None = None,
        to_date: str | None = None,
        as_df: bool = False,
        debug: bool = False,
    ) -> list[dict[str, Any]] | pd.DataFrame:
        if debug:
            logger.info("get_historical: symbol=%s exchange=%s timeframe=%s interval=%s", symbol, exchange, timeframe, interval)
        return self._historical.get_historical(symbol, exchange, timeframe, interval, from_date, to_date, as_df=as_df)

    def get_intraday(
        self,
        symbol: str,
        exchange: str = "NSE",
        interval: int = 5,
        from_date: str | None = None,
        to_date: str | None = None,
        as_df: bool = False,
        debug: bool = False,
    ) -> list[dict[str, Any]] | pd.DataFrame:
        if debug:
            logger.info("get_intraday: symbol=%s exchange=%s interval=%s", symbol, exchange, interval)
        return self._historical.get_intraday(symbol, exchange, interval, from_date, to_date, as_df=as_df)

    def get_daily(
        self,
        symbol: str,
        exchange: str = "NSE",
        from_date: str | None = None,
        to_date: str | None = None,
        as_df: bool = False,
        debug: bool = False,
    ) -> list[dict[str, Any]] | pd.DataFrame:
        if debug:
            logger.info("get_daily: symbol=%s exchange=%s", symbol, exchange)
        return self._historical.get_daily(symbol, exchange, from_date, to_date, as_df=as_df)

    # ── Option chain ───────────────────────────────────────────────────

    def get_option_chain(
        self,
        symbol: str,
        exchange: str = "NSE",
        expiry: str | None = None,
        as_df: bool = False,
        num_strikes: int = 0,
        debug: bool = False,
    ) -> dict[str, Any] | pd.DataFrame:
        if debug:
            logger.info("get_option_chain: symbol=%s exchange=%s expiry=%s num_strikes=%d", symbol, exchange, expiry, num_strikes)
        return self._option_chain.get_option_chain(symbol, exchange, expiry=expiry, as_df=as_df, num_strikes=num_strikes, debug=debug)

    def get_expiry_list(self, symbol: str, exchange: str = "NSE", as_series: bool = False, debug: bool = False) -> list[str] | pd.Series:
        if debug:
            logger.info("get_expiry_list: symbol=%s exchange=%s", symbol, exchange)
        return self._option_chain.get_expiry_list(symbol, exchange, as_series=as_series)

    def atm_strike(self, symbol: str, expiry_idx: int = 0, exchange: str = "NSE") -> tuple[str, str, float]:
        return self._option_chain.atm_strike_selection(symbol, expiry_idx=expiry_idx, exchange=exchange)

    def otm_strike(
        self, symbol: str, expiry_idx: int = 0, count: int = 1, exchange: str = "NSE",
    ) -> tuple[str, str, float, float]:
        return self._option_chain.otm_strike_selection(symbol, expiry_idx=expiry_idx, count=count, exchange=exchange)

    def itm_strike(
        self, symbol: str, expiry_idx: int = 0, count: int = 1, exchange: str = "NSE",
    ) -> tuple[str, str, float, float]:
        return self._option_chain.itm_strike_selection(symbol, expiry_idx=expiry_idx, count=count, exchange=exchange)

    def get_greeks(
        self,
        symbol: str,
        expiry: str,
        strike: float,
        option_type: str,
        exchange: str = "NSE",
        as_df: bool = False,
    ) -> dict | pd.DataFrame | None:
        return self._greeks.calculate_from_chain(symbol, expiry, strike, option_type, exchange=exchange, as_df=as_df)

    # ── Resample ───────────────────────────────────────────────────────

    @staticmethod
    def resample_timeframe(data: list[dict] | pd.DataFrame, timeframe: str = "5T") -> pd.DataFrame:
        """Delegates to scalpr.market_data.charting.resample_timeframe."""
        return _resample_timeframe(data, timeframe)

    # ── Chart transforms ───────────────────────────────────────────────

    @staticmethod
    def renko_bricks(data: list[dict] | pd.DataFrame, box_size: int = 7) -> pd.DataFrame:
        """Delegates to scalpr.market_data.charting.renko_bricks."""
        return _renko_bricks(data, box_size)

    @staticmethod
    def heikin_ashi(data: list[dict] | pd.DataFrame) -> pd.DataFrame:
        """Delegates to scalpr.market_data.charting.heikin_ashi."""
        return _heikin_ashi(data)

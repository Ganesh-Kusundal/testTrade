from __future__ import annotations

import logging
from typing import Any

import pandas as pd
import pytz

from scalpr.domain.instrument import (
    DerivativeInstrumentId,
    InstrumentId,
    SimpleInstrumentId,
)
from scalpr.domain.tick import Tick as QuoteTick

logger = logging.getLogger(__name__)


def _list_to_df(data: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(data)


class MarketDataClient:
    def __init__(
        self,
        http_provider,
        token_provider,
        ws_provider,
        historical_provider,
        option_chain_provider,
        greeks_provider,
        bus: Any,
        resolve_fn,
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
            return instrument_id.underlying, instrument_id.exchange.value
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

    def unsubscribe_market_depth(self, instrument_id: InstrumentId, level: int = 20) -> None:
        symbol, exchange = self._instrument_id_to_symbol_exchange(instrument_id)
        security_id, segment = self._resolve(symbol, exchange)
        self._ws.unsubscribe_depth([(security_id, segment)], level=level)

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
        raw = self.get_market_depth_snapshot(instrument_id)
        depth = raw.get("depth") or {}
        bids = depth.get("bid") or []
        asks = depth.get("ask") or []

        bid_sorted = sorted(bids, key=lambda x: float(x.get("price", 0)), reverse=True)
        ask_sorted = sorted(asks, key=lambda x: float(x.get("price", 0)))

        out: list[dict] = []
        min_len = min(len(bid_sorted), len(ask_sorted))
        for i in range(min_len):
            b = bid_sorted[i]
            a = ask_sorted[i]
            out.append({
                "level": i + 1,
                "bid_price": float(b.get("price", 0)),
                "bid_qty": int(b.get("quantity", 0)),
                "bid_orders": int(b.get("orders", 0)),
                "ask_price": float(a.get("price", 0)),
                "ask_qty": int(a.get("quantity", 0)),
                "ask_orders": int(a.get("orders", 0)),
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
        if isinstance(data, list):
            df = pd.DataFrame(data)
        else:
            df = data.copy()

        if df.empty:
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df.set_index("timestamp", inplace=True)

        tz = pytz.timezone("Asia/Kolkata")
        df.index = df.index.tz_localize(tz, ambiguous="infer")

        market_start = pd.to_datetime("09:15:00").time()
        market_end = pd.to_datetime("15:30:00").time()

        freq = timeframe.replace("T", "min").replace("H", "h")

        resampled = []
        for date, group in df.groupby(df.index.date):
            origin = tz.localize(pd.Timestamp(f"{date} 09:15:00"))
            daily = group.between_time(market_start, market_end)
            if not daily.empty:
                r = daily.resample(freq, origin=origin).agg({
                    "open": "first",
                    "high": "max",
                    "low": "min",
                    "close": "last",
                    "volume": "sum",
                }).dropna(how="all")
                resampled.append(r)

        if resampled:
            result = pd.concat(resampled)
        else:
            result = pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

        result.reset_index(inplace=True)
        return result

    # ── Chart transforms ───────────────────────────────────────────────

    @staticmethod
    def renko_bricks(data: list[dict] | pd.DataFrame, box_size: int = 7) -> pd.DataFrame:
        if isinstance(data, list):
            df = pd.DataFrame(data)
        else:
            df = data.copy()

        if df.empty:
            return pd.DataFrame(columns=["date", "direction", "high", "low"])

        if "timestamp" in df.columns:
            df = df.rename(columns={"timestamp": "date"})

        df = df.sort_values("date").reset_index(drop=True)

        closes = df["close"].to_numpy(dtype=float)
        dates = df["date"].to_numpy()

        bricks: list[dict] = []
        brick_edge = closes[0]

        for i in range(1, len(closes)):
            close = closes[i]
            ts = dates[i]

            while close >= brick_edge + box_size:
                bricks.append({
                    "date": ts,
                    "direction": 1,
                    "high": brick_edge + box_size,
                    "low": brick_edge,
                })
                brick_edge += box_size

            while close <= brick_edge - box_size:
                bricks.append({
                    "date": ts,
                    "direction": -1,
                    "high": brick_edge,
                    "low": brick_edge - box_size,
                })
                brick_edge -= box_size

        return pd.DataFrame(bricks)

    @staticmethod
    def heikin_ashi(data: list[dict] | pd.DataFrame) -> pd.DataFrame:
        if isinstance(data, list):
            df = pd.DataFrame(data)
        else:
            df = data.copy()

        if df.empty:
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close"])

        if "date" in df.columns:
            df = df.rename(columns={"date": "timestamp"})

        df = df.sort_values("timestamp").reset_index(drop=True)

        ha = df[["timestamp"]].copy().astype({"timestamp": "object"})
        ha["open"] = 0.0
        ha["high"] = 0.0
        ha["low"] = 0.0
        ha["close"] = 0.0

        for i in range(len(df)):
            o = float(df.loc[i, "open"])
            h = float(df.loc[i, "high"])
            l = float(df.loc[i, "low"])
            c = float(df.loc[i, "close"])

            ha_close = (o + h + l + c) / 4.0

            if i == 0:
                ha_open = o
            else:
                ha_open = (ha.loc[i - 1, "open"] + ha.loc[i - 1, "close"]) / 2.0

            ha_high = max(h, ha_open, ha_close)
            ha_low = min(l, ha_open, ha_close)

            ha.loc[i, "open"] = ha_open
            ha.loc[i, "high"] = ha_high
            ha.loc[i, "low"] = ha_low
            ha.loc[i, "close"] = ha_close

        return ha

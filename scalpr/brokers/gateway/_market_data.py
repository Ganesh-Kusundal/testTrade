"""Market data mixin for Gateway.

Provides market data operations: ltp, quote, depth, history.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

import pandas as pd

from scalpr.brokers.contracts import DepthLevel, MarketDepth, Quote
from scalpr.domain.values import DEFAULT_EXCHANGE


class MarketDataMixin:
    """Mixin providing market data operations.

    Expects the composed Gateway class to provide _gateway attribute.
    """

    # Attribute provided by the composed Gateway class
    _gateway: Any

    def ltp(self, symbol: str, exchange: str = DEFAULT_EXCHANGE) -> Decimal:
        """Get Last Traded Price for a symbol.

        Args:
            symbol: Trading symbol (e.g., "TCS", "RELIANCE")
            exchange: Exchange code (default: "NSE")

        Returns:
            LTP as Decimal
        """
        return self._gateway.get_ltp(symbol, exchange)

    def quote(self, symbol: str, exchange: str = DEFAULT_EXCHANGE) -> Quote:
        """Get full market quote for a symbol.

        Args:
            symbol: Trading symbol
            exchange: Exchange code (default: "NSE")

        Returns:
            Quote dataclass with ltp, open, high, low, close, volume
        """
        raw_quote = self._gateway.get_quote(symbol, exchange)

        return Quote(
            symbol=symbol,
            exchange=exchange,
            ltp=Decimal(str(raw_quote.get("ltp", 0))),
            open=Decimal(str(raw_quote.get("open", 0))),
            high=Decimal(str(raw_quote.get("high", 0))),
            low=Decimal(str(raw_quote.get("low", 0))),
            close=Decimal(str(raw_quote.get("close", 0))),
            volume=int(raw_quote.get("volume", 0)),
            change=Decimal(str(raw_quote.get("change", 0))),
            change_percent=Decimal(str(raw_quote.get("change_percent", 0))),
            timestamp=None,
        )

    def depth(
        self, symbol: str, exchange: str = DEFAULT_EXCHANGE
    ) -> MarketDepth:
        """Get market depth (order book) for a symbol.

        Args:
            symbol: Trading symbol
            exchange: Exchange code (default: "NSE")

        Returns:
            MarketDepth dataclass with bid/ask levels
        """
        # Delegate to connection's market_data adapter
        if hasattr(self._gateway, "connection") and hasattr(
            self._gateway.connection, "market_data"
        ):
            raw_depth = self._gateway.connection.market_data.get_depth(
                symbol, exchange
            )

            bid_levels = [
                DepthLevel(
                    price=level["price"],
                    quantity=level["quantity"],
                    orders=level["orders"],
                )
                for level in raw_depth.get("bids", [])
            ]
            ask_levels = [
                DepthLevel(
                    price=level["price"],
                    quantity=level["quantity"],
                    orders=level["orders"],
                )
                for level in raw_depth.get("asks", [])
            ]

            return MarketDepth(
                symbol=symbol,
                exchange=exchange,
                bid_levels=bid_levels,
                ask_levels=ask_levels,
            )

        raise NotImplementedError(
            f"depth() not implemented for {self._broker_name}"
        )

    def history(
        self,
        symbol: str | list[str],
        exchange: str = DEFAULT_EXCHANGE,
        timeframe: str = "1m",
        lookback_days: int = 365,
    ) -> pd.DataFrame:
        """Fetch historical OHLCV candlestick data.

        Args:
            symbol: Single symbol or list of symbols
            exchange: Exchange code (default: "NSE")
            timeframe: Candle interval (default: "1m")
            lookback_days: Days of history (default: 365)

        Returns:
            DataFrame with columns:
            timestamp, open, high, low, close, volume, oi, symbol, exchange, timeframe
        """
        symbols = [symbol] if isinstance(symbol, str) else symbol

        all_candles = []

        for sym in symbols:
            to_date = date.today()
            from_date = to_date - timedelta(days=lookback_days)

            candles = self._gateway.get_ohlcv(
                sym, exchange, timeframe, from_date, to_date
            )

            for candle in candles:
                all_candles.append(
                    {
                        "timestamp": candle.get("timestamp"),
                        "open": float(candle.get("open", 0)),
                        "high": float(candle.get("high", 0)),
                        "low": float(candle.get("low", 0)),
                        "close": float(candle.get("close", 0)),
                        "volume": float(candle.get("volume", 0)),
                        "oi": float(candle.get("oi", 0)),
                        "symbol": sym,
                        "exchange": exchange,
                        "timeframe": timeframe,
                    }
                )

        df = pd.DataFrame(all_candles)

        # Ensure correct column order
        columns = [
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "oi",
            "symbol",
            "exchange",
            "timeframe",
        ]

        # Reorder columns if DataFrame is not empty
        if not df.empty:
            df = df[columns]

        return df

"""Market data adapter — LTP, Quote, Depth, OHLC.

Provides methods to fetch market data from Dhan API.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from scalpr.brokers.dhan.http_client import DhanHttpClient
from scalpr.brokers.dhan.resolution import SymbolResolver
from scalpr.domain.values import DEFAULT_EXCHANGE, ZERO

logger = logging.getLogger(__name__)


def _build_quote_fields(raw: dict[str, Any], symbol: str) -> dict[str, Any]:
    """Build the canonical quote dict[str, Any] from a raw /marketfeed/quote entry.

    Single source of truth for quote fields — used by both single and batch
    paths so they can never silently diverge (S-4: batch quotes were missing
    change/change_percent because they hand-rolled a second field list).
    """
    ohlc = raw.get("ohlc", {})
    close = Decimal(str(ohlc.get("close", 0)))
    net_change = Decimal(str(raw.get("net_change", 0)))
    change_percent = (
        (net_change / close * 100) if close else ZERO
    )
    return {
        "symbol": symbol,
        "ltp": Decimal(str(raw.get("last_price", 0))),
        "open": Decimal(str(ohlc.get("open", 0))),
        "high": Decimal(str(ohlc.get("high", 0))),
        "low": Decimal(str(ohlc.get("low", 0))),
        "close": close,
        "volume": int(raw.get("volume", 0)),
        "change": net_change,
        "change_percent": change_percent,
        "average_price": Decimal(str(raw.get("average_price", 0))),
        "buy_quantity": int(raw.get("buy_quantity", 0)),
        "sell_quantity": int(raw.get("sell_quantity", 0)),
        "last_quantity": int(raw.get("last_quantity", 0)),
        "last_trade_time": raw.get("last_trade_time"),
        "lower_circuit_limit": Decimal(str(raw.get("lower_circuit_limit", 0))),
        "upper_circuit_limit": Decimal(str(raw.get("upper_circuit_limit", 0))),
        "oi": int(raw.get("oi", 0)),
        "oi_day_high": Decimal(str(raw.get("oi_day_high", 0))),
        "oi_day_low": Decimal(str(raw.get("oi_day_low", 0))),
    }


class MarketDataAdapter:
    """Adapter for fetching market data from Dhan API.

    Provides methods for:
    - LTP (Last Traded Price)
    - Quote (full market data)
    - Depth (bid/ask levels)
    - Batch operations
    """

    def __init__(self, client: DhanHttpClient, resolver: SymbolResolver):
        self._client = client
        self._resolver = resolver

    def _resolve_segment(self, symbol: str, exchange: str) -> tuple[int, str]:
        """Resolve symbol to numeric security_id and segment."""
        inst = self._resolver.resolve(symbol, exchange)
        segment = self._resolver.wire_segment_of(symbol, exchange)
        security_id = int(inst.security_id)  # Convert to int for Dhan API
        return security_id, segment

    def get_ltp(self, symbol: str, exchange: str = DEFAULT_EXCHANGE) -> Decimal:
        """Get Last Traded Price for a symbol.

        Args:
            symbol: Trading symbol (e.g., "RELIANCE")
            exchange: Exchange (e.g., "NSE", "MCX")

        Returns:
            LTP as Decimal
        """
        security_id, segment = self._resolve_segment(symbol, exchange)
        return self.get_ltp_by_id(security_id, segment, symbol=symbol)

    def get_ltp_by_id(self, security_id: str | int, segment: str, symbol: str = "") -> Decimal:
        """Get LTP by pre-resolved security_id + wire segment (no re-resolution)."""
        security_id = int(security_id)
        data = self._client.post("/marketfeed/ltp", json={segment: [security_id]})
        entry = data.get("data", {}).get(segment, {}).get(str(security_id))

        if entry is None:
            logger.warning("LTP missing for %s (security_id=%s, segment=%s)", symbol or security_id, security_id, segment)
            raise ValueError(f"No LTP data for {symbol or security_id} on {segment}")

        ltp = Decimal(str(entry.get("last_price", 0)))
        logger.debug("LTP fetched: %s = %s", symbol or security_id, ltp)
        return ltp

    def get_quote(self, symbol: str, exchange: str = DEFAULT_EXCHANGE) -> dict[str, Any]:
        """Get full quote for a symbol.

        Args:
            symbol: Trading symbol
            exchange: Exchange

        Returns:
            Quote dict[str, Any] with all Dhan fields: ltp, open, high, low, close, volume,
            change, average_price, buy_quantity, sell_quantity, last_quantity,
            last_trade_time, lower_circuit_limit, upper_circuit_limit, oi,
            oi_day_high, oi_day_low
        """
        security_id, segment = self._resolve_segment(symbol, exchange)
        return self.get_quote_by_id(security_id, segment, symbol=symbol)

    def get_quote_by_id(self, security_id: str | int, segment: str, symbol: str = "") -> dict[str, Any]:
        """Get full quote by pre-resolved security_id + wire segment."""
        security_id = int(security_id)
        data = self._client.post("/marketfeed/quote", json={segment: [security_id]})
        raw = data.get("data", {}).get(segment, {}).get(str(security_id))

        if not raw:
            logger.warning("Quote missing for %s (security_id=%s, segment=%s)", symbol or security_id, security_id, segment)
            raise ValueError(f"No quote data for {symbol or security_id} on {segment}")

        quote = _build_quote_fields(raw, symbol)

        logger.debug("Quote fetched: %s LTP=%s", symbol, quote['ltp'])
        return quote

    def get_depth(self, symbol: str, exchange: str = DEFAULT_EXCHANGE) -> dict[str, Any]:
        """Get market depth for a symbol (5-level via REST quote endpoint).

        Note: For 20-level depth, use the DhanWebSocketManager with FullDepth mode.
        The REST /marketfeed/quote endpoint only returns 5 levels.

        Args:
            symbol: Trading symbol
            exchange: Exchange

        Returns:
            Depth dict[str, Any] with bids and asks lists
        """
        security_id, segment = self._resolve_segment(symbol, exchange)
        return self.get_depth_by_id(security_id, segment, symbol=symbol)

    def get_depth_by_id(self, security_id: str | int, segment: str, symbol: str = "") -> dict[str, Any]:
        """Get 5-level market depth by pre-resolved security_id + wire segment."""
        security_id = int(security_id)
        data = self._client.post("/marketfeed/quote", json={segment: [security_id]})
        raw = data.get("data", {}).get(segment, {}).get(str(security_id))

        if not raw:
            logger.warning("Depth missing for %s (security_id=%s, segment=%s)", symbol or security_id, security_id, segment)
            raise ValueError(f"No depth data for {symbol or security_id} on {segment}")

        bids = [
            {
                "price": Decimal(str(level.get("price", 0))),
                "quantity": int(level.get("quantity", 0)),
                "orders": int(level.get("orders", 0)),
            }
            for level in raw.get("depth", {}).get("buy", [])[:5]
        ]

        asks = [
            {
                "price": Decimal(str(level.get("price", 0))),
                "quantity": int(level.get("quantity", 0)),
                "orders": int(level.get("orders", 0)),
            }
            for level in raw.get("depth", {}).get("sell", [])[:5]
        ]

        depth = {
            "symbol": symbol,
            "bids": bids,
            "asks": asks,
        }

        logger.debug("Depth fetched: %s bids=%s asks=%s", symbol, len(bids), len(asks))
        return depth

    def get_batch_ltp(self, symbols: list[str], exchange: str = DEFAULT_EXCHANGE) -> dict[str, Decimal]:
        """Get LTP for multiple symbols in one call.

        Args:
            symbols: List of trading symbols
            exchange: Exchange

        Returns:
            Dict mapping symbol to LTP
        """
        segment_map: dict[str, list[int]] = {}
        symbol_map: dict[str, str] = {}

        for sym in symbols:
            try:
                security_id, segment = self._resolve_segment(sym, exchange)
                segment_map.setdefault(segment, []).append(security_id)
                symbol_map[str(security_id)] = sym  # response keys are strings
            except Exception as exc:
                logger.warning("Batch resolve skipped %r on %s: %s", sym, exchange, exc)
                continue

        if not segment_map:
            return {}

        data = self._client.post("/marketfeed/ltp", json=segment_map)

        result = {}
        for seg, sids in data.get("data", {}).items():
            for sid_str, info in sids.items():
                if sid_str in symbol_map:
                    result[symbol_map[sid_str]] = Decimal(str(info.get("last_price", 0)))

        logger.debug("Batch LTP fetched: %s symbols", len(result))
        return result

    def get_batch_quote(self, symbols: list[str], exchange: str = DEFAULT_EXCHANGE) -> dict[str, dict[str, Any]]:
        """Get quotes for multiple symbols in one call.

        Args:
            symbols: List of trading symbols
            exchange: Exchange

        Returns:
            Dict mapping symbol to quote dict[str, Any]
        """
        segment_map: dict[str, list[int]] = {}
        symbol_map: dict[str, str] = {}

        for sym in symbols:
            try:
                security_id, segment = self._resolve_segment(sym, exchange)
                segment_map.setdefault(segment, []).append(security_id)
                symbol_map[str(security_id)] = sym  # response keys are strings
            except Exception as exc:
                logger.warning("Batch resolve skipped %r on %s: %s", sym, exchange, exc)
                continue

        if not segment_map:
            return {}

        data = self._client.post("/marketfeed/quote", json=segment_map)

        result = {}
        for seg, sids in data.get("data", {}).items():
            for sid_str, info in sids.items():
                if sid_str in symbol_map:
                    result[symbol_map[sid_str]] = _build_quote_fields(info, symbol_map[sid_str])

        logger.debug("Batch quotes fetched: %s symbols", len(result))
        return result

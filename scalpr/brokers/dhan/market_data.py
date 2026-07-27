"""Market data adapter — LTP, Quote, Depth, OHLC.

Provides methods to fetch market data from Dhan API.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from scalpr.brokers.dhan.http_client import DhanHttpClient
from scalpr.brokers.dhan.resolver import SymbolResolver
from scalpr.brokers.dhan.segments import EXCHANGE_TO_SEGMENT
from scalpr.domain.instrument import Exchange

logger = logging.getLogger(__name__)


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
        segment = EXCHANGE_TO_SEGMENT.get(inst.exchange.value, "NSE_EQ")
        security_id = int(inst.security_id)  # Convert to int for Dhan API
        return security_id, segment

    def get_ltp(self, symbol: str, exchange: str = "NSE") -> Decimal:
        """Get Last Traded Price for a symbol.
        
        Args:
            symbol: Trading symbol (e.g., "RELIANCE")
            exchange: Exchange (e.g., "NSE", "MCX")
        
        Returns:
            LTP as Decimal
        """
        security_id, segment = self._resolve_segment(symbol, exchange)
        
        data = self._client.post("/marketfeed/ltp", json={segment: [security_id]})
        segment_data = data.get("data", {}).get(segment, {})
        entry = segment_data.get(str(security_id))
        
        if entry is None:
            logger.warning(f"LTP missing for {symbol} (security_id={security_id}, segment={segment})")
            raise ValueError(f"No LTP data for {symbol} on {exchange}")
        
        ltp = Decimal(str(entry.get("last_price", 0)))
        logger.debug(f"LTP fetched: {symbol} = {ltp}")
        return ltp

    def get_quote(self, symbol: str, exchange: str = "NSE") -> dict[str, Any]:
        """Get full quote for a symbol.
        
        Args:
            symbol: Trading symbol
            exchange: Exchange
        
        Returns:
            Quote dict with ltp, open, high, low, close, volume
        """
        security_id, segment = self._resolve_segment(symbol, exchange)
        
        data = self._client.post("/marketfeed/quote", json={segment: [security_id]})
        raw = data.get("data", {}).get(segment, {}).get(str(security_id), {})
        
        ohlc = raw.get("ohlc", {})
        quote = {
            "symbol": symbol,
            "ltp": Decimal(str(raw.get("last_price", 0))),
            "open": Decimal(str(ohlc.get("open", 0))),
            "high": Decimal(str(ohlc.get("high", 0))),
            "low": Decimal(str(ohlc.get("low", 0))),
            "close": Decimal(str(ohlc.get("close", 0))),
            "volume": int(raw.get("volume", 0)),
            "change": Decimal(str(raw.get("net_change", 0))),
        }
        
        logger.debug(f"Quote fetched: {symbol} LTP={quote['ltp']}")
        return quote

    def get_depth(self, symbol: str, exchange: str = "NSE") -> dict[str, Any]:
        """Get market depth for a symbol.
        
        Args:
            symbol: Trading symbol
            exchange: Exchange
        
        Returns:
            Depth dict with bids and asks lists
        """
        security_id, segment = self._resolve_segment(symbol, exchange)
        
        data = self._client.post("/marketfeed/quote", json={segment: [security_id]})
        raw = data.get("data", {}).get(segment, {}).get(str(security_id), {})
        
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
        
        logger.debug(f"Depth fetched: {symbol} bids={len(bids)} asks={len(asks)}")
        return depth

    def get_batch_ltp(self, symbols: list[str], exchange: str = "NSE") -> dict[str, Decimal]:
        """Get LTP for multiple symbols in one call.
        
        Args:
            symbols: List of trading symbols
            exchange: Exchange
        
        Returns:
            Dict mapping symbol to LTP
        """
        segment_map: dict[str, list[str]] = {}
        symbol_map: dict[str, str] = {}
        
        for sym in symbols:
            try:
                security_id, segment = self._resolve_segment(sym, exchange)
                segment_map.setdefault(segment, []).append(security_id)
                symbol_map[security_id] = sym
            except Exception:
                continue
        
        if not segment_map:
            return {}
        
        data = self._client.post("/marketfeed/ltp", json=segment_map)
        
        result = {}
        for seg, sids in data.get("data", {}).items():
            for sid_str, info in sids.items():
                if sid_str in symbol_map:
                    result[symbol_map[sid_str]] = Decimal(str(info.get("last_price", 0)))
        
        logger.debug(f"Batch LTP fetched: {len(result)} symbols")
        return result

    def get_batch_quote(self, symbols: list[str], exchange: str = "NSE") -> dict[str, dict]:
        """Get quotes for multiple symbols in one call.
        
        Args:
            symbols: List of trading symbols
            exchange: Exchange
        
        Returns:
            Dict mapping symbol to quote dict
        """
        segment_map: dict[str, list[str]] = {}
        symbol_map: dict[str, str] = {}
        
        for sym in symbols:
            try:
                security_id, segment = self._resolve_segment(sym, exchange)
                segment_map.setdefault(segment, []).append(security_id)
                symbol_map[security_id] = sym
            except Exception:
                continue
        
        if not segment_map:
            return {}
        
        data = self._client.post("/marketfeed/quote", json=segment_map)
        
        result = {}
        for seg, sids in data.get("data", {}).items():
            for sid_str, info in sids.items():
                if sid_str in symbol_map:
                    ohlc = info.get("ohlc", {})
                    result[symbol_map[sid_str]] = {
                        "symbol": symbol_map[sid_str],
                        "ltp": Decimal(str(info.get("last_price", 0))),
                        "open": Decimal(str(ohlc.get("open", 0))),
                        "high": Decimal(str(ohlc.get("high", 0))),
                        "low": Decimal(str(ohlc.get("low", 0))),
                        "close": Decimal(str(ohlc.get("close", 0))),
                        "volume": int(info.get("volume", 0)),
                    }
        
        logger.debug(f"Batch quotes fetched: {len(result)} symbols")
        return result

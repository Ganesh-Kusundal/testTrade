"""TradeX Gateway - High-level broker-agnostic trading API."""

from scalpr.brokers.capabilities import GatewayCapabilities
from scalpr.brokers.contracts import Funds, Holding, MarketDepth, Quote, Trade
from scalpr.brokers.gateway import Gateway
from scalpr.brokers.registry import BrokerRegistry

__all__ = [
    "BrokerRegistry",
    "Funds",
    "Gateway",
    "GatewayCapabilities",
    "Holding",
    "MarketDepth",
    "Quote",
    "Trade",
]

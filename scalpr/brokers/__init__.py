"""TradeX Gateway - High-level broker-agnostic trading API."""

from scalpr.brokers.gateway import Gateway
from scalpr.brokers.registry import BrokerRegistry
from scalpr.brokers.contracts import Quote, MarketDepth, Holding, Funds, Trade
from scalpr.brokers.capabilities import GatewayCapabilities

__all__ = [
    "Gateway",
    "BrokerRegistry",
    "Quote",
    "MarketDepth",
    "Holding",
    "Funds",
    "Trade",
    "GatewayCapabilities",
]

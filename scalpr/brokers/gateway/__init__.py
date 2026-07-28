"""Gateway package — high-level broker-agnostic gateway with intelligent defaults.

This package provides a user-friendly, broker-agnostic Gateway that wraps
IBrokerGateway implementations with sensible defaults, automatic credential
loading, and simplified method signatures.

The Gateway class is composed from multiple mixins:
- MarketDataMixin: ltp, quote, depth, history
- PortfolioMixin: positions, holdings, funds, orders, trades
- StreamingMixin: stream, stop_stream, subscribe_feed, unsubscribe

Usage::

    from scalpr.brokers.gateway import Gateway

    g = Gateway()
    ltp = g.ltp("TCS")
"""
from scalpr.brokers.broker_port import IBrokerGateway
from scalpr.brokers.gateway.facade import Gateway

__all__ = ["Gateway", "IBrokerGateway"]

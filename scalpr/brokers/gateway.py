"""Backward-compatible gateway module.

This module re-exports the Gateway class from the gateway package
for backward compatibility. All existing imports continue to work.

The Gateway class is now implemented as a package with mixins:
- scalpr.brokers.gateway._market_data.MarketDataMixin
- scalpr.brokers.gateway._portfolio.PortfolioMixin
- scalpr.brokers.gateway._streaming.StreamingMixin
- scalpr.brokers.gateway.facade.Gateway (composed from above mixins)
"""
from scalpr.brokers.gateway import Gateway

__all__ = ["Gateway"]

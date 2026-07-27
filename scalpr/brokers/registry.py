"""Broker registry for discovery and instantiation."""

from __future__ import annotations

import logging
from typing import Any

from scalpr.brokers.broker_port import IBrokerGateway

logger = logging.getLogger(__name__)


class BrokerRegistry:
    """Registry for broker discovery and instantiation.

    Provides a central location to register and retrieve broker
    gateway implementations by name.
    """

    _brokers: dict[str, type[IBrokerGateway]] = {}

    @classmethod
    def register(cls, name: str, gateway_class: type[IBrokerGateway]) -> None:
        """Register a broker gateway implementation.

        Args:
            name: Broker name (e.g., "dhan", "paper")
            gateway_class: Gateway class implementing IBrokerGateway
        """
        cls._brokers[name] = gateway_class
        logger.info(f"broker_registered: {name}")

    @classmethod
    def list_brokers(cls) -> list[str]:
        """List all registered broker names.

        Returns:
            List of broker names
        """
        return list(cls._brokers.keys())

    @classmethod
    def get(cls, broker: str, config: dict[str, Any]) -> IBrokerGateway:
        """Instantiate a broker gateway by name.

        Args:
            broker: Broker name (e.g., "dhan", "paper")
            config: Broker-specific configuration dict

        Returns:
            Instantiated gateway implementing IBrokerGateway

        Raises:
            ValueError: If broker is not registered
        """
        if broker not in cls._brokers:
            available = ", ".join(cls.list_brokers())
            raise ValueError(
                f"Unknown broker '{broker}'. Available: {available}"
            )

        gateway_class = cls._brokers[broker]
        logger.info(f"broker_instantiated: {broker}")
        return gateway_class(config)

    @classmethod
    def is_available(cls, broker: str) -> bool:
        """Check if a broker is registered.

        Args:
            broker: Broker name

        Returns:
            True if broker is registered
        """
        return broker in cls._brokers


# Auto-register known brokers
def _register_default_brokers() -> None:
    """Register default broker implementations."""
    try:
        from scalpr.brokers.dhan.gateway import DhanGateway

        BrokerRegistry.register("dhan", DhanGateway)
    except ImportError:
        logger.debug("DhanGateway not available")

    try:
        from scalpr.oms.paper_oms import PaperOms

        BrokerRegistry.register("paper", PaperOms)
    except ImportError:
        logger.debug("PaperOms not available")


# Register on module import
_register_default_brokers()

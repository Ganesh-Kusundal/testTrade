"""Broker registry for discovery and instantiation."""

from __future__ import annotations

import logging
from typing import Any

from scalpr.brokers.broker_port import IBrokerGateway

logger = logging.getLogger(__name__)

# Module-level private dict — avoids mutable class-level state that leaks
# between tests and subclasses. Access only through BrokerRegistry methods.
_brokers: dict[str, type[IBrokerGateway]] = {}

# Adapter registry: broker_name -> {adapter_key -> class/callable}
# Adapters are broker-specific classes (e.g., OptionChainAdapter,
# DhanWebSocketManager) that the broker-agnostic facade needs but
# must not import directly (boundary rule).
_adapters: dict[str, dict[str, Any]] = {}


class BrokerRegistry:
    """Registry for broker discovery and instantiation.

    Provides a central location to register and retrieve broker
    gateway implementations by name.
    """

    @classmethod
    def reset(cls) -> None:
        """Clear all registered brokers and adapters. Use in test teardown."""
        _brokers.clear()
        _adapters.clear()

    @classmethod
    def register(cls, name: str, gateway_class: type[IBrokerGateway]) -> None:
        """Register a broker gateway implementation.

        Args:
            name: Broker name (e.g., "dhan", "paper")
            gateway_class: Gateway class implementing IBrokerGateway
        """
        _brokers[name] = gateway_class
        logger.info("broker_registered: %s", name)

    @classmethod
    def list_brokers(cls) -> list[str]:
        """List all registered broker names.

        Returns:
            List of broker names
        """
        return list(_brokers.keys())

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
        if broker not in _brokers:
            available = ", ".join(cls.list_brokers())
            raise ValueError(
                f"Unknown broker '{broker}'. Available: {available}"
            )

        gateway_class = _brokers[broker]
        logger.info("broker_instantiated: %s", broker)
        return gateway_class(config)

    @classmethod
    def is_available(cls, broker: str) -> bool:
        """Check if a broker is registered.

        Args:
            broker: Broker name

        Returns:
            True if broker is registered
        """
        return broker in _brokers

    @classmethod
    def register_adapter(
        cls, broker: str, key: str, adapter_class: Any
    ) -> None:
        """Register a broker-specific adapter class.

        Adapters are broker-specific classes that the broker-agnostic
        facade needs but must not import directly (boundary rule).

        Args:
            broker: Broker name (e.g., "dhan")
            key: Adapter key (e.g., "option_chain", "ws_manager", "auth")
            adapter_class: The adapter class or callable
        """
        if broker not in _adapters:
            _adapters[broker] = {}
        _adapters[broker][key] = adapter_class
        logger.debug("adapter_registered: %s.%s", broker, key)

    @classmethod
    def get_adapter(cls, broker: str, key: str) -> Any:
        """Retrieve a registered adapter by broker and key.

        Args:
            broker: Broker name
            key: Adapter key

        Returns:
            The adapter class or callable, or None if not found
        """
        return _adapters.get(broker, {}).get(key)


# Auto-register known brokers
def _register_default_brokers() -> None:
    """Register default broker implementations and their adapters."""
    try:
        from scalpr.brokers.dhan.gateway import DhanGateway

        BrokerRegistry.register("dhan", DhanGateway)

        # Register Dhan-specific adapters so the broker-agnostic facade
        # can look them up without importing from brokers.dhan directly.
        from scalpr.brokers.dhan.auth import ensure_fresh_token
        from scalpr.brokers.dhan.option_chain import OptionChainAdapter
        from scalpr.brokers.dhan.ws_manager import DhanWebSocketManager

        BrokerRegistry.register_adapter("dhan", "auth", ensure_fresh_token)
        BrokerRegistry.register_adapter(
            "dhan", "option_chain", OptionChainAdapter
        )
        BrokerRegistry.register_adapter(
            "dhan", "ws_manager", DhanWebSocketManager
        )
    except ImportError:
        logger.debug("DhanGateway not available")

    try:
        from scalpr.oms.paper_oms import PaperOms

        BrokerRegistry.register("paper", PaperOms)
    except ImportError:
        logger.debug("PaperOms not available")


# Register on module import
_register_default_brokers()

"""Order Router - Enforces mandatory risk checks before order submission."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal

from scalpr.brokers.broker_port import IBrokerGateway
from scalpr.domain.events import CircuitBreakerTripped as CircuitBreakerTrippedEvent
from scalpr.domain.events import IEventBus, OrderPlaced
from scalpr.domain.events import RiskCheckFailed as RiskCheckFailedEvent
from scalpr.domain.fill import Fill
from scalpr.domain.order import Order
from scalpr.domain.position import Position
from scalpr.oms.order_manager import OrderManager
from scalpr.risk.circuit_breaker import CircuitBreaker
from scalpr.risk.pre_trade import PreTradeRiskGate

logger = logging.getLogger(__name__)


class RiskCheckFailed(Exception):
    """Raised when pre-trade risk check fails."""
    pass


class CircuitBreakerTripped(Exception):
    """Raised when circuit breaker prevents order submission."""
    pass


class PersistenceError(Exception):
    """Raised when order persistence fails after broker submission."""
    pass


class OrderRouter:
    """
    Mandatory order submission router that enforces risk gates.

    All strategies MUST submit orders through this router, never directly
    to the broker gateway.
    """

    def __init__(
        self,
        gateway: IBrokerGateway,
        risk_gate: PreTradeRiskGate,
        circuit_breaker: CircuitBreaker,
        event_bus: IEventBus | None = None,
        order_manager: OrderManager | None = None,
    ):
        self.gateway = gateway
        self.risk_gate = risk_gate
        self.circuit_breaker = circuit_breaker
        self.event_bus = event_bus
        self.order_manager = order_manager

    def submit_order(
        self,
        order: Order,
        positions: list[Position],
        available_margin: Decimal,
        daily_loss: Decimal,
        portfolio_value: Decimal,
        drawdown: Decimal = Decimal("0"),
    ) -> Fill:
        """
        Submit order through mandatory risk gates.

        Args:
            order: Order to submit
            positions: Current positions
            available_margin: Available margin from broker
            daily_loss: Current daily P&L loss
            portfolio_value: Total portfolio value
            drawdown: Current drawdown percentage (as decimal, e.g., 0.03 = 3%)

        Returns:
            Fill from broker

        Raises:
            CircuitBreakerTripped: If circuit breaker limits exceeded
            RiskCheckFailed: If pre-trade risk check fails
            PersistenceError: If order persistence fails after broker submission
        """
        # 1. Check circuit breaker (system-wide safety)
        if not self.circuit_breaker.check_limits(
            portfolio_value=portfolio_value,
            daily_loss=daily_loss,
            drawdown=drawdown,
        ):
            logger.error(
                f"Circuit breaker tripped - blocking order {order.symbol} "
                f"(daily_loss={daily_loss}, portfolio_value={portfolio_value})"
            )
            # Publish circuit breaker event
            if self.event_bus:
                self.event_bus.publish(
                    CircuitBreakerTrippedEvent(
                        timestamp=datetime.now(timezone.utc),
                        component="OrderRouter",
                        reason=f"Daily loss limit exceeded: {daily_loss}",
                        threshold=Decimal("0.03"),  # 3% default threshold
                        current_value=daily_loss,
                    )
                )
            raise CircuitBreakerTripped(
                f"Circuit breaker tripped: daily_loss={daily_loss}"
            )

        # 2. Pre-trade risk check (order-specific safety)
        order_notional = order.price * Decimal(order.quantity) if order.price else Decimal('0')

        allowed, reason = self.risk_gate.check_order(
            order=order,
            positions=positions,
            available_margin=available_margin,
            required_margin=order_notional * Decimal('0.2'),  # 20% margin requirement
            daily_loss=daily_loss,
        )

        if not allowed:
            logger.warning(
                f"Risk check failed for order {order.symbol}: {reason}"
            )
            # Publish risk check failed event
            if self.event_bus:
                self.event_bus.publish(
                    RiskCheckFailedEvent(
                        timestamp=datetime.now(timezone.utc),
                        check_name="PreTradeRiskGate",
                        order=order,
                        reason=reason,
                    )
                )
            raise RiskCheckFailed(reason)

        # 3. All checks passed - forward to broker
        logger.info(f"Order {order.symbol} passed risk checks, submitting to broker")
        fill = self.gateway.place_order(order)

        # Persist order and fill via OrderManager
        if self.order_manager:
            try:
                self.order_manager.add_order(order)
                if fill:
                    self.order_manager.process_fill(fill)
            except Exception as e:
                logger.error(f"CRITICAL: Persistence failed after order placed: {e}")
                raise PersistenceError(
                    f"Order {order.order_id} placed at broker but persistence failed: {e}"
                ) from e

        # Publish OrderPlaced event
        if self.event_bus:
            self.event_bus.publish(
                OrderPlaced(
                    timestamp=datetime.now(timezone.utc),
                    order=order,
                )
            )

        return fill

"""Order Router - Enforces mandatory risk checks before order submission."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from scalpr.domain.errors import (
    CircuitBreakerTripped,
    OrderRateLimitExceeded,
    PersistenceError,
    RiskCheckFailed,
)
from scalpr.domain.events import CircuitBreakerTripped as CircuitBreakerTrippedEvent
from scalpr.domain.events import IEventBus, OrderPlaced
from scalpr.domain.events import RiskCheckFailed as RiskCheckFailedEvent
from scalpr.domain.fill import Fill
from scalpr.domain.order import Order, OrderType
from scalpr.domain.position import Position
from scalpr.domain.values import ZERO
from scalpr.observability.correlation import set_correlation_id
from scalpr.oms.order_manager import OrderManager
from scalpr.risk.circuit_breaker import CircuitBreaker
from scalpr.risk.order_rate_limiter import OrderRateLimiter
from scalpr.risk.pre_trade import PreTradeRiskGate

logger = logging.getLogger(__name__)


# Re-export for test imports (backward compatibility)
__all__ = [
    "CircuitBreakerTripped",
    "OrderRateLimitExceeded",
    "OrderRouter",
    "PersistenceError",
    "RiskCheckFailed",
]


class OrderRouter:
    """
    Mandatory order submission router that enforces risk gates.

    All strategies MUST submit orders through this router, never directly
    to the broker gateway.
    """

    def __init__(
        self,
        gateway: Any,
        risk_gate: PreTradeRiskGate,
        circuit_breaker: CircuitBreaker,
        event_bus: IEventBus | None = None,
        order_manager: OrderManager | None = None,
        rate_limiter: OrderRateLimiter | None = None,
    ):
        self.gateway = gateway
        self.risk_gate = risk_gate
        self.circuit_breaker = circuit_breaker
        self.event_bus = event_bus
        self.order_manager = order_manager
        self.rate_limiter = rate_limiter

    def submit_order(
        self,
        order: Order,
        positions: list[Position],
        available_margin: Decimal,
        daily_loss: Decimal,
        portfolio_value: Decimal,
        drawdown: Decimal = ZERO,
        ltp: Decimal | None = None,
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
            ltp: Last traded price for MARKET order notional calculation (K-020)

        Returns:
            Fill from broker

        Raises:
            CircuitBreakerTripped: If circuit breaker limits exceeded
            RiskCheckFailed: If pre-trade risk check fails
            OrderRateLimitExceeded: If order submission rate limit exceeded
        """
        # Set correlation ID for this order's lifecycle (enables log tracing)
        if order.correlation_id:
            set_correlation_id(order.correlation_id)

        # 0. Rate limit check (fail fast — K-019)
        if self.rate_limiter and not self.rate_limiter.acquire():
            logger.warning(
                "Order rate limit exceeded for %s — rejecting order", order.symbol
            )
            raise OrderRateLimitExceeded(
                f"Order submission rate limit exceeded for {order.symbol}",
                correlation_id=order.correlation_id,
                context={"symbol": order.symbol, "order_id": order.order_id},
            )

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
                        threshold=float(Decimal("0.03")),  # 3% default threshold
                        current_value=float(daily_loss),
                    )
                )
            raise CircuitBreakerTripped(
                f"Circuit breaker tripped: daily_loss={daily_loss}",
                correlation_id=order.correlation_id,
                context={
                    "symbol": order.symbol,
                    "daily_loss": str(daily_loss),
                    "portfolio_value": str(portfolio_value),
                },
            )

        # 2. Pre-trade risk check (order-specific safety)
        # K-020: Use LTP for MARKET orders, order.price for LIMIT
        effective_price = ltp if (order.order_type == OrderType.MARKET and ltp) else order.price
        order_notional = effective_price * Decimal(order.quantity) if effective_price else Decimal('0')

        allowed, reason = self.risk_gate.check_order(
            order=order,
            positions=positions,
            available_margin=available_margin,
            required_margin=order_notional * Decimal('0.2'),  # 20% margin requirement
            daily_loss=daily_loss,
            ltp=ltp,
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
            raise RiskCheckFailed(
                reason,
                correlation_id=order.correlation_id,
                context={"symbol": order.symbol, "order_id": order.order_id},
            )

        # 3. All checks passed - persist FIRST, then forward to broker (K-016)
        logger.info("Order %s passed risk checks, persisting to OMS first", order.symbol)
        if self.order_manager:
            self.order_manager.add_order(order)

        # 4. Submit to broker
        result = self.gateway.place_order(order)
        if isinstance(result, Fill):
            fill = result
        else:
            order_id = str(result)
            fill = Fill(
                fill_id=order_id,
                order_id=order_id,
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity,
                price=order.price if order.price is not None else Decimal("0"),
                timestamp=datetime.now(timezone.utc),
            )

        # 5. Process fill via OrderManager
        if self.order_manager and fill:
            self.order_manager.process_fill(fill)

        # Publish OrderPlaced event
        if self.event_bus:
            self.event_bus.publish(
                OrderPlaced(
                    timestamp=datetime.now(timezone.utc),
                    order=order,
                )
            )

        return fill

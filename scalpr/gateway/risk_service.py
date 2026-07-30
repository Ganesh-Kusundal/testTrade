from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from scalpr.adapters.dhan.client import DhanClient
from scalpr.domain.errors import InvalidOrder
from scalpr.domain.instrument import ResolvedInstrument
from scalpr.domain.order import OrderRequest, ProductType

logger = logging.getLogger(__name__)


class RiskService:
    """Validates order requests against exchange/instrument constraints.

    Checks: lot-size multiples, tick-size alignment, freeze quantity,
    quantity positivity, product validity by segment.
    """

    def __init__(self, client: DhanClient) -> None:
        self._client = client

    def validate(self, request: OrderRequest) -> None:
        """Validate an order request. Raises InvalidOrder on failure."""
        resolved = self._resolve(request)

        # Quantity positivity
        if request.quantity <= 0:
            raise InvalidOrder(f"quantity must be positive, got {request.quantity}")

        # Lot-size check for derivatives
        if resolved.lot_size is not None and resolved.lot_size > 1:
            if request.quantity % resolved.lot_size != 0:
                raise InvalidOrder(
                    f"quantity {request.quantity} is not a multiple of lot_size {resolved.lot_size}"
                )

        # Freeze quantity check
        if resolved.freeze_quantity is not None and request.quantity > resolved.freeze_quantity:
            raise InvalidOrder(
                f"quantity {request.quantity} exceeds freeze quantity {resolved.freeze_quantity}"
            )

        # Tick-size alignment for LIMIT orders
        if request.order_type.value == "LIMIT" and request.price is not None:
            if resolved.tick_size is not None:
                remainder = request.price % resolved.tick_size
                if remainder != Decimal("0"):
                    raise InvalidOrder(
                        f"price {request.price} is not aligned to tick_size {resolved.tick_size}"
                    )

        # Product validity by segment
        _validate_product_for_segment(request.product, resolved)

    def _resolve(self, request: OrderRequest) -> ResolvedInstrument:
        if hasattr(request.instrument, "resolved"):
            return request.instrument.resolved
        return self._client.resolve_instrument(request.instrument)


def _validate_product_for_segment(product: ProductType, resolved: ResolvedInstrument) -> None:
    """Validate that the product type is valid for the instrument's segment."""
    # CO (Cover Order) and BO (Bracket Order) are only valid for F&O
    if product in (ProductType.COVER_ORDER,):
        if resolved.segment.value not in ("FUTURES", "OPTIONS"):
            raise InvalidOrder(
                f"product {product.value} is only valid for F&O instruments, "
                f"got segment {resolved.segment.value}"
            )

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(slots=True, frozen=True)
class DhanOrderRequest:
    """DTO representing an order request payload for Dhan API."""
    dhanClientId: str
    correlationId: str
    transactionType: str
    exchangeSegment: str
    productType: str
    orderType: str
    quantity: int
    price: Decimal
    triggerPrice: Decimal
    securityId: str


@dataclass(slots=True, frozen=True)
class DhanOrderResponse:
    """DTO representing an order response payload from Dhan API."""
    orderId: str
    orderStatus: str
    errorCode: str
    errorMessage: str

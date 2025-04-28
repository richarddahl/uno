# SPDX-FileCopyrightText: 2025-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""
Domain model: Order aggregate and related events.
Represents an order to purchase or sell InventoryLots of a particular InventoryItem to/from a Vendor.
Implements Uno canonical serialization, DDD, and event sourcing contracts.
"""

from typing import Literal, Self

from pydantic import PrivateAttr

from uno.core.domain.aggregate import AggregateRoot
from uno.core.domain.event import DomainEvent
from uno.core.errors.base import get_error_context
from uno.core.errors.definitions import DomainValidationError
from uno.core.errors.result import Success, Failure


# --- Events ---
class OrderCreated(DomainEvent):
    order_id: str
    item_id: str
    lot_id: str
    vendor_id: str
    quantity: int
    price: float
    order_type: Literal["purchase", "sale"]


class OrderFulfilled(DomainEvent):
    order_id: str
    fulfilled_quantity: int


class OrderCancelled(DomainEvent):
    order_id: str
    reason: str | None = None


# --- Aggregate ---
class Order(AggregateRoot[str]):
    item_id: str
    lot_id: str
    vendor_id: str
    quantity: int
    price: float
    order_type: Literal["purchase", "sale"]
    is_fulfilled: bool = False
    is_cancelled: bool = False
    _domain_events: list[DomainEvent] = PrivateAttr(default_factory=list)

    @classmethod
    def create(
        cls,
        order_id: str,
        item_id: str,
        lot_id: str,
        vendor_id: str | None,
        quantity: int,
        price: float,
        order_type: str,
    ) -> Success[Self, Exception] | Failure[None, Exception]:
        try:
            if not order_id:
                return Failure(DomainValidationError("order_id is required", details=get_error_context()))
            if not item_id:
                return Failure(DomainValidationError("item_id is required", details=get_error_context()))
            if not lot_id:
                return Failure(DomainValidationError("lot_id is required", details=get_error_context()))
            if quantity < 0:
                return Failure(DomainValidationError("quantity must be non-negative", details=get_error_context()))
            if price < 0:
                return Failure(DomainValidationError("price must be non-negative", details=get_error_context()))
            if not order_type:
                return Failure(DomainValidationError("order_type is required", details=get_error_context()))
            order = cls(
                id=order_id,
                item_id=item_id,
                lot_id=lot_id,
                vendor_id=vendor_id,
                quantity=quantity,
                price=price,
                order_type=order_type,
            )
            event = OrderCreated(
                order_id=order_id,
                item_id=item_id,
                lot_id=lot_id,
                vendor_id=vendor_id,
                quantity=quantity,
                price=price,
                order_type=order_type,
            )
            order._record_event(event)
            return Success(order)
        except Exception as e:
            return Failure(DomainValidationError(str(e), details=get_error_context()))

    def fulfill(self, fulfilled_quantity: int) -> None:
        event = OrderFulfilled(order_id=self.id, fulfilled_quantity=fulfilled_quantity)
        self._record_event(event)

    def cancel(self, reason: str | None = None) -> None:
        event = OrderCancelled(order_id=self.id, reason=reason)
        self._record_event(event)

    def _record_event(self, event: DomainEvent) -> None:
        self._domain_events.append(event)
        self._apply_event(event)

    def _apply_event(self, event: DomainEvent) -> None:
        if isinstance(event, OrderCreated):
            self.item_id = event.item_id
            self.lot_id = event.lot_id
            self.vendor_id = event.vendor_id
            self.quantity = event.quantity
            self.price = event.price
            self.order_type = event.order_type
        elif isinstance(event, OrderFulfilled):
            self.is_fulfilled = True
        elif isinstance(event, OrderCancelled):
            self.is_cancelled = True
        else:
            raise DomainValidationError(
                f"Unhandled event: {event}", details=get_error_context()
            )

    # Canonical serialization already handled by AggregateRoot/Entity base

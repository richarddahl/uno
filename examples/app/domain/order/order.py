# SPDX-FileCopyrightText: 2025-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""
Domain model: Order aggregate and related events.
Represents an order to purchase or sell InventoryLots of a particular InventoryItem to/from a Vendor.
Implements Uno canonical serialization, DDD, and event sourcing contracts.
"""

from typing import ClassVar, Literal, Self

from pydantic import PrivateAttr

from examples.app.domain.order.events import (
    OrderCancelled,
    OrderCreated,
    OrderFulfilled,
)
from examples.app.domain.value_objects import Count, Money, Quantity
from uno.core.domain.aggregate import AggregateRoot
from uno.core.domain.entity import Entity
from uno.core.domain.event import DomainEvent
from uno.core.errors.base import get_error_context
from uno.core.errors.definitions import DomainValidationError
from uno.core.errors.result import Failure, Success


class Order(Entity[str]):
    """
    Order aggregate root.

    Note: to_dict() is always canonical and contract-compliant (see Uno DDD base classes).
    Use to_dict() for all serialization needs.
    """

    @classmethod
    def replay_from_events(cls, id: str, events: list[DomainEvent]) -> "Order":
        """
        Create an Order instance for event sourcing replay. Initializes with placeholder values, then applies the given events in order.

        Note:
            This method is used for event sourcing and aggregate rehydration. It relies on internal mutation of a frozen Pydantic model
            via `object.__setattr__` in `_apply_event`, which is the idiomatic and recommended approach for DDD/event sourcing with Pydantic v2.
            Direct mutation is only permitted in this tightly controlled context; all other code should treat the model as immutable.
        """
        from examples.app.domain.value_objects import Quantity, Money, Currency

        dummy = cls(
            id=id,
            item_id="PLACEHOLDER",
            lot_id="PLACEHOLDER",
            vendor_id="PLACEHOLDER",
            quantity=Quantity.from_count(0),
            price=Money.from_value(0, currency=Currency.USD).unwrap(),
            order_type="purchase",
        )
        for event in events:
            dummy._apply_event(event)
        return dummy

    item_id: str
    lot_id: str
    vendor_id: str
    quantity: Quantity
    price: Money
    order_type: Literal["purchase", "sale"]
    is_fulfilled: bool = False
    is_cancelled: bool = False
    _domain_events: list[DomainEvent] = PrivateAttr(default_factory=list)

    # Note: to_dict() is always canonical and contract-compliant (see Uno DDD base classes).
    # No need for a separate to_dict. Use to_dict() for all serialization needs.

    @classmethod
    def create(
        cls,
        order_id: str,
        item_id: str,
        lot_id: str,
        vendor_id: str,
        quantity: Quantity | Count | float | int,
        price: Money,
        order_type: str,
    ) -> Success[Self, Exception] | Failure[None, Exception]:
        from examples.app.domain.value_objects import Quantity, Count

        try:
            if not order_id:
                return Failure(
                    DomainValidationError(
                        "order_id is required", details=get_error_context()
                    )
                )
            if not item_id:
                return Failure(
                    DomainValidationError(
                        "item_id is required", details=get_error_context()
                    )
                )
            if not lot_id:
                return Failure(
                    DomainValidationError(
                        "lot_id is required", details=get_error_context()
                    )
                )
            # Accept Quantity, Count, int, float for quantity
            if isinstance(quantity, Quantity):
                q = quantity
            elif isinstance(quantity, Count):
                q = Quantity.from_count(quantity)
            elif isinstance(quantity, int | float):
                if quantity < 0:
                    return Failure(
                        DomainValidationError(
                            "quantity must be non-negative",
                            details=get_error_context(),
                        )
                    )
                q = Quantity.from_count(quantity)
            else:
                return Failure(
                    DomainValidationError(
                        "quantity must be a Quantity, Count, int, or float",
                        details=get_error_context(),
                    )
                )
            if not isinstance(price, Money):
                return Failure(
                    DomainValidationError(
                        "price must be a Money value object",
                        details=get_error_context(),
                    )
                )
            if not order_type:
                return Failure(
                    DomainValidationError(
                        "order_type is required", details=get_error_context()
                    )
                )
            order = cls(
                id=order_id,
                item_id=item_id,
                lot_id=lot_id,
                vendor_id=vendor_id,
                quantity=q,
                price=price,
                order_type=order_type,
            )
            event = OrderCreated(
                order_id=order_id,
                item_id=item_id,
                lot_id=lot_id,
                vendor_id=vendor_id,
                quantity=q,
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
        """
        Internal: Applies a domain event to this aggregate, mutating state as needed.

        This method uses `object.__setattr__` to mutate fields on a frozen Pydantic model. This is the idiomatic and recommended approach
        for event replay/rehydration in DDD systems using Pydantic v2. Direct mutation is strictly limited to this internal mechanism.
        """
        from examples.app.domain.value_objects import Quantity, Count, Money

        if isinstance(event, OrderCreated):
            # All field assignments here use object.__setattr__ to bypass Pydantic's frozen model restriction.
            # This is intentional and safe ONLY for event replay/rehydration.
            object.__setattr__(self, "item_id", event.item_id)
            object.__setattr__(self, "lot_id", event.lot_id)
            object.__setattr__(self, "vendor_id", event.vendor_id)
            # Accept Quantity, Count, int, float for replay
            if isinstance(event.quantity, Quantity):
                object.__setattr__(self, "quantity", event.quantity)
            elif isinstance(event.quantity, Count | int | float):
                object.__setattr__(
                    self, "quantity", Quantity.from_count(event.quantity)
                )
            else:
                raise DomainValidationError(
                    "Invalid quantity type for replay", details=get_error_context()
                )
            object.__setattr__(
                self,
                "price",
                (
                    event.price
                    if isinstance(event.price, Money)
                    else Money.from_value(
                        event.price, currency=getattr(event.price, "currency", "USD")
                    ).unwrap()
                ),
            )
            object.__setattr__(self, "order_type", event.order_type)
        elif isinstance(event, OrderFulfilled):
            object.__setattr__(self, "is_fulfilled", True)
        elif isinstance(event, OrderCancelled):
            object.__setattr__(self, "is_cancelled", True)
        else:
            raise DomainValidationError(
                f"Unhandled event: {event}", details=get_error_context()
            )

    def validate(self) -> Success[None, Exception] | Failure[None, Exception]:
        """
        Validate the aggregate's invariants. Returns Success(None) if valid, Failure(None, Exception) otherwise.
        """
        from uno.core.errors.result import Success, Failure
        from uno.core.errors.definitions import DomainValidationError
        from uno.core.errors.base import get_error_context
        from examples.app.domain.value_objects import Money, Quantity

        if self.quantity is None or not isinstance(self.quantity, Quantity):
            return Failure(DomainValidationError("quantity must be a Quantity value object", details=get_error_context()))
        if self.quantity.value.value < 0:
            return Failure(DomainValidationError("quantity must be non-negative", details=get_error_context()))
        if self.price is None or not isinstance(self.price, Money):
            return Failure(DomainValidationError("price must be a Money value object", details=get_error_context()))
        if self.order_type not in ("purchase", "sale"):
            return Failure(DomainValidationError(f"order_type must be 'purchase' or 'sale', got {self.order_type}", details=get_error_context()))
        if self.is_fulfilled and self.is_cancelled:
            return Failure(DomainValidationError("Order cannot be both fulfilled and cancelled", details=get_error_context()))
        # Add more invariants as needed
        return Success(None)

    # Canonical serialization already handled by AggregateRoot/Entity base

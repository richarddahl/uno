# SPDX-FileCopyrightText: 2025-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""
Domain model: Order aggregate and related events.
Represents an order to purchase or sell InventoryLots of a particular InventoryItem to/from a Vendor.
Implements Uno canonical serialization, DDD, and event sourcing contracts.
"""

from typing import Literal, Self

from pydantic import PrivateAttr, model_validator

from examples.app.domain.inventory.measurement import Measurement
from examples.app.domain.inventory.value_objects import Money, Count
from examples.app.domain.order.events import (
    OrderCreated,
    OrderFulfilled,
    OrderCancelled,
)
from uno.domain.aggregate import AggregateRoot
from uno.errors.base import get_error_context
from uno.domain.errors import DomainValidationError
from uno.events import DomainEvent


class Order(AggregateRoot[str]):
    """
    Order aggregate root.

    Note: to_dict() is always canonical and contract-compliant (see Uno DDD base classes).
    Use to_dict() for all serialization needs.
    """

    @classmethod
    def from_events(cls, events: list[DomainEvent]) -> "Order":
        """
        Canonical Uno event replay/rehydration method.
        """
        if not events:
            raise DomainValidationError("No events to rehydrate Order.")
        instance = cls.__new__(cls)
        for event in events:
            instance.apply_event(event)
        return instance

    aggregate_id: str
    lot_id: str
    vendor_id: str
    measurement: Measurement
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
        aggregate_id: str,
        lot_id: str,
        vendor_id: str,
        measurement: int | float | Count | Measurement,
        price: Money,
        order_type: str,
    ) -> Self:
        """
        Create a new Order with validation.

        Args:
            order_id: The ID for the new order
            aggregate_id: The aggregate ID
            lot_id: The ID of the inventory lot
            vendor_id: The ID of the vendor
            measurement: The measurement (quantity)
            price: The price
            order_type: Type of order (purchase or sale)

        Returns:
            A new Order instance

        Raises:
            DomainValidationError: If validation fails
        """
        try:
            if not order_id:
                raise DomainValidationError(
                    "order_id is required", details=get_error_context()
                )
            if not aggregate_id:
                raise DomainValidationError(
                    "aggregate_id is required", details=get_error_context()
                )
            if not lot_id:
                raise DomainValidationError(
                    "lot_id is required", details=get_error_context()
                )
            if not vendor_id:
                raise DomainValidationError(
                    "vendor_id is required", details=get_error_context()
                )
            if isinstance(measurement, Measurement):
                m = measurement
            elif isinstance(measurement, Count):
                m = Measurement.from_count(measurement)
            elif isinstance(measurement, int | float):
                m = Measurement.from_each(measurement)
            if not order_type:
                raise DomainValidationError(
                    "order_type is required", details=get_error_context()
                )
            order = cls(
                id=order_id,
                aggregate_id=aggregate_id,
                lot_id=lot_id,
                vendor_id=vendor_id,
                measurement=m,
                price=price,
                order_type=order_type,
            )
            event = OrderCreated(
                order_id=order_id,
                aggregate_id=aggregate_id,
                lot_id=lot_id,
                vendor_id=vendor_id,
                measurement=m,
                price=price,
                order_type=order_type,
            )
            order.add_event(event)
            return order
        except Exception as e:
            if isinstance(e, DomainValidationError):
                raise
            raise DomainValidationError(str(e), details=get_error_context()) from e

    def fulfill(self, fulfilled_measurement: int) -> None:
        event = OrderFulfilled(
            order_id=self.id, fulfilled_measurement=fulfilled_measurement
        )
        self.add_event(event)

    def cancel(self, reason: str | None = None) -> None:
        event = OrderCancelled(order_id=self.id, reason=reason)
        self.add_event(event)

    def add_event(self, event: DomainEvent) -> None:
        self._domain_events.append(event)
        self.apply_event(event)

    def apply_event(self, event: DomainEvent) -> None:
        if isinstance(event, OrderCreated):
            object.__setattr__(self, "aggregate_id", event.aggregate_id)
            object.__setattr__(self, "lot_id", event.lot_id)
            object.__setattr__(self, "vendor_id", event.vendor_id)
            if isinstance(event.measurement, Measurement):
                object.__setattr__(self, "measurement", event.measurement)
            elif isinstance(event.measurement, Count | int | float):
                object.__setattr__(
                    self, "measurement", Measurement.from_count(event.measurement)
                )
            else:
                raise DomainValidationError(
                    "Invalid measurement type for replay", details=get_error_context()
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

    @model_validator(mode="after")
    def check_invariants(self) -> Self:
        """
        Validate the aggregate's invariants. Raises ValueError if invalid, returns self if valid.
        """
        if self.measurement is None or not isinstance(self.measurement, Measurement):
            raise ValueError("measurement must be a valid Measurement instance")
        if self.order_type not in ("purchase", "sale"):
            raise ValueError(
                f"order_type must be 'purchase' or 'sale', got {self.order_type}"
            )
        if self.is_fulfilled and self.is_cancelled:
            raise ValueError("Order cannot be both fulfilled and cancelled")
        # Add more invariants as needed
        return self

    # Canonical serialization already handled by AggregateRoot base

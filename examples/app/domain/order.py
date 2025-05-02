# SPDX-FileCopyrightText: 2025-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""
Domain model: Order aggregate and related events.
Represents an order to purchase or sell InventoryLots of a particular InventoryItem to/from a Vendor.
Implements Uno canonical serialization, DDD, and event sourcing contracts.
"""

from typing import ClassVar, Literal, Self

from pydantic import PrivateAttr

from examples.app.domain.value_objects import Money, Quantity, Count
from uno.core.domain.aggregate import AggregateRoot
from uno.core.domain.event import DomainEvent
from uno.core.errors.base import get_error_context
from uno.core.errors.definitions import DomainValidationError
from uno.core.errors.result import Failure, Success


# --- Events ---
class OrderCreated(DomainEvent):
    """
    Event: Order was created.

    Usage:
        result = OrderCreated.create(
            order_id="O100",
            item_id="A100",
            lot_id="L100",
            vendor_id="V100",
            quantity=Quantity(10),
            price=Money(25.0),
            order_type="purchase",
        )
        if isinstance(result, Success):
            event = result.value
        else:
            # handle error context
            ...
    """

    order_id: str
    item_id: str
    lot_id: str
    vendor_id: str
    quantity: Quantity
    price: Money
    order_type: Literal["purchase", "sale"]
    version: int = 1
    model_config = {"frozen": True}

    @classmethod
    def create(
        cls,
        order_id: str,
        item_id: str,
        lot_id: str,
        vendor_id: str,
        quantity: Quantity | Count | float | int,
        price: Money,
        order_type: Literal["purchase", "sale"],
        version: int = 1,
    ) -> Success[Self, Exception] | Failure[Self, Exception]:
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
            if not vendor_id:
                return Failure(
                    DomainValidationError(
                        "vendor_id is required", details=get_error_context()
                    )
                )
            # Accept Quantity, Count, int, float for quantity
            if isinstance(quantity, Quantity):
                q = quantity
            elif isinstance(quantity, Count):
                q = Quantity.from_count(quantity)
            elif isinstance(quantity, (int, float)):
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
            if order_type not in ("purchase", "sale"):
                return Failure(
                    DomainValidationError(
                        "order_type must be 'purchase' or 'sale'",
                        details=get_error_context(),
                    )
                )
            event = cls(
                order_id=order_id,
                item_id=item_id,
                lot_id=lot_id,
                vendor_id=vendor_id,
                quantity=q,
                price=price,
                order_type=order_type,
                version=version,
            )
            return Success(event)
        except Exception as exc:
            return Failure(
                DomainValidationError(
                    "Failed to create OrderCreated", details={"error": str(exc)}
                )
            )

    def upcast(
        self, target_version: int
    ) -> Success[Self, Exception] | Failure[Self, Exception]:
        """
        Upcast event to target version. Stub for future event versioning.
        """
        if target_version == self.version:
            return Success(self)
        return Failure(
            DomainValidationError(
                "Upcasting not implemented",
                details={"from": self.version, "to": target_version},
            )
        )


class OrderFulfilled(DomainEvent):
    """
    Event: Order was fulfilled.

    Usage:
        result = OrderFulfilled.create(
            order_id="O100",
            fulfilled_quantity=10,
        )
        if isinstance(result, Success):
            event = result.value
        else:
            # handle error context
            ...
    """

    order_id: str
    fulfilled_quantity: int
    version: int = 1
    model_config = {"frozen": True}

    @classmethod
    def create(
        cls,
        order_id: str,
        fulfilled_quantity: int,
        version: int = 1,
    ) -> Success[Self, Exception] | Failure[Self, Exception]:
        try:
            if not order_id:
                return Failure(
                    DomainValidationError(
                        "order_id is required", details=get_error_context()
                    )
                )
            if fulfilled_quantity < 0:
                return Failure(
                    DomainValidationError(
                        "fulfilled_quantity must be non-negative",
                        details=get_error_context(),
                    )
                )
            event = cls(
                order_id=order_id,
                fulfilled_quantity=fulfilled_quantity,
                version=version,
            )
            return Success(event)
        except Exception as exc:
            return Failure(
                DomainValidationError(
                    "Failed to create OrderFulfilled", details={"error": str(exc)}
                )
            )

    def upcast(
        self, target_version: int
    ) -> Success[Self, Exception] | Failure[Self, Exception]:
        if target_version == self.version:
            return Success(self)
        return Failure(
            DomainValidationError(
                "Upcasting not implemented",
                details={"from": self.version, "to": target_version},
            )
        )


class OrderCancelled(DomainEvent):
    """
    Event: Order was cancelled.

    Usage:
        result = OrderCancelled.create(
            order_id="O100",
            reason="Customer request",
        )
        if isinstance(result, Success):
            event = result.value
        else:
            # handle error context
            ...
    """

    order_id: str
    reason: str | None = None
    version: int = 1
    model_config = {"frozen": True}

    @classmethod
    def create(
        cls,
        order_id: str,
        reason: str | None = None,
        version: int = 1,
    ) -> Success[Self, Exception] | Failure[Self, Exception]:
        try:
            if not order_id:
                return Failure(
                    DomainValidationError(
                        "order_id is required", details=get_error_context()
                    )
                )
            event = cls(order_id=order_id, reason=reason, version=version)
            return Success(event)
        except Exception as exc:
            return Failure(
                DomainValidationError(
                    "Failed to create OrderCancelled", details={"error": str(exc)}
                )
            )

    def upcast(
        self, target_version: int
    ) -> Success[Self, Exception] | Failure[Self, Exception]:
        if target_version == self.version:
            return Success(self)
        return Failure(
            DomainValidationError(
                "Upcasting not implemented",
                details={"from": self.version, "to": target_version},
            )
        )


# --- Aggregate ---
class Order(AggregateRoot[str]):
    item_id: str
    lot_id: str
    vendor_id: str
    quantity: Quantity
    price: Money
    order_type: Literal["purchase", "sale"]
    is_fulfilled: bool = False
    is_cancelled: bool = False
    _domain_events: ClassVar[list[DomainEvent]] = PrivateAttr(default_factory=list)

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
            elif isinstance(quantity, (int, float)):
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
        from examples.app.domain.value_objects import Quantity, Count, Money
        if isinstance(event, OrderCreated):
            self.item_id = event.item_id
            self.lot_id = event.lot_id
            self.vendor_id = event.vendor_id
            # Accept Quantity, Count, int, float for replay
            if isinstance(event.quantity, Quantity):
                self.quantity = event.quantity
            elif isinstance(event.quantity, Count):
                self.quantity = Quantity.from_count(event.quantity)
            elif isinstance(event.quantity, (int, float)):
                self.quantity = Quantity.from_count(event.quantity)
            else:
                raise DomainValidationError("Invalid quantity type for replay", details=get_error_context())
            self.price = event.price if isinstance(event.price, Money) else Money.from_value(event.price, currency=getattr(event.price, 'currency', "USD")).unwrap()
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

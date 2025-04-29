# SPDX-FileCopyrightText: 2025-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""
Domain model: InventoryItem aggregate and events (vertical slice reference).
Implements Uno canonical serialization, DDD, and event sourcing contracts.
"""

from pydantic import PrivateAttr
from typing import Self
from uno.core.domain.aggregate import AggregateRoot
from uno.core.domain.event import DomainEvent
from uno.core.errors.result import Result, Success, Failure
from uno.core.errors.base import get_error_context
from uno.core.errors.definitions import DomainValidationError


# --- Events ---
class InventoryItemCreated(DomainEvent):
    """
    Event: InventoryItem was created.

    Usage:
        result = InventoryItemCreated.create(
            item_id="A100",
            name="Widget",
            quantity=100,
        )
        if isinstance(result, Success):
            event = result.value
        else:
            # handle error context
            ...
    """
    item_id: str
    name: str
    quantity: int
    version: int = 1

    @classmethod
    def create(
        cls,
        item_id: str,
        name: str,
        quantity: int,
        version: int = 1,
    ) -> Success[Self, Exception] | Failure[Self, Exception]:
        try:
            if not item_id:
                return Failure(DomainValidationError("item_id is required", details={"item_id": item_id}))
            if not name:
                return Failure(DomainValidationError("name is required", details={"name": name}))
            if not isinstance(quantity, int) or quantity < 0:
                return Failure(DomainValidationError("quantity must be a non-negative int", details={"quantity": quantity}))
            event = cls(
                item_id=item_id,
                name=name,
                quantity=quantity,
                version=version,
            )
            return Success(event)
        except Exception as exc:
            return Failure(DomainValidationError("Failed to create InventoryItemCreated", details={"error": str(exc)}))

    def upcast(self, target_version: int) -> Success[Self, Exception] | Failure[Self, Exception]:
        """
        Upcast event to target version. Stub for future event versioning.
        """
        if target_version == self.version:
            return Success(self)
        return Failure(DomainValidationError("Upcasting not implemented", details={"from": self.version, "to": target_version}))


class InventoryItemRenamed(DomainEvent):
    """
    Event: InventoryItem was renamed.

    Usage:
        result = InventoryItemRenamed.create(
            item_id="sku-123",
            new_name="Gadget",
        )
        if isinstance(result, Success):
            event = result.value
        else:
            # handle error context
            ...
    """
    item_id: str
    new_name: str
    version: int = 1

    @classmethod
    def create(
        cls,
        item_id: str,
        new_name: str,
        version: int = 1,
    ) -> Success[Self, Exception] | Failure[Self, Exception]:
        try:
            if not item_id:
                return Failure(DomainValidationError("item_id is required", details={"item_id": item_id}))
            if not new_name:
                return Failure(DomainValidationError("new_name is required", details={"new_name": new_name}))
            event = cls(
                item_id=item_id,
                new_name=new_name,
                version=version,
            )
            return Success(event)
        except Exception as exc:
            return Failure(DomainValidationError("Failed to create InventoryItemRenamed", details={"error": str(exc)}))

    def upcast(self, target_version: int) -> Success[Self, Exception] | Failure[Self, Exception]:
        """
        Upcast event to target version. Stub for future event versioning.
        """
        if target_version == self.version:
            return Success(self)
        return Failure(DomainValidationError("Upcasting not implemented", details={"from": self.version, "to": target_version}))


class InventoryItemAdjusted(DomainEvent):
    """
    Event: InventoryItem was adjusted.

    Usage:
        result = InventoryItemAdjusted.create(
            item_id="sku-123",
            adjustment=5,
        )
        if isinstance(result, Success):
            event = result.value
        else:
            # handle error context
            ...
    """
    item_id: str
    adjustment: int  # positive or negative
    version: int = 1

    @classmethod
    def create(
        cls,
        item_id: str,
        adjustment: int,
        version: int = 1,
    ) -> Success[Self, Exception] | Failure[Self, Exception]:
        try:
            if not item_id:
                return Failure(DomainValidationError("item_id is required", details={"item_id": item_id}))
            if not isinstance(adjustment, int):
                return Failure(DomainValidationError("adjustment must be an int", details={"adjustment": adjustment}))
            event = cls(
                item_id=item_id,
                adjustment=adjustment,
                version=version,
            )
            return Success(event)
        except Exception as exc:
            return Failure(DomainValidationError("Failed to create InventoryItemAdjusted", details={"error": str(exc)}))

    def upcast(self, target_version: int) -> Success[Self, Exception] | Failure[Self, Exception]:
        """
        Upcast event to target version. Stub for future event versioning.
        """
        if target_version == self.version:
            return Success(self)
        return Failure(DomainValidationError("Upcasting not implemented", details={"from": self.version, "to": target_version}))


# --- Aggregate ---
class InventoryItem(AggregateRoot[str]):
    name: str
    quantity: int
    _domain_events: list[DomainEvent] = PrivateAttr(default_factory=list)

    @classmethod
    def create(cls, item_id: str, name: str, quantity: int) -> Result[Self, Exception]:
        try:
            if not item_id:
                return Failure(DomainValidationError("item_id is required", details=get_error_context()))
            if not name:
                return Failure(DomainValidationError("name is required", details=get_error_context()))
            if quantity < 0:
                return Failure(DomainValidationError("quantity must be non-negative", details=get_error_context()))
            item = cls(id=item_id, name=name, quantity=quantity)
            event = InventoryItemCreated(item_id=item_id, name=name, quantity=quantity)
            item._record_event(event)
            return Success(item)
        except Exception as e:
            return Failure(DomainValidationError(str(e), details=get_error_context()))

    def rename(self, new_name: str) -> Result[None, Exception]:
        try:
            if not new_name:
                return Failure(DomainValidationError("new_name is required", details=get_error_context()))
            event = InventoryItemRenamed(item_id=self.id, new_name=new_name)
            self._record_event(event)
            return Success(None)
        except Exception as e:
            return Failure(DomainValidationError(str(e), details=get_error_context()))

    def adjust_quantity(self, adjustment: int) -> Result[None, Exception]:
        try:
            if self.quantity + adjustment < 0:
                return Failure(DomainValidationError("resulting quantity cannot be negative", details=get_error_context()))
            event = InventoryItemAdjusted(item_id=self.id, adjustment=adjustment)
            self._record_event(event)
            return Success(None)
        except Exception as e:
            return Failure(DomainValidationError(str(e), details=get_error_context()))

    def _record_event(self, event: DomainEvent) -> None:
        self._domain_events.append(event)
        self._apply_event(event)

    def _apply_event(self, event: DomainEvent) -> None:
        if isinstance(event, InventoryItemCreated):
            self.name = event.name
            self.quantity = event.quantity
        elif isinstance(event, InventoryItemRenamed):
            self.name = event.new_name
        elif isinstance(event, InventoryItemAdjusted):
            self.quantity += event.adjustment
        else:
            raise DomainValidationError(f"Unhandled event: {event}", details=get_error_context())

    # Canonical serialization already handled by AggregateRoot/Entity base

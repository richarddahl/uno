# SPDX-FileCopyrightText: 2025-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""
Domain model: InventoryLot aggregate and related events.
Represents a physical or logical lot of a particular InventoryItem, with purchase/sale tracking.
Implements Uno canonical serialization, DDD, and event sourcing contracts.
"""

from pydantic import PrivateAttr
from typing import Self
from uno.core.domain.aggregate import AggregateRoot
from uno.core.domain.event import DomainEvent
from uno.core.errors.base import get_error_context
from uno.core.errors.definitions import DomainValidationError
from uno.core.errors.result import Success, Failure


# --- Events ---
class InventoryLotCreated(DomainEvent):
    lot_id: str
    item_id: str
    vendor_id: str | None = None
    quantity: int
    purchase_price: float | None = None  # If purchased
    sale_price: float | None = None  # If sold


class InventoryLotAdjusted(DomainEvent):
    lot_id: str
    adjustment: int
    reason: str | None = None


# --- Aggregate ---
class InventoryLot(AggregateRoot[str]):
    item_id: str
    vendor_id: str | None = None
    quantity: int
    purchase_price: float | None = None
    sale_price: float | None = None
    _domain_events: list[DomainEvent] = PrivateAttr(default_factory=list)

    @classmethod
    def create(
        cls,
        lot_id: str,
        item_id: str,
        quantity: int,
        vendor_id: str | None = None,
        purchase_price: float | None = None,
    ) -> Success[Self, Exception] | Failure[None, Exception]:
        try:
            if not lot_id:
                return Failure(DomainValidationError("lot_id is required", details=get_error_context()))
            if not item_id:
                return Failure(DomainValidationError("item_id is required", details=get_error_context()))
            if quantity < 0:
                return Failure(DomainValidationError("quantity must be non-negative", details=get_error_context()))
            lot = cls(
                id=lot_id,
                item_id=item_id,
                vendor_id=vendor_id,
                quantity=quantity,
                purchase_price=purchase_price,
            )
            event = InventoryLotCreated(
                lot_id=lot_id,
                item_id=item_id,
                vendor_id=vendor_id,
                quantity=quantity,
                purchase_price=purchase_price,
            )
            lot._record_event(event)
            return Success(lot)
        except Exception as e:
            return Failure(DomainValidationError(str(e), details=get_error_context()))

    def adjust_quantity(self, adjustment: int, reason: str | None = None) -> Success[None, Exception] | Failure[None, Exception]:
        try:
            if self.quantity + adjustment < 0:
                return Failure(DomainValidationError("resulting quantity cannot be negative", details=get_error_context()))
            event = InventoryLotAdjusted(
                lot_id=self.id, adjustment=adjustment, reason=reason
            )
            self._record_event(event)
            return Success(None)
        except Exception as e:
            return Failure(DomainValidationError(str(e), details=get_error_context()))

    def _record_event(self, event: DomainEvent) -> None:
        self._domain_events.append(event)
        self._apply_event(event)

    def _apply_event(self, event: DomainEvent) -> None:
        if isinstance(event, InventoryLotCreated):
            self.item_id = event.item_id
            self.vendor_id = event.vendor_id
            self.quantity = event.quantity
            self.purchase_price = event.purchase_price
        elif isinstance(event, InventoryLotAdjusted):
            self.quantity += event.adjustment
        else:
            raise DomainValidationError(f"Unhandled event: {event}", details=get_error_context())

    # Canonical serialization already handled by AggregateRoot/Entity base

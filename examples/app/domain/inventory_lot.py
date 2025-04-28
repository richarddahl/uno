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
from examples.app.domain.value_objects import Grade


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

class InventoryLotsCombined(DomainEvent):
    source_lot_ids: list[str]
    source_grades: list[Grade | None]
    source_vendor_ids: list[str]
    new_lot_id: str
    item_id: str
    combined_quantity: int
    blended_grade: Grade | None
    blended_vendor_ids: list[str]
    # Optionally: merged attributes, notes

class InventoryLotSplit(DomainEvent):
    source_lot_id: str
    new_lot_ids: list[str]
    item_id: str
    split_quantities: list[int]
    # Optionally: attributes, timestamp


# --- Aggregate ---
class InventoryLot(AggregateRoot[str]):
    item_id: str
    vendor_id: str | None = None
    quantity: int
    purchase_price: float | None = None
    sale_price: float | None = None
    grade: Grade | None = None  # e.g., protein %, numeric quality, etc.
    _domain_events: list[DomainEvent] = PrivateAttr(default_factory=list)
    _source_vendor_ids: list[str] = PrivateAttr(default_factory=list)  # Trace all contributing vendors

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
        elif isinstance(event, InventoryLotsCombined):
            # For traceability: update grade and source_vendor_ids
            self.grade = getattr(event, "blended_grade", None)
            self._source_vendor_ids = getattr(event, "blended_vendor_ids", [])
        elif isinstance(event, InventoryLotSplit):
            pass
        else:
            raise DomainValidationError(f"Unhandled event: {event}", details=get_error_context())

    def combine_with(self, other: Self, new_lot_id: str) -> Success[Self, Exception] | Failure[None, Exception]:
        """
        Combine this lot with another lot of the same item, producing a new lot.
        Performs weighted grade averaging and aggregates all vendor IDs for traceability.
        """
        if self.item_id != other.item_id:
            return Failure(DomainValidationError("Cannot combine lots of different items", details=get_error_context()))
        if self.id == other.id:
            return Failure(DomainValidationError("Cannot combine a lot with itself", details=get_error_context()))
        combined_quantity = self.quantity + other.quantity
        # Weighted grade average
        grades, weights = [], []
        for lot in [self, other]:
            if lot.grade is not None:
                grades.append(lot.grade.value)
                weights.append(lot.quantity)
        blended_grade = None
        if grades and weights:
            blended_value = sum(g * w for g, w in zip(grades, weights)) / sum(weights)
            blended_grade = Grade(value=blended_value)
        # Vendor attribution (all unique, non-None)
        vendor_ids = set(filter(None, [self.vendor_id, other.vendor_id]))
        source_vendor_ids = list(vendor_ids)
        new_lot = InventoryLot(
            id=new_lot_id,
            item_id=self.item_id,
            vendor_id=None,
            quantity=combined_quantity,
            purchase_price=None,
            grade=blended_grade,
        )
        new_lot._source_vendor_ids = list(vendor_ids)
        event = InventoryLotsCombined(
            source_lot_ids=[self.id, other.id],
            source_grades=[self.grade, other.grade],
            source_vendor_ids=source_vendor_ids,
            new_lot_id=new_lot_id,
            item_id=self.item_id,
            combined_quantity=combined_quantity,
            blended_grade=blended_grade,
            blended_vendor_ids=list(vendor_ids),
        )
        new_lot._record_event(event)
        return Success(new_lot)

    def split(self, split_quantities: list[int], new_lot_ids: list[str]) -> Success[list[Self], Exception] | Failure[None, Exception]:
        """
        Split this lot into multiple new lots with given quantities and IDs.
        Validates sum and count. Attributes are copied from the source lot.
        """
        if any(q <= 0 for q in split_quantities):
            return Failure(DomainValidationError("All split quantities must be positive", details=get_error_context()))
        if sum(split_quantities) != self.quantity:
            return Failure(DomainValidationError("Split quantities must sum to original quantity", details=get_error_context()))
        if len(split_quantities) != len(new_lot_ids):
            return Failure(DomainValidationError("Must provide a new lot ID for each split", details=get_error_context()))
        new_lots = []
        for qty, lot_id in zip(split_quantities, new_lot_ids):
            new_lot = InventoryLot(
                id=lot_id,
                item_id=self.item_id,
                vendor_id=self.vendor_id,
                quantity=qty,
                purchase_price=self.purchase_price,
            )
            new_lots.append(new_lot)
        event = InventoryLotSplit(
            source_lot_id=self.id,
            new_lot_ids=new_lot_ids,
            item_id=self.item_id,
            split_quantities=split_quantities,
        )
        for lot in new_lots:
            lot._record_event(event)
        return Success(new_lots)

    # Canonical serialization already handled by AggregateRoot/Entity base

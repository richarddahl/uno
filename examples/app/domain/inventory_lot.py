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

from examples.app.domain.value_objects import Grade, Quantity, Count


# --- Events ---
class InventoryLotCreated(DomainEvent):
    lot_id: str
    item_id: str
    vendor_id: str | None = None
    quantity: Quantity
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
    combined_quantity: Quantity
    blended_grade: Grade | None
    blended_vendor_ids: list[str]
    # Optionally: merged attributes, notes


class InventoryLotSplit(DomainEvent):
    source_lot_id: str
    new_lot_ids: list[str]
    item_id: str
    split_quantities: list[Quantity]
    # Optionally: attributes, timestamp


# --- Aggregate ---
class InventoryLot(AggregateRoot[str]):
    item_id: str
    vendor_id: str | None = None
    quantity: Quantity
    purchase_price: float | None = None
    sale_price: float | None = None
    grade: Grade | None = None  # e.g., protein %, numeric quality, etc.
    _domain_events: list[DomainEvent] = PrivateAttr(default_factory=list)
    _source_vendor_ids: list[str] = PrivateAttr(
        default_factory=list
    )  # Trace all contributing vendors

    @classmethod
    def create(
        cls,
        lot_id: str,
        item_id: str,
        quantity: int | Quantity,
        vendor_id: str | None = None,
        purchase_price: float | None = None,
    ) -> Success[Self, Exception] | Failure[None, Exception]:
        try:
            if not lot_id:
                return Failure(
                    DomainValidationError(
                        "lot_id is required", details=get_error_context()
                    )
                )
            if not item_id:
                return Failure(
                    DomainValidationError(
                        "item_id is required", details=get_error_context()
                    )
                )
            # Accept int or Quantity
            if isinstance(quantity, int):
                if quantity < 0:
                    return Failure(
                        DomainValidationError(
                            "quantity must be non-negative", details=get_error_context()
                        )
                    )
                quantity_obj = Quantity.from_count(quantity)
            elif isinstance(quantity, Quantity):
                quantity_obj = quantity
            else:
                return Failure(
                    DomainValidationError(
                        "quantity must be int or Quantity", details=get_error_context()
                    )
                )
            lot = cls(
                id=lot_id,
                item_id=item_id,
                vendor_id=vendor_id,
                quantity=quantity_obj,
                purchase_price=purchase_price,
            )
            # Create a deep copy of the Quantity object for event creation
            # This ensures we're not passing the original instance with enums to the event
            if quantity_obj.type == "count":
                count_value = quantity_obj.value.value
                count_unit = quantity_obj.value.unit
                # Recreate with fresh objects
                event_quantity = Quantity.from_count(count_value)
            else:
                # For other types, use the original quantity (to be implemented as needed)
                event_quantity = quantity_obj
                
            event = InventoryLotCreated(
                lot_id=lot_id,
                item_id=item_id,
                vendor_id=vendor_id,
                quantity=event_quantity,
                purchase_price=purchase_price,
            )
            lot._record_event(event)
            return Success(lot)
        except Exception as e:
            return Failure(DomainValidationError(str(e), details=get_error_context()))

    def adjust_quantity(
        self, adjustment: int, reason: str | None = None
    ) -> Success[Self, Exception] | Failure[None, Exception]:
        try:
            if self.quantity.type != "count":
                return Failure(
                    DomainValidationError(
                        "adjust_quantity only supports count-based lots",
                        details=get_error_context(),
                    )
                )
            new_count = self.quantity.value.value + adjustment
            print(f"[DEBUG] adjust_quantity: new_count={new_count} type={type(new_count)}")
            if new_count < 0:
                return Failure(
                    DomainValidationError(
                        "resulting quantity cannot be negative",
                        details=get_error_context(),
                    )
                )
            event = InventoryLotAdjusted(
                lot_id=self.id, adjustment=adjustment, reason=reason
            )
            self._record_event(event)
            return Success(self)
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
            if self.quantity.type == "count":
                new_count = self.quantity.value.value + event.adjustment
                if new_count < 0:
                    raise DomainValidationError(
                        "resulting quantity cannot be negative",
                        details=get_error_context(),
                    )
                self.quantity = Quantity.from_count(Count.from_each(float(new_count)))
            else:
                raise DomainValidationError(
                    "adjust_quantity only supports count-based lots",
                    details=get_error_context(),
                )
        elif isinstance(event, InventoryLotsCombined):
            # For traceability: update grade and source_vendor_ids
            self.grade = getattr(event, "blended_grade", None)
            self._source_vendor_ids = getattr(event, "blended_vendor_ids", [])
        elif isinstance(event, InventoryLotSplit):
            pass
        else:
            raise DomainValidationError(
                f"Unhandled event: {event}", details=get_error_context()
            )

    def combine_with(
        self, other: Self, new_lot_id: str
    ) -> Success[Self, Exception] | Failure[None, Exception]:
        """
        Combine this lot with another lot of the same item, producing a new lot.
        Performs weighted grade averaging and aggregates all vendor IDs for traceability.
        """
        if self.item_id != other.item_id:
            return Failure(
                DomainValidationError(
                    "Cannot combine lots of different items",
                    details=get_error_context(),
                )
            )
        if self.id == other.id:
            return Failure(
                DomainValidationError(
                    "Cannot combine a lot with itself", details=get_error_context()
                )
            )
        # Only support combining lots of the same quantity type and unit
        if self.quantity.type != other.quantity.type:
            return Failure(
                DomainValidationError(
                    "Cannot combine lots with different quantity types",
                    details=get_error_context(),
                )
            )
        if self.quantity.type == "count":
            combined_quantity = Quantity.from_count(
                self.quantity.value + other.quantity.value
            )
            weights = [self.quantity.value, other.quantity.value]
        else:
            return Failure(
                DomainValidationError(
                    "Only count-based lots are supported", details=get_error_context()
                )
            )

        blended_grade = None
        if self.grade is not None and other.grade is not None:
            total = self.quantity.value.value + other.quantity.value.value
            grade_result = Grade.from_value(
                (
                    self.grade.value * self.quantity.value.value
                    + other.grade.value * other.quantity.value.value
                )
                / total
            )
            if grade_result.is_success:
                blended_grade = grade_result.value
            else:
                return Failure(grade_result.error)
        elif self.grade is not None:
            blended_grade = self.grade
        elif other.grade is not None:
            blended_grade = other.grade

        # Combine vendor IDs
        vendor_ids = set()
        if self.vendor_id:
            vendor_ids.add(self.vendor_id)
        if other.vendor_id:
            vendor_ids.add(other.vendor_id)
        # Only include non-None vendor IDs for event
        source_vendor_ids = [vid for vid in [self.vendor_id, other.vendor_id] if vid is not None]

        new_lot = InventoryLot(
            id=new_lot_id,
            item_id=self.item_id,
            vendor_id=None,
            quantity=combined_quantity,
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

    def split(
        self, split_quantities: list[float], new_lot_ids: list[str]
    ) -> Success[list[Self], Exception] | Failure[None, Exception]:
        if len(split_quantities) != len(new_lot_ids):
            return Failure(
                DomainValidationError(
                    "Number of lot IDs must match each split quantity",
                    details=get_error_context(),
                )
            )
        """
        Split this lot into multiple new lots with given quantities and IDs.
        Validates sum and count. Attributes are copied from the source lot.
        """
        # Only support splitting count-based lots
        if self.quantity.type == "count":
            total = sum(split_quantities)
            if any(q <= 0 for q in split_quantities):
                return Failure(
                    DomainValidationError(
                        "All split quantities must be positive",
                        details=get_error_context(),
                    )
                )
            if total != self.quantity.value.value:
                return Failure(
                    DomainValidationError(
                        "Split quantities must sum to lot quantity",
                        details=get_error_context(),
                    )
                )
            split_qty_objs = [
                Quantity.from_count(Count.from_each(float(q))) for q in split_quantities
            ]
        else:
            return Failure(
                DomainValidationError(
                    "Can only split count-based lots", details=get_error_context()
                )
            )

        new_lots = []
        for qty_obj, lot_id in zip(split_qty_objs, new_lot_ids):
            new_lot = InventoryLot(
                id=lot_id,
                item_id=self.item_id,
                vendor_id=self.vendor_id,
                quantity=qty_obj,
                purchase_price=self.purchase_price,
            )
            new_lots.append(new_lot)

        event = InventoryLotSplit(
            source_lot_id=self.id,
            new_lot_ids=new_lot_ids,
            item_id=self.item_id,
            split_quantities=split_qty_objs,
        )
        for lot in new_lots:
            lot._record_event(event)
        return Success(new_lots)

    # Canonical serialization already handled by AggregateRoot/Entity base

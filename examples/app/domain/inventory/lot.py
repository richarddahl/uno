"""
InventoryLot aggregate and related events for the inventory bounded context.

Represents a physical or logical lot of a particular InventoryItem, with purchase/sale tracking.
Implements Uno canonical serialization, DDD, and event sourcing contracts.
"""

from typing import Self

from pydantic import ConfigDict, PrivateAttr, field_serializer

from examples.app.domain.value_objects import Count, Grade, Quantity
from uno.core.domain.aggregate import AggregateRoot
from uno.core.domain.event import DomainEvent
from uno.core.errors.base import get_error_context
from uno.core.errors.definitions import DomainValidationError
from uno.core.errors.result import Failure, Success


# --- Events ---
class InventoryLotCreated(DomainEvent):
    """
    Event: InventoryLot was created.


    Usage:
        result = InventoryLotCreated.create(
            lot_id="123",
            item_id="A100",
            quantity=Quantity.from_count(Count.from_each(10)),
            vendor_id="VEND01",
            purchase_price=100.0,
            sale_price=None,
        )
        if isinstance(result, Success):
            event = result.value
        else:
            # handle error context
            ...
    """

    model_config = ConfigDict(frozen=True)

    lot_id: str
    item_id: str
    vendor_id: str | None = None
    quantity: Quantity
    purchase_price: float | None = None  # If purchased
    sale_price: float | None = None  # If sold
    version: int = 1

    @field_serializer("quantity")
    def serialize_quantity(self, value, _info):
        return value.model_dump(mode="json")

    @field_serializer("purchase_price")
    def serialize_purchase_price(self, value, _info):
        return str(value) if value else None

    @field_serializer("sale_price")
    def serialize_sale_price(self, value, _info):
        return str(value) if value else None

    @classmethod
    def create(
        cls,
        lot_id: str,
        item_id: str,
        quantity: Quantity,
        vendor_id: str | None = None,
        purchase_price: float | None = None,
        sale_price: float | None = None,
        version: int = 1,
    ) -> Success[Self, Exception] | Failure[Self, Exception]:
        try:
            if not lot_id:
                return Failure(
                    DomainValidationError(
                        "lot_id is required", details={"lot_id": lot_id}
                    )
                )
            if not item_id:
                return Failure(
                    DomainValidationError(
                        "item_id is required", details={"item_id": item_id}
                    )
                )
            if not isinstance(quantity, Quantity):
                return Failure(
                    DomainValidationError(
                        "quantity must be a Quantity object",
                        details={"quantity": quantity},
                    )
                )
            event = cls(
                lot_id=lot_id,
                item_id=item_id,
                quantity=quantity,
                vendor_id=vendor_id,
                purchase_price=purchase_price,
                sale_price=sale_price,
                version=version,
            )
            return Success(event)
        except Exception as exc:
            return Failure(
                DomainValidationError(
                    "Failed to create InventoryLotCreated", details={"error": str(exc)}
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


class InventoryLotAdjusted(DomainEvent):
    """
    Event: InventoryLot was adjusted.

    Usage:
        result = InventoryLotAdjusted.create(
            lot_id="123",
            adjustment=5,
            reason="Inventory recount"
        )
        if isinstance(result, Success):
            event = result.value
        else:
            # handle error context
            ...
    """

    lot_id: str
    adjustment: int
    reason: str | None = None
    version: int = 1

    @classmethod
    def create(
        cls,
        lot_id: str,
        adjustment: int,
        reason: str | None = None,
        version: int = 1,
    ) -> Success[Self, Exception] | Failure[Self, Exception]:
        try:
            if not lot_id:
                return Failure(
                    DomainValidationError(
                        "lot_id is required", details={"lot_id": lot_id}
                    )
                )
            if not isinstance(adjustment, int):
                return Failure(
                    DomainValidationError(
                        "adjustment must be an int", details={"adjustment": adjustment}
                    )
                )
            event = cls(
                lot_id=lot_id,
                adjustment=adjustment,
                reason=reason,
                version=version,
            )
            return Success(event)
        except Exception as exc:
            return Failure(
                DomainValidationError(
                    "Failed to create InventoryLotAdjusted", details={"error": str(exc)}
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


class InventoryLotsCombined(DomainEvent):
    """
    Event: InventoryLots were combined into a new lot.


    Usage:
        result = InventoryLotsCombined.create(
            source_lot_ids=["lot-1", "lot-2"],
            source_grades=[Grade("A"), Grade("B")],
            source_vendor_ids=["VEND01", "VEND02"],
            new_lot_id="lot-3",
            item_id="A100",
            combined_quantity=Quantity.from_count(Count.from_each(20)),
            blended_grade=Grade("A"),
            blended_vendor_ids=["VEND01", "VEND02"],
        )
        if isinstance(result, Success):
            event = result.value
        else:
            # handle error context
            ...
    """

    model_config = ConfigDict(frozen=True)

    source_lot_ids: list[str]
    source_grades: list[Grade | None]
    source_vendor_ids: list[str]
    new_lot_id: str
    item_id: str
    combined_quantity: Quantity
    blended_grade: Grade | None
    blended_vendor_ids: list[str]
    version: int = 1

    @field_serializer("combined_quantity")
    def serialize_combined_quantity(self, value, _info):
        return value.model_dump(mode="json")

    @field_serializer("blended_grade")
    def serialize_blended_grade(self, value, _info):
        return str(value) if value else None

    @classmethod
    def create(
        cls,
        source_lot_ids: list[str],
        source_grades: list[Grade | None],
        source_vendor_ids: list[str],
        new_lot_id: str,
        item_id: str,
        combined_quantity: Quantity,
        blended_grade: Grade | None,
        blended_vendor_ids: list[str],
        version: int = 1,
    ) -> Success[Self, Exception] | Failure[Self, Exception]:
        try:
            if not source_lot_ids or not new_lot_id:
                return Failure(
                    DomainValidationError(
                        "source_lot_ids and new_lot_id are required",
                        details={
                            "source_lot_ids": source_lot_ids,
                            "new_lot_id": new_lot_id,
                        },
                    )
                )
            if not item_id:
                return Failure(
                    DomainValidationError(
                        "item_id is required", details={"item_id": item_id}
                    )
                )
            if not isinstance(combined_quantity, Quantity):
                return Failure(
                    DomainValidationError(
                        "combined_quantity must be a Quantity object",
                        details={"combined_quantity": combined_quantity},
                    )
                )
            event = cls(
                source_lot_ids=source_lot_ids,
                source_grades=source_grades,
                source_vendor_ids=source_vendor_ids,
                new_lot_id=new_lot_id,
                item_id=item_id,
                combined_quantity=combined_quantity,
                blended_grade=blended_grade,
                blended_vendor_ids=blended_vendor_ids,
                version=version,
            )
            return Success(event)
        except Exception as exc:
            return Failure(
                DomainValidationError(
                    "Failed to create InventoryLotsCombined",
                    details={"error": str(exc)},
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


class InventoryLotSplit(DomainEvent):
    """
    Event: InventoryLot was split into multiple new lots.
    Usage:
        result = InventoryLotSplit.create(
            source_lot_id="lot-1",
            new_lot_ids=["lot-2", "lot-3"],
            item_id="item-xyz",
            split_quantities=[Quantity.from_count(Count.from_each(5)), Quantity.from_count(Count.from_each(5))],
        )
        if isinstance(result, Success):
            event = result.value
        else:
            # handle error context
            ...
    """

    model_config = ConfigDict(frozen=True)

    @field_serializer("split_quantities")
    def serialize_split_quantities(self, values, _info):
        return [q.model_dump(mode="json") for q in values]

    source_lot_id: str
    new_lot_ids: list[str]
    item_id: str
    split_quantities: list[Quantity]
    version: int = 1

    @classmethod
    def create(
        cls,
        source_lot_id: str,
        new_lot_ids: list[str],
        item_id: str,
        split_quantities: list[Quantity],
        version: int = 1,
    ) -> Success[Self, Exception] | Failure[Self, Exception]:
        try:
            if not source_lot_id or not new_lot_ids:
                return Failure(
                    DomainValidationError(
                        "source_lot_id and new_lot_ids are required",
                        details={
                            "source_lot_id": source_lot_id,
                            "new_lot_ids": new_lot_ids,
                        },
                    )
                )
            if not item_id:
                return Failure(
                    DomainValidationError(
                        "item_id is required", details={"item_id": item_id}
                    )
                )
            if not split_quantities or len(split_quantities) != len(new_lot_ids):
                return Failure(
                    DomainValidationError(
                        "split_quantities and new_lot_ids must be the same length and non-empty",
                        details={
                            "split_quantities": split_quantities,
                            "new_lot_ids": new_lot_ids,
                        },
                    )
                )
            event = cls(
                source_lot_id=source_lot_id,
                new_lot_ids=new_lot_ids,
                item_id=item_id,
                split_quantities=split_quantities,
                version=version,
            )
            return Success(event)
        except Exception as exc:
            # Always include split_quantities in details for relevant errors
            details = {"error": str(exc)}
            if "split_quantities" not in details:
                details["split_quantities"] = (
                    split_quantities if "split_quantities" in locals() else None
                )
            return Failure(
                DomainValidationError(
                    "Failed to create InventoryLotSplit", details=details
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
class InventoryLot(AggregateRoot[str]):
    item_id: str
    vendor_id: str | None = None
    quantity: Quantity
    purchase_price: float | None = None
    sale_price: float | None = None
    grade: Grade | None = None
    _domain_events: list[DomainEvent] = PrivateAttr(default_factory=list)

    @classmethod
    def create(
        cls,
        lot_id: str,
        item_id: str,
        quantity: int | Quantity,
        vendor_id: str | None = None,
        purchase_price: float | None = None,
    ) -> Success[Self, Exception] | Failure[Self, Exception]:
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
            if isinstance(quantity, int):
                quantity = Quantity.from_count(Count.from_each(float(quantity)))
            if not isinstance(quantity, Quantity):
                return Failure(
                    DomainValidationError(
                        "quantity must be a Quantity object",
                        details=get_error_context(),
                    )
                )
            lot = cls(
                id=lot_id,
                item_id=item_id,
                quantity=quantity,
                vendor_id=vendor_id,
                purchase_price=purchase_price,
            )
            event = InventoryLotCreated(
                lot_id=lot_id,
                item_id=item_id,
                quantity=quantity,
                vendor_id=vendor_id,
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
            if not isinstance(adjustment, int):
                return Failure(
                    DomainValidationError(
                        "adjustment must be an int", details=get_error_context()
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
            self.quantity = event.quantity
            self.vendor_id = event.vendor_id
            self.purchase_price = event.purchase_price
            self.sale_price = event.sale_price
        elif isinstance(event, InventoryLotAdjusted):
            # Update quantity by adjustment
            if hasattr(self, "quantity") and hasattr(self.quantity, "value"):
                self.quantity = Quantity.from_count(
                    Count.from_each(self.quantity.value.value + event.adjustment)
                )
        elif isinstance(event, InventoryLotsCombined):
            self.item_id = event.item_id
            self.quantity = event.combined_quantity
            self.vendor_id = None
            self.grade = event.blended_grade
        elif isinstance(event, InventoryLotSplit):
            # No direct state change on source lot; handled in split logic
            pass
        else:
            raise DomainValidationError(
                f"Unhandled event: {event}", details=get_error_context()
            )

    def combine_with(
        self, other: Self, new_lot_id: str
    ) -> Success[Self, Exception] | Failure[None, Exception]:
        if self is other or self.id == other.id:
            return Failure(
                DomainValidationError(
                    "Cannot combine a lot with itself", details=get_error_context()
                )
            )
        if self.item_id != other.item_id:
            return Failure(
                DomainValidationError(
                    "Cannot combine lots with different items",
                    details=get_error_context(),
                )
            )
        # Sum quantities
        combined_quantity = Quantity.from_count(
            Count.from_each(self.quantity.value.value + other.quantity.value.value)
        )
        # Blend grades if present
        blended_grade = None
        if self.grade and other.grade:
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
        source_vendor_ids = [
            vid for vid in [self.vendor_id, other.vendor_id] if vid is not None
        ]

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

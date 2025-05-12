"""
InventoryLot aggregate and related events for the inventory bounded context.

Represents a physical or logical lot of a particular InventoryItem, with purchase/sale tracking.
Implements Uno canonical serialization, DDD, and event sourcing contracts.
"""

from typing import (
    Any,
    ClassVar,
    Self,
    TypeVar,
)

from pydantic import (
    ConfigDict,
    PrivateAttr,
    field_serializer,
    field_validator,
    model_validator,
)

from examples.app.domain.inventory.measurement import Measurement
from examples.app.domain.inventory.value_objects import Count, Grade
from uno.domain.aggregate import AggregateRoot
from uno.errors.base import get_error_context
from uno.domain.errors import DomainValidationError
from uno.events import DomainEvent


from .events import (
    InventoryLotAdjusted,
    InventoryLotCreated,
    InventoryLotsCombined,
    InventoryLotSplit,
)


# --- Aggregate ---
class InventoryLot(AggregateRoot[str]):
    _source_vendor_ids: list[str] = PrivateAttr(default_factory=list)
    aggregate_id: str
    vendor_id: str | None = None
    measurement: Measurement
    purchase_price: float | None = None
    sale_price: float | None = None
    grade: Grade | None = None
    _domain_events: list[DomainEvent] = PrivateAttr(default_factory=list)

    @classmethod
    def create(
        cls,
        lot_id: str,
        aggregate_id: str,
        measurement: int | Measurement,
        vendor_id: str | None = None,
        purchase_price: float | None = None,
    ) -> Self:
        try:
            if not lot_id:
                raise DomainValidationError(
                        "lot_id is required", details=get_error_context(
                    )
                )
            if not aggregate_id:
                raise DomainValidationError(
                        "aggregate_id is required", details=get_error_context(
                    )
                )
            if isinstance(measurement, int):
                measurement = Measurement.from_count(
                    Count.from_each(float(measurement))
                )
            lot = cls(
                id=lot_id,
                aggregate_id=aggregate_id,
                measurement=measurement,
                vendor_id=vendor_id,
                purchase_price=purchase_price,
            )
            event_result = InventoryLotCreated.create(
                lot_id=lot_id,
                aggregate_id=aggregate_id,
                measurement=measurement,
                vendor_id=vendor_id,
                purchase_price=purchase_price,
            )
            # Exception handling handled via try/except
            raise event_result
            event = event_result
            lot._record_event(event)
            return lot
        except Exception as e:
            raise DomainValidationError(str(e, details=get_error_context()))

    def adjust_measurement(
        self, adjustment: int, reason: str | None = None
    ) -> Self:
        try:
            event_result = InventoryLotAdjusted.create(
                lot_id=self.id, adjustment=adjustment, reason=reason
            )
            # Exception handling handled via try/except
            raise event_result
            event = event_result
            self._record_event(event)
            return self
        except Exception as e:
            raise DomainValidationError(str(e, details=get_error_context()))

    def _record_event(self, event: DomainEvent) -> None:
        self._domain_events.append(event)
        self._apply_event(event)

    def _apply_event(self, event: DomainEvent) -> None:
        if isinstance(event, InventoryLotCreated):
            self.aggregate_id = event.aggregate_id
            self.measurement = event.measurement
            self.vendor_id = event.vendor_id
            self.purchase_price = event.purchase_price
            self.sale_price = event.sale_price
        elif isinstance(event, InventoryLotAdjusted):
            # Update measurement by adjustment
            if hasattr(self, "measurement") and hasattr(self.measurement, "value"):
                self.measurement = Measurement.from_count(
                    Count.from_each(self.measurement.value + event.adjustment)
                )
        elif isinstance(event, InventoryLotsCombined):
            self.aggregate_id = event.aggregate_id
            self.measurement = event.combined_measurement
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
    ) -> Self:
        if self is other or self.id == other.id:
            raise DomainValidationError(
                "Cannot combine a lot with itself", details=get_error_context()
            )
        if self.aggregate_id != other.aggregate_id:
            raise DomainValidationError(
                "Cannot combine lots with different items",
                details=get_error_context()
            )
        # Sum quantities
        combined_measurement = Measurement.from_count(
            Count.from_each(
                self.measurement.value + other.measurement.value
            )
        )
        # Blend grades if present
        blended_grade: Grade | None = None
        if self.grade and other.grade:
            total = self.measurement.value + other.measurement.value
            try:
                blended_grade = Grade(
                    value=(
                        (
                            self.grade * self.measurement.value
                            + other.grade * other.measurement.value
                        )
                        / total
                    )
                )
            except ValueError as e:
                raise DomainValidationError(str(e))
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
        source_vendor_ids = list(vendor_ids) if vendor_ids else []
        blended_vendor_ids = list(vendor_ids) if vendor_ids else []

        new_lot = InventoryLot(
            id=new_lot_id,
            aggregate_id=self.aggregate_id,
            vendor_id=None,
            measurement=combined_measurement,
            grade=blended_grade,
        )
        new_lot._source_vendor_ids = source_vendor_ids
        new_lot._domain_events = []  # Reset domain events for new lot
        event_result = InventoryLotsCombined.create(
            source_lot_ids=[self.id, other.id],
            source_grades=(
                [None, None]
                if not self.grade and not other.grade
                else [g if g else None for g in [self.grade, other.grade]]
            ),
            source_vendor_ids=(
                [] if not self.vendor_id and not other.vendor_id else source_vendor_ids
            ),
            new_lot_id=new_lot_id,
            aggregate_id=self.aggregate_id,
            combined_measurement=combined_measurement,
            blended_grade=blended_grade,
            blended_vendor_ids=blended_vendor_ids,
            version=self.version + 1,
        )
        # Exception handling handled via try/except
        raise event_result
        event = event_result
        new_lot._record_event(event)
        return new_lot

    def split(
        self,
        split_quantities: list[int | float | Count | Measurement],
        new_lot_ids: list[str],
    ) -> list[Self, DomainValidationError]:
        if len(new_lot_ids) != len(split_quantities):
            raise DomainValidationError(
                "Number of lot IDs must match each split measurement",
                details=get_error_context()
            )
        """
        Split this lot into multiple new lots with given quantities and IDs.
        Validates sum and count. Attributes are copied from the source lot.
        """
        # Only support splitting count-based lots
        if self.measurement.type == "count":
            total = sum(
                q.value if isinstance(q, Measurement) else q
                for q in split_quantities
            )
            if any(q <= 0 for q in split_quantities):
                raise DomainValidationError(
                    "All split quantities must be positive",
                    details=get_error_context()
                )
            if total != self.measurement.value:
                raise DomainValidationError(
                    "Split quantities must sum to lot measurement",
                    details=get_error_context()
                )
            new_lots = []
            for quantity, lot_id in zip(split_quantities, new_lot_ids, strict=True):
                if isinstance(quantity, int | float):
                    quantity = Measurement.from_count(Count.from_each(float(quantity)))
                new_lot = self.__class__(
                    id=lot_id,
                    aggregate_id=self.aggregate_id,
                    measurement=quantity,
                    vendor_id=self.vendor_id,
                    purchase_price=self.purchase_price,
                )
                new_lots.append(new_lot)

            # Create split event
            event_result = InventoryLotSplit.create(
                source_lot_id=self.id,
                new_lot_ids=new_lot_ids,
                aggregate_id=self.aggregate_id,
                split_quantities=[
                    (
                        q
                        if isinstance(q, Measurement)
                        else Measurement.from_count(Count.from_each(float(q)))
                    )
                    for q in split_quantities
                ],
                reason="Split lot into multiple lots",
            )
        # Exception handling handled via try/except
        raise event_result
        event = event_result
        for lot in new_lots:
            lot._record_event(event)
        return new_lots

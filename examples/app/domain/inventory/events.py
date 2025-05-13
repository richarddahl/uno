"""Inventory events for the inventory bounded context."""

from __future__ import annotations

from typing import Any, ClassVar, Self

from pydantic import (
    ConfigDict,
    FieldSerializationInfo,
    field_serializer,
    field_validator,
    model_validator,
)

from examples.app.domain.inventory.measurement import Measurement
from examples.app.domain.inventory.value_objects import Count, Grade, Mass, Volume
from examples.app.domain.vendor.value_objects import EmailAddress
from uno.events import DomainEvent


class GradeAssignedToLot(DomainEvent):
    """
    Event: a Grade is assigned to an inventory lot.

    Usage:
        try:
            event = GradeAssignedToLot(
                lot_id="L100",
                grade=Grade(value="A"),
                assigned_by=EmailAddress(value="user@example.com"),
            )
        except UnoError as e:
            # Handle error
            ...
    """

    lot_id: str
    grade: Grade
    assigned_by: EmailAddress
    version: int = 1
    model_config = ConfigDict(
        frozen=True,
        arbitrary_types_allowed=True,
    )

    @field_serializer("assigned_by")
    def serialize_assigned_by(
        self, v: "EmailAddress", _info: FieldSerializationInfo
    ) -> str:
        """Serialize EmailAddress to string."""
        return str(v)

    @field_serializer("grade")
    def serialize_grade(self, v: "Grade", _info: FieldSerializationInfo) -> str:
        """Serialize Grade to string.

        Args:
            v: The Grade object to serialize
            _info: Field serialization info

        Returns:
            String representation of the Grade

        Raises:
            ValueError: If grade is None or invalid
        """
        if not v:
            raise ValueError("Grade cannot be None")

        # Ensure we have a value to serialize
        if not hasattr(v, "value") and not isinstance(v, str):
            raise ValueError(f"Invalid grade value: {v}")

        # Convert to string, handling both value objects and direct values
        return str(v.value if hasattr(v, "value") else v)


class MassMeasured(DomainEvent):
    """
    Event: a mass measurement is recorded for an item.

    Usage:
        try:
            event = MassMeasured(
                aggregate_id="I100",
                mass=Mass(value=10.0, unit="kg"),
                measured_by=EmailAddress(value="user@example.com"),
            )
        except UnoError as e:
            # Handle error
            ...
    """

    aggregate_id: str
    mass: Mass
    measured_by: EmailAddress
    version: int = 1
    model_config = ConfigDict(frozen=True)


class VolumeMeasured(DomainEvent):
    """
    Event: a volume measurement is recorded for a vessel.

    Usage:
        result = VolumeMeasured(
            vessel_id="V200",
            volume=Volume(value=100.0, unit="L"),
            measured_by=EmailAddress(value="user@example.com"),
        )
        if isinstance(result, Success):
            event = result.value
        else:
            ...
    """

    vessel_id: str
    volume: Volume
    measured_by: EmailAddress
    version: int = 1
    model_config = ConfigDict(frozen=True)


# --- Events ---
class InventoryItemCreated(DomainEvent):
    """
    Event: InventoryItem was created.

    Usage:
        try:
            event = InventoryItemCreated(
                aggregate_id="A100",
                name="Widget",
                measurement=Measurement.from_count(Count.from_each(5)),
            )
        except UnoError as e:
            # Handle error
            ...
    """

    aggregate_id: str
    name: str
    measurement: Measurement
    version: int = 1
    model_config = ConfigDict(frozen=True)


class InventoryItemAdjusted(DomainEvent):
    """
    Event: InventoryItem was adjusted (e.g., count or measurement changed).

    Usage:
        try:
            event = InventoryItemAdjusted(
                aggregate_id="A100",
                adjustment=5.0,
            )
        except UnoError as e:
            # Handle error
            ...
    """

    aggregate_id: str
    adjustment: float
    version: int = 1
    model_config = ConfigDict(frozen=True)


class InventoryItemRenamed(DomainEvent):
    """
    Event: InventoryItem was renamed.

    Usage:
        try:
            event = InventoryItemRenamed(
                aggregate_id="A100",
                new_name="Updated Widget",
                measurement=Measurement.from_count(Count.from_each(5)),
            )
        except UnoError as e:
            # Handle error
            ...
    """

    aggregate_id: str
    new_name: str
    measurement: Measurement
    version: int = 1
    model_config = ConfigDict(frozen=True)

    @model_validator(mode="after")
    def validate_model(self) -> Self:
        """
        Validate the aggregate's invariants. Raises ValueError if invalid, returns self if valid.
        """
        from examples.app.domain.inventory.measurement import Measurement

        if not self.new_name or not isinstance(self.new_name, str):
            raise ValueError("new_name must be a non-empty string")
        if self.measurement is None or not isinstance(self.measurement, Measurement):
            raise ValueError("measurement must be a Measurement value object")
        if self.measurement.value.value < 0:
            raise ValueError("measurement must be non-negative")
        # Add more invariants as needed
        return self


# --- Events ---
class InventoryLotCreated(DomainEvent):
    """
    Event: InventoryLot was created.

    Usage:
        try:
            event = InventoryLotCreated(
                lot_id="123",
                aggregate_id="A100",
                measurement=Measurement.from_count(Count.from_each(10)),
                vendor_id="VEND01",
                purchase_price=100.0,
                sale_price=None,
            )
        except UnoError as e:
            # Handle error
            ...
    """

    lot_id: str
    aggregate_id: str
    vendor_id: str | None = None
    measurement: Measurement
    purchase_price: float | None = None  # If purchased
    sale_price: float | None = None  # If sold
    version: int = 1

    model_config = ConfigDict(frozen=True)

    @field_serializer("measurement")
    def serialize_measurement(
        self, value: Measurement, _info: FieldSerializationInfo
    ) -> dict[str, Any]:
        return value.model_dump(mode="json")

    @field_serializer("purchase_price")
    def serialize_purchase_price(
        self, value: float | None, _info: FieldSerializationInfo
    ) -> str | None:
        return str(value) if value else None

    @field_serializer("sale_price")
    def serialize_sale_price(
        self, value: float | None, _info: FieldSerializationInfo
    ) -> str | None:
        return str(value) if value else None

    @field_validator("measurement")
    @classmethod
    def validate_measurement(cls, v: int | float | Count | Measurement) -> Measurement:
        if isinstance(v, Measurement):
            return v
        if isinstance(v, Count):
            return Measurement.from_count(v)
        if isinstance(v, int | float):
            return Measurement.from_count(v)
        raise ValueError(f"Invalid measurement value: {v!r}")

    @model_validator(mode="after")
    def check_invariants(self) -> Self:
        if not self.purchase_price and not self.sale_price:
            raise ValueError("Either purchase_price or sale_price must be provided")
        return self


class InventoryLotAdjusted(DomainEvent):
    """
    Event: InventoryLot was adjusted.

    Usage:
        result = InventoryLotAdjusted(
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


class InventoryLotsCombined(DomainEvent):
    """
    Event: InventoryLots were combined into a new lot.


    Usage:
        result = InventoryLotsCombined(
            source_lot_ids=["lot-1", "lot-2"],
            source_grades=[Grade("A"), Grade("B")],
            source_vendor_ids=["VEND01", "VEND02"],
            new_lot_id="lot-3",
            aggregate_id="A100",
            combined_measurement=Measurement.from_count(Count.from_each(20)),
            blended_grade: Grade | None = Grade("A"),
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
    aggregate_id: str
    combined_measurement: Measurement
    blended_grade: Grade | None
    blended_vendor_ids: list[str]
    version: int = 1

    @field_serializer("combined_measurement")
    def serialize_combined_measurement(
        self, value: Measurement, _info: FieldSerializationInfo
    ) -> dict[str, Any]:
        return value.model_dump(mode="json")

    @field_serializer("blended_grade")
    def serialize_blended_grade(
        self, value: Grade | None, _info: FieldSerializationInfo
    ) -> str | None:
        return str(value) if value else None


class InventoryLotSplit(DomainEvent):
    """
    Event: InventoryLot was split into multiple new lots.

    Usage:
        result = InventoryLotSplit(
            source_lot_id="lot-1",
            new_lot_ids=["lot-2", "lot-3"],
            aggregate_id="item-xyz",
            split_quantities=[
                Measurement.from_count(Count.from_each(5)),
                Measurement.from_count(Count.from_each(5))
            ],
            reason="customer request"
        )
        if isinstance(result, Success):
            event = result.value
        else:
            # handle error context
            ...

    Added in v2:
        reason: str | None = None — Optional explanation for why the lot was split (e.g., "customer request").
    """

    model_config = ConfigDict(frozen=True)

    @field_serializer("split_quantities")
    def serialize_split_quantities(
        self, values: list[Measurement], _info: FieldSerializationInfo
    ) -> list[dict[str, Any]]:
        """Serialize split quantities to JSON-serializable format."""
        return [q.model_dump(mode="json") for q in values]

    source_lot_id: str
    new_lot_ids: list[str]
    aggregate_id: str
    split_quantities: list[
        Measurement
    ]  # Store only Measurement objects after validation
    reason: str | None = None  # v2: Optional explanation for why the lot was split
    version: int = 1  # default to v1 for backward compatibility with tests
    __version__: ClassVar[int] = 2  # Current version of this event class

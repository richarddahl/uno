"""Inventory events for the inventory bounded context."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, Self, TypeVar

from pydantic import (
    ConfigDict,
    FieldSerializationInfo,
    field_serializer,
    field_validator,
    model_validator,
)

from examples.app.domain.inventory.measurement import Measurement
from examples.app.domain.inventory.value_objects import Count, Grade, Mass, Volume
from uno.errors import UnoError
from uno.errors.codes import ErrorCode
from uno.errors.factories import event_error
from uno.events import DomainEvent

# Forward references for type hints
if TYPE_CHECKING:
    from examples.app.domain.vendor.value_objects import EmailAddress
else:
    # Forward reference for runtime
    EmailAddress = "EmailAddress"


class GradeAssignedToLot(DomainEvent):
    """
    Event: a Grade is assigned to an inventory lot.

    Usage:
        try:
            event = GradeAssignedToLot.create(
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

    @classmethod
    def create(
        cls,
        aggregate_id: str,
        lot_id: str,
        grade: Grade,
        assigned_by: EmailAddress,
        version: int = 1,
    ) -> Self:
        """Create a new GradeAssignedToLot event.

        Args:
            lot_id: The ID of the lot being graded
            grade: The grade being assigned
            assigned_by: Email address of the user assigning the grade
            version: Event version (defaults to 1)

        Returns:
            A new GradeAssignedToLot event

        Raises:
            UnoError: If validation fails
        """
        try:
            if not lot_id:
                raise event_error(
                    "lot_id is required",
                    code=ErrorCode.INVALID_INPUT,
                )

            return cls(
                aggregate_id=aggregate_id,
                lot_id=lot_id,
                grade=grade,
                assigned_by=assigned_by,
                version=version,
            )
        except UnoError:
            raise
        except Exception as e:
            raise event_error(
                f"Failed to create GradeAssignedToLot event: {e}",
                code=ErrorCode.INTERNAL_ERROR,
            ) from e

    def upcast(self, target_version: int) -> Self:
        """Upcast the event to a different version.

        Args:
            target_version: The target version to upcast to

        Returns:
            The upcasted event

        Raises:
            UnoError: If upcasting is not supported
        """
        if target_version == self.version:
            return self

        raise event_error(
            f"Upcasting from version {self.version} to {target_version} is not implemented",
            code=ErrorCode.NOT_IMPLEMENTED,
        )


class MassMeasured(DomainEvent):
    """
    Event: a mass measurement is recorded for an item.

    Usage:
        try:
            event = MassMeasured.create(
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

    @classmethod
    def create(
        cls,
        aggregate_id: str,
        mass: Mass,
        measured_by: EmailAddress,
        version: int = 1,
    ) -> Self:
        """Create a new MassMeasured event.

        Args:
            aggregate_id: The ID of the aggregate being measured
            mass: The mass measurement
            measured_by: Email address of the user recording the measurement
            version: Event version (defaults to 1)

        Returns:
            A new MassMeasured event

        Raises:
            UnoError: If validation fails
        """
        try:
            if not aggregate_id:
                raise event_error(
                    "aggregate_id is required",
                    code=ErrorCode.INVALID_INPUT,
                )

            return cls(
                aggregate_id=aggregate_id,
                mass=mass,
                measured_by=measured_by,
                version=version,
            )
        except UnoError:
            raise
        except Exception as e:
            raise event_error(
                f"Failed to create MassMeasured event: {e}",
                code=ErrorCode.INTERNAL_ERROR,
            ) from e

    def upcast(self, target_version: int) -> Self:
        """Upcast the event to a different version.

        Args:
            target_version: The target version to upcast to

        Returns:
            The upcasted event

        Raises:
            UnoError: If upcasting is not supported
        """
        if target_version == self.version:
            return self

        raise event_error(
            f"Upcasting from version {self.version} to {target_version} is not implemented",
            code=ErrorCode.NOT_IMPLEMENTED,
        )


class VolumeMeasured(DomainEvent):
    """
    Event: a volume measurement is recorded for a vessel.

    Usage:
        result = VolumeMeasured.create(
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

    @classmethod
    def create(
        cls,
        vessel_id: str,
        volume: Volume,
        measured_by: EmailAddress,
        version: int = 1,
    ) -> Self:
        try:
            if not vessel_id:
                raise event_error(
                    "vessel_id is required",
                    code=ErrorCode.INVALID_INPUT,
                    details={},
                )
            event = cls(
                vessel_id=vessel_id,
                volume=volume,
                measured_by=measured_by,
                version=version,
            )
            return event
        except Exception as exc:
            raise event_error(
                f"Failed to create VolumeMeasured: {exc}",
                details={"error": str(exc)},
            ) from exc


# --- Events ---
class InventoryItemCreated(DomainEvent):
    """
    Event: InventoryItem was created.

    Usage:
        try:
            event = InventoryItemCreated.create(
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

    @classmethod
    def create(
        cls,
        aggregate_id: str,
        name: str,
        measurement: int | float | Measurement | Count,
        version: int = 1,
    ) -> Self:
        """Create a new InventoryItemCreated event.

        Args:
            aggregate_id: The ID of the inventory item
            name: The name of the inventory item
            measurement: The measurement (can be Measurement, Count, int, or float)
            version: Event version (defaults to 1)

        Returns:
            A new InventoryItemCreated event

        Raises:
            UnoError: If validation fails
        """
        try:
            if not aggregate_id or not isinstance(aggregate_id, str):
                raise event_error(
                    "aggregate_id is required and must be a string",
                    code=ErrorCode.INVALID_INPUT,
                    details={"aggregate_id": aggregate_id},
                )

            if not name or not isinstance(name, str):
                raise event_error(
                    "name is required and must be a string",
                    code=ErrorCode.INVALID_INPUT,
                    details={"name": name},
                )

            # Accept Measurement, Count, int, float
            if isinstance(measurement, Measurement):
                m = measurement
            elif isinstance(measurement, Count | int | float):
                m = Measurement.from_count(measurement)
            else:
                raise event_error(
                    "measurement must be a Measurement, Count, int, or float",
                    code=ErrorCode.INVALID_INPUT,
                    details={"measurement_type": type(measurement).__name__},
                )

            return cls(
                aggregate_id=aggregate_id,
                name=name,
                measurement=m,
                version=version,
            )
        except UnoError:
            raise
        except Exception as e:
            from pydantic import ValidationError

            if isinstance(e, ValidationError):
                # Map pydantic validation errors to domain errors
                details = {}
                for err in e.errors():
                    if err.get("loc"):
                        key = err["loc"][-1]
                        if key == "value":
                            details["measurement"] = err["msg"]
                        else:
                            details[key] = err["msg"]

                details_str = ", ".join(f"{k}: {v}" for k, v in details.items())
                raise event_error(
                    f"Invalid measurement: {details_str or str(e)}",
                    code=ErrorCode.INVALID_INPUT,
                    details=details,
                ) from e

            raise event_error(
                f"Failed to create inventory item: {e}",
                code=ErrorCode.INTERNAL_ERROR,
            ) from e

    def upcast(self, target_version: int) -> Self:
        """Upcast the event to a different version.

        Args:
            target_version: The target version to upcast to

        Returns:
            The upcasted event

        Raises:
            UnoError: If upcasting is not supported
        """
        if target_version == self.version:
            return self

        raise event_error(
            f"Upcasting from version {self.version} to {target_version} is not implemented",
            code=ErrorCode.NOT_IMPLEMENTED,
        )


class InventoryItemAdjusted(DomainEvent):
    """
    Event: InventoryItem was adjusted (e.g., count or measurement changed).

    Usage:
        try:
            event = InventoryItemAdjusted.create(
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

    @classmethod
    def create(
        cls,
        aggregate_id: str,
        adjustment: int | float,
        version: int = 1,
    ) -> Self:
        """Create a new InventoryItemAdjusted event.

        Args:
            aggregate_id: The ID of the inventory item being adjusted
            adjustment: The adjustment amount (positive or negative)
            version: Event version (defaults to 1)

        Returns:
            A new InventoryItemAdjusted event

        Raises:
            UnoError: If validation fails
        """
        try:
            if not aggregate_id:
                raise event_error(
                    "aggregate_id is required",
                    code=ErrorCode.INVALID_INPUT,
                )

            if adjustment == 0:
                raise event_error(
                    "adjustment cannot be zero",
                    code=ErrorCode.INVALID_INPUT,
                )

            return cls(
                aggregate_id=aggregate_id,
                adjustment=adjustment,
                version=version,
            )
        except UnoError:
            raise
        except Exception as exc:
            raise event_error(
                f"Failed to create inventory item adjustment: {exc}",
                code=ErrorCode.INTERNAL_ERROR,
            ) from exc

    # ... (rest of the code remains the same)


class InventoryItemRenamed(DomainEvent):
    # ... (rest of the code remains the same)

    @classmethod
    def create(
        cls,
        aggregate_id: str,
        new_name: str,
        measurement: Measurement,
        version: int = 1,
    ) -> Self:
        """Create a new InventoryItemRenamed event.

        Args:
            aggregate_id: The ID of the inventory item being renamed
            new_name: The new name for the inventory item
            measurement: The current measurement of the inventory item
            version: Event version (defaults to 1)

        Returns:
            A new InventoryItemRenamed event

        Raises:
            UnoError: If validation fails
        """
        try:
            if not aggregate_id or not isinstance(aggregate_id, str):
                raise event_error(
                    "aggregate_id is required and must be a string",
                    code=ErrorCode.INVALID_INPUT,
                    details={"aggregate_id": aggregate_id},
                )

            if not new_name or not isinstance(new_name, str):
                raise event_error(
                    "new_name is required and must be a string",
                    code=ErrorCode.INVALID_INPUT,
                )

            return cls(
                aggregate_id=aggregate_id,
                new_name=new_name,
                measurement=measurement,
                version=version,
            )
        except UnoError:
            raise
        except Exception as e:
            raise event_error(
                f"Failed to rename inventory item: {e}",
                code=ErrorCode.INTERNAL_ERROR,
                details={"new_name": new_name},
            ) from e

    def upcast(self, target_version: int) -> Self:
        """Upcast the event to a different version.

        Args:
            target_version: The target version to upcast to

        Returns:
            The upcasted event

        Raises:
            UnoError: If upcasting is not supported or invalid version
        """
        if target_version == self.version:
            return self
            
        if target_version < 1 or target_version > self.__version__:
            raise event_error(
                f"Cannot upcast to version {target_version}. "
                f"Supported versions: 1-{self.__version__}",
                code=ErrorCode.INVALID_INPUT,
                details={
                    "current_version": self.version,
                    "target_version": target_version,
                    "max_supported_version": self.__version__,
                },
            )
            
        # Create a new instance with the target version
        return self.model_copy(update={"version": target_version})

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
            event = InventoryLotCreated.create(
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

    def upcast(self, target_version: int) -> Self:
        """Upcast the event to a different version.

        Args:
            target_version: The target version to upcast to

        Returns:
            The upcasted event

        Raises:
            UnoError: If upcasting is not supported
        """
        if target_version == self.version:
            return self

        raise event_error(
            f"Upcasting from version {self.version} to {target_version} is not implemented",
            code=ErrorCode.NOT_IMPLEMENTED,
        )

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

    @classmethod
    def create(
        cls,
        lot_id: str,
        aggregate_id: str,
        measurement: int | float | Count | Measurement,
        vendor_id: str | None = None,
        purchase_price: float | None = None,
        sale_price: float | None = None,
        version: int = 1,
    ) -> Self:
        """
        Create a new InventoryLotCreated event.

        Args:
            lot_id: Unique identifier for the lot
            aggregate_id: Aggregate ID for the inventory item
            measurement: Initial measurement (either an int, float, Count value object, or Measurement type)
            vendor_id: Optional vendor ID
            purchase_price: Optional purchase price
            sale_price: Optional sale price
            version: Event version

        Returns:
            A new InventoryLotCreated event

        Raises:
            UnoError: If validation fails
        """
        try:
            if not lot_id:
                raise event_error(
                    "lot_id is required",
                    code=ErrorCode.INVALID_INPUT,
                    details={"lot_id": lot_id},
                )

            if not aggregate_id:
                raise event_error(
                    "aggregate_id is required",
                    code=ErrorCode.INVALID_INPUT,
                    message="aggregate_id is required",
                    details={"aggregate_id": aggregate_id},
                )

            # Handle measurement validation directly
            if isinstance(measurement, Measurement):
                m = measurement
            elif isinstance(measurement, Count | int | float):
                m = Measurement.from_count(measurement)
            else:
                raise event_error(
                    "Invalid argument provided",
                    code=ErrorCode.INVALID_INPUT,
                    message="measurement must be a Measurement, Count, or int/float",
                    details={"measurement_type": type(measurement).__name__},
                )

            # Use model_construct to bypass additional validation that could cause recursion
            event = cls.model_construct(
                lot_id=lot_id,
                aggregate_id=aggregate_id,
                measurement=m,
                vendor_id=vendor_id,
                purchase_price=purchase_price,
                sale_price=sale_price,
                version=version,
            )
            return event

        except UnoError:
            raise

        except Exception as e:
            raise event_error(
                "Internal error encountered",
                code=ErrorCode.INTERNAL_ERROR,
                message=f"Failed to create inventory lot: {e}",
                details={
                    "lot_id": lot_id,
                    "aggregate_id": aggregate_id,
                },
            ) from e

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

    @model_validator(mode="before")
    @classmethod
    def validate_model(cls, data: dict[str, Any] | Self) -> Self:
        """
        Validate and construct a new instance from data.

        Args:
            data: Dictionary or existing instance to validate

        Returns:
            A new instance of this class

        Raises:
            ValueError: If measurement cannot be validated
        """
        if isinstance(data, cls):
            return data

        if isinstance(data, dict):
            measurement = data.get("measurement")

            if measurement is not None:
                if isinstance(measurement, Measurement):
                    data["measurement"] = measurement
                elif isinstance(measurement, Count | int | float):
                    data["measurement"] = Measurement.from_count(measurement)
                elif isinstance(measurement, dict):
                    data["measurement"] = Measurement.model_validate(measurement)
                else:
                    raise ValueError(
                        f"Invalid measurement type: {type(measurement).__name__}"
                    )

            return super().model_validate(data)

        return super().model_validate(data)


T = TypeVar("T", bound="InventoryLotAdjusted")


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

    def upcast(self, target_version: int) -> Self:
        if target_version == self.version:
            return self
        raise event_error(
            UnoError(
                "Upcasting not implemented",
                details={"from": self.version, "to": target_version},
            )
        )

    @classmethod
    def create(
        cls,
        lot_id: str,
        adjustment: int,
        reason: str | None = None,
        version: int = 1,
    ) -> Self:
        try:
            if not lot_id:
                raise event_error("lot_id is required", details={"lot_id": lot_id})
            event = cls(
                lot_id=lot_id,
                adjustment=adjustment,
                reason=reason,
                version=version,
            )
            return event
        except Exception as exc:
            raise event_error(
                "Failed to create InventoryLotAdjusted", details={"error": str(exc)}
            ) from exc


class InventoryLotsCombined(DomainEvent):
    """
    Event: InventoryLots were combined into a new lot.


    Usage:
        result = InventoryLotsCombined.create(
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

    def upcast(self, target_version: int) -> Self:
        if target_version == self.version:
            return self
        raise event_error(
            UnoError(
                "Upcasting not implemented",
                details={"from": self.version, "to": target_version},
            )
        )

    @field_serializer("combined_measurement")
    def serialize_combined_measurement(self, value, _info):
        return value.model_dump(mode="json")

    @field_serializer("blended_grade")
    def serialize_blended_grade(self, value, _info):
        return str(value) if value else None

    @classmethod
    def create(
        cls: type[T],
        source_lot_ids: list[str],
        source_grades: list[Grade | None],
        source_vendor_ids: list[str],
        new_lot_id: str,
        aggregate_id: str,
        combined_measurement: int | float | Count | Measurement,
        blended_grade: Grade | None,
        blended_vendor_ids: list[str],
        version: int = 1,
    ) -> Self:
        try:
            if not (source_lot_ids and new_lot_id and aggregate_id):
                raise event_error(
                    "source_lot_ids, new_lot_id, and aggregate_id are required",
                    details={
                        "source_lot_ids": source_lot_ids,
                        "new_lot_id": new_lot_id,
                        "aggregate_id": aggregate_id,
                    },
                )
            if isinstance(combined_measurement, Measurement):
                m = combined_measurement
            elif isinstance(combined_measurement, Count | float | int):
                m = Measurement.from_count(combined_measurement)
            else:
                raise event_error(
                    "combined_measurement must be a Measurement, Count, int, or float",
                    details={"combined_measurement": combined_measurement},
                )
            event = cls(
                source_lot_ids=source_lot_ids,
                source_grades=source_grades,
                source_vendor_ids=source_vendor_ids,
                new_lot_id=new_lot_id,
                aggregate_id=aggregate_id,
                combined_measurement=m,
                blended_grade=blended_grade,
                blended_vendor_ids=blended_vendor_ids,
                version=version,
            )
            return event
        except Exception as exc:
            raise event_error(
                "Failed to create InventoryLotsCombined",
                details={"error": str(exc)},
            ) from exc

    @classmethod
    def model_validate(cls, data):
        if isinstance(data, cls):
            return data
        if isinstance(data, dict):
            m = data.get("combined_measurement")

            if not isinstance(m, Measurement):
                if isinstance(m, dict):
                    data["combined_measurement"] = Measurement.model_validate(m)
                elif isinstance(m, Count | int | float):
                    data["combined_measurement"] = Measurement.from_count(m)
            return super().model_validate(data)
        return super().model_validate(data)


T = TypeVar("T", bound="InventoryLotSplit")


class InventoryLotSplit(DomainEvent):
    """
    Event: InventoryLot was split into multiple new lots.

    Usage:
        result = InventoryLotSplit.create(
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
    split_quantities: list[Measurement]  # Store only Measurement objects after validation
    reason: str | None = None  # v2: Optional explanation for why the lot was split
    version: int = 1  # default to v1 for backward compatibility with tests
    __version__: ClassVar[int] = 2  # Current version of this event class

    @classmethod
    def create(
        cls,
        source_lot_id: str,
        new_lot_ids: list[str],
        aggregate_id: str,
        split_quantities: list[int | float | Count | Measurement],
        reason: str | None = None,
        version: int = 1,
    ) -> Self:
        """Create a new InventoryLotSplit event.
        
        Args:
            source_lot_id: ID of the original lot being split
            new_lot_ids: List of new lot IDs created from the split
            aggregate_id: ID of the aggregate this event belongs to
            split_quantities: List of quantities for each new lot
            reason: Optional reason for the split
            version: Version of the event schema to use
            
        Returns:
            A new InventoryLotSplit event
            
        Raises:
            UnoError: If validation fails
        """
        try:
            # Input validation
            if not source_lot_id or not isinstance(source_lot_id, str):
                raise event_error(
                    "source_lot_id is required and must be a string",
                    code=ErrorCode.INVALID_INPUT,
                    details={"source_lot_id": source_lot_id},
                )
                
            if not new_lot_ids or not isinstance(new_lot_ids, list) or not all(
                isinstance(id, str) for id in new_lot_ids
            ):
                raise event_error(
                    "new_lot_ids must be a non-empty list of strings",
                    code=ErrorCode.INVALID_INPUT,
                    details={"new_lot_ids": new_lot_ids},
                )
                
            if not aggregate_id or not isinstance(aggregate_id, str):
                raise event_error(
                    "aggregate_id is required and must be a string",
                    code=ErrorCode.INVALID_INPUT,
                    details={"aggregate_id": aggregate_id},
                )
                
            if not split_quantities or not isinstance(split_quantities, list):
                raise event_error(
                    "split_quantities must be a non-empty list",
                    code=ErrorCode.INVALID_INPUT,
                    details={"split_quantities": split_quantities},
                )
                
            # Convert all quantities to Measurement objects
            qty_objs: list[Measurement] = []
            for i, q in enumerate(split_quantities):
                try:
                    if isinstance(q, Measurement):
                        qty_objs.append(q)
                    elif isinstance(q, Count | int | float):
                        qty_objs.append(Measurement.from_count(q))
                    else:
                        raise ValueError(
                            f"Invalid type for split quantity: {type(q).__name__}. "
                            "Must be Measurement, Count, int, or float"
                        )
                except Exception as e:
                    if not isinstance(e, ValueError):
                        e = ValueError(str(e))
                    raise event_error(
                        f"Invalid split_quantity at index {i}: {e}",
                        code=ErrorCode.INVALID_INPUT,
                        details={"index": i, "value": str(q)},
                    ) from e
            
            # Create and return the event
            return cls(
                source_lot_id=source_lot_id,
                new_lot_ids=new_lot_ids,
                aggregate_id=aggregate_id,
                split_quantities=qty_objs,
                reason=reason,
                version=version,
            )
            
        except UnoError:
            raise
        except Exception as exc:
            raise event_error(
                f"Failed to create InventoryLotSplit: {exc}",
                code=ErrorCode.INTERNAL_ERROR,
                details={
                    "source_lot_id": source_lot_id,
                    "new_lot_ids": new_lot_ids,
                    "aggregate_id": aggregate_id,
                },
            ) from exc

    def upcast(self, target_version: int) -> Self:
        """Upcast the event to a different version.
        
        Args:
            target_version: The version to upcast to
            
        Returns:
            A new event instance of the target version
            
        Raises:
            UnoError: If upcasting is not supported to the target version
        """
        if target_version == self.version:
            return self
            
        if target_version < 1 or target_version > self.__version__:
            raise event_error(
                f"Cannot upcast to version {target_version}. "
                f"Supported versions: 1-{self.__version__}",
                code=ErrorCode.INVALID_INPUT,
                details={
                    "current_version": self.version,
                    "target_version": target_version,
                    "max_supported_version": self.__version__,
                },
            )
            
        # Handle v1 -> v2 upcasting
        if self.version == 1 and target_version == 2:
            return self.model_copy(update={
                "version": 2,
                "reason": None,  # Add default reason for v2
            })
            
        # Should never reach here due to version check above
        raise event_error(
            "Unsupported version combination for upcasting",
            code=ErrorCode.INVALID_INPUT,
            details={
                "current_version": self.version,
                "target_version": target_version,
            },
        )

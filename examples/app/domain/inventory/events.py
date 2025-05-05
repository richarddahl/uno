"""
Inventory events for the inventory bounded context.
"""

from typing import (
    Any,
    ClassVar,
    List,
    Optional,
    Self,
    TypeVar,
    Union,
)

from pydantic import ConfigDict, field_serializer, field_validator, model_validator

from examples.app.domain.inventory.measurement import Measurement
from examples.app.domain.inventory.value_objects import (
    Count,
    Grade,
    Mass,
    Volume,
)
from examples.app.domain.vendor.value_objects import EmailAddress
from uno.core.errors import Failure, Result, Success
from uno.core.errors.base import get_error_context
from uno.core.errors.definitions import DomainValidationError
from uno.core.events import DomainEvent
from uno.core.events.base_event import EventUpcasterRegistry
from uno.infrastructure.di.provider import get_service_provider
from uno.infrastructure.logging.logger import LoggerService

from pydantic import ConfigDict, field_serializer, field_validator, model_validator

from examples.app.domain.inventory.measurement import Measurement
from examples.app.domain.inventory.value_objects import (
    Count,
    Grade,
    Mass,
    Volume,
)
from examples.app.domain.vendor.value_objects import EmailAddress
from uno.core.errors import Failure, Result, Success
from uno.core.errors.base import get_error_context
from uno.core.errors.definitions import DomainValidationError
from uno.core.events import DomainEvent

from uno.infrastructure.di.provider import get_service_provider
from uno.infrastructure.logging.logger import LoggerService




class GradeAssignedToLot(DomainEvent):
    """
    Event: a Grade is assigned to an inventory lot.

    Usage:
        result = GradeAssignedToLot.create(
            lot_id="L100",
            grade=Grade(value="A"),
            assigned_by=EmailAddress(value="user@example.com"),
        )
        if isinstance(result, Success):
            event = result.value
        else:
            ...
    """

    lot_id: str
    grade: Grade
    assigned_by: EmailAddress
    version: ClassVar[int] = 1
    model_config = ConfigDict(frozen=True)

    @classmethod
    def create(
        cls,
        lot_id: str,
        grade: Grade,
        assigned_by: EmailAddress,
        version: int = 1,
    ) -> Success[Self, Exception] | Failure[Self, Exception]:
        try:
            if not lot_id:
                return Failure(
                    DomainValidationError(
                        "lot_id is required", details=get_error_context()
                    )
                )
            if not isinstance(grade, Grade):
                return Failure(
                    DomainValidationError(
                        "grade must be a Grade instance", details=get_error_context()
                    )
                )
            if not isinstance(assigned_by, EmailAddress):
                return Failure(
                    DomainValidationError(
                        "assigned_by must be an EmailAddress",
                        details=get_error_context(),
                    )
                )
            event = cls(
                lot_id=lot_id, grade=grade, assigned_by=assigned_by, version=version
            )
            return Success(event)
        except Exception as exc:
            return Failure(
                DomainValidationError(
                    "Failed to create GradeAssignedToLot", details={"error": str(exc)}
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


class MassMeasured(DomainEvent):
    """
    Event: a mass measurement is recorded for an item.

    Usage:
        result = MassMeasured.create(
            aggregate_id="I100",
            mass=Mass(value=10.0, unit="kg"),
            measured_by=EmailAddress(value="user@example.com"),
        )
        if isinstance(result, Success):
            event = result.value
        else:
            ...
    """

    aggregate_id: str
    mass: Mass
    measured_by: EmailAddress
    version: ClassVar[int] = 1
    model_config = ConfigDict(frozen=True)

    @classmethod
    def create(
        cls,
        aggregate_id: str,
        mass: Mass,
        measured_by: EmailAddress,
        version: int = 1,
    ) -> Success[Self, Exception] | Failure[Self, Exception]:
        try:
            if not aggregate_id:
                return Failure(
                    DomainValidationError(
                        "aggregate_id is required", details=get_error_context()
                    )
                )
            if not isinstance(mass, Mass):
                return Failure(
                    DomainValidationError(
                        "mass must be a Mass instance", details=get_error_context()
                    )
                )
            if not isinstance(measured_by, EmailAddress):
                return Failure(
                    DomainValidationError(
                        "measured_by must be an EmailAddress",
                        details=get_error_context(),
                    )
                )
            event = cls(
                aggregate_id=aggregate_id,
                mass=mass,
                measured_by=measured_by,
                version=version,
            )
            return Success(event)
        except Exception as exc:
            return Failure(
                DomainValidationError(
                    "Failed to create MassMeasured", details={"error": str(exc)}
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
    version: ClassVar[int] = 1
    model_config = ConfigDict(frozen=True)

    @classmethod
    def create(
        cls,
        vessel_id: str,
        volume: Volume,
        measured_by: EmailAddress,
        version: int = 1,
    ) -> Success[Self, Exception] | Failure[Self, Exception]:
        try:
            if not vessel_id:
                return Failure(
                    DomainValidationError(
                        "vessel_id is required", details=get_error_context()
                    )
                )
            if not isinstance(volume, Volume):
                return Failure(
                    DomainValidationError(
                        "volume must be a Volume instance", details=get_error_context()
                    )
                )
            if not isinstance(measured_by, EmailAddress):
                return Failure(
                    DomainValidationError(
                        "measured_by must be an EmailAddress",
                        details=get_error_context(),
                    )
                )
            event = cls(
                vessel_id=vessel_id,
                volume=volume,
                measured_by=measured_by,
                version=version,
            )
            return Success(event)
        except Exception as exc:
            return Failure(
                DomainValidationError(
                    "Failed to create VolumeMeasured", details={"error": str(exc)}
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


# --- Events ---
class InventoryItemCreated(DomainEvent):
    """
    Event: InventoryItem was created.

    Handles Measurement validation through model_construct to ensure proper handling of discriminated unions.

    Usage:
        result = InventoryItemCreated.create(
            aggregate_id="A100",
            name="Widget",
            measurement=Measurement.from_count(100),
        )
        if isinstance(result, Success):
            event = result.value
        else:
            # handle error context
            ...
    """

    aggregate_id: str
    name: str
    measurement: Measurement
    version: int = 1

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    @classmethod
    def create(
        cls,
        aggregate_id: str,
        name: str,
        measurement: int | float | Measurement | Count,
        version: int = 1,
    ) -> Success[Self, Exception] | Failure[Self, Exception]:
        """
        Create a new InventoryItemCreated event.

        Args:
            aggregate_id: Unique identifier for the aggregate
            name: Display name for the inventory item
            measurement: Initial measurement (either an int, float, Count value object, or Measurement type)
            version: Event version

        Returns:
            Result containing the event or a validation error
        """
        try:
            # Get logger service correctly
            logger_service = get_service_provider().get_service(LoggerService)()
            logger = logger_service.get_logger("uno.domain.inventory.events")
            logger.debug(
                "[InventoryItemCreated.create] Creating event - aggregate_id=%s name=%s measurement_type=%s",
                aggregate_id,
                name,
                type(measurement).__name__,
            )

            if not aggregate_id or not isinstance(aggregate_id, str):
                logger.error(
                    "[InventoryItemCreated.create] Invalid aggregate_id: %s",
                    aggregate_id,
                )
                return Failure(
                    DomainValidationError(
                        "aggregate_id must be a non-empty string",
                        details={"aggregate_id": aggregate_id},
                    )
                )
            if not name or not isinstance(name, str):
                logger.error("[InventoryItemCreated.create] Invalid name: %s", name)
                return Failure(
                    DomainValidationError(
                        "name must be a non-empty string",
                        details={"name": name},
                    )
                )
            if isinstance(measurement, Measurement):
                q = measurement
            elif isinstance(measurement, (Count, float, int)):
                q = Measurement.from_count(measurement)
            else:
                logger.error(
                    "[InventoryItemCreated.create] Invalid measurement type: %s value: %r",
                    type(measurement).__name__,
                    measurement,
                )
                return Failure(
                    DomainValidationError(
                        "measurement must be a Measurement, Count, int, or float",
                        details={"measurement": measurement},
                    )
                )
            # Use model_construct to ensure proper validation of the measurement field
            event = cls.model_construct(
                aggregate_id=aggregate_id,
                name=name,
                measurement=q,
                version=version,
            )
            logger.info(
                "[InventoryItemCreated.create] Event created - aggregate_id=%s name=%s measurement=%s",
                aggregate_id,
                name,
                q.value.value,
            )
            return Success(event)
        except Exception as e:
            from pydantic import ValidationError

            from uno.core.errors.definitions import DomainValidationError

            if isinstance(e, ValidationError):
                logger.error(
                    "[InventoryItemCreated.create] ValidationError: %s", str(e)
                )
                return Failure(
                    DomainValidationError(
                        str(e),
                        details=get_error_context(),
                    )
                )
            logger.error("[InventoryItemCreated.create] Unexpected error: %s", str(e))
            return Failure(
                DomainValidationError(
                    str(e),
                    details=get_error_context(),
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


class InventoryItemRenamed(DomainEvent):
    """
    Event: InventoryItem was renamed.

    Usage:
        result = InventoryItemRenamed.create(
            aggregate_id="sku-123",
            new_name="Gadget",
        )
        if isinstance(result, Success):
            event = result.value
        else:
            # handle error context
            ...
    """

    aggregate_id: str
    new_name: str
    version: int = 1

    @classmethod
    def create(
        cls,
        aggregate_id: str,
        new_name: str,
        version: int = 1,
    ) -> Success[Self, Exception] | Failure[Self, Exception]:
        try:
            logger_service = get_service_provider().get_service(LoggerService)()
            logger = logger_service.get_logger("uno.domain.inventory.events")
            logger.debug(
                "[InventoryItemRenamed.create] Creating event - aggregate_id=%s new_name=%s",
                aggregate_id,
                new_name,
            )

            if not new_name:
                logger.error(
                    "[InventoryItemRenamed.create] Invalid new_name: %s", new_name
                )
                return Failure(
                    DomainValidationError(
                        "new_name is required", details=get_error_context()
                    )
                )
            event = cls(
                aggregate_id=aggregate_id,
                new_name=new_name,
                version=version,
            )
            logger.info(
                "[InventoryItemRenamed.create] Event created - aggregate_id=%s new_name=%s",
                aggregate_id,
                new_name,
            )
            return Success(event)
        except Exception as exc:
            logger = (
                get_service_provider()
                .get_service(LoggerService)()
                .get_logger("uno.domain.inventory.events")
            )
            logger.error("[InventoryItemRenamed.create] Unexpected error: %s", str(exc))
            return Failure(
                DomainValidationError(
                    "Failed to rename InventoryItem",
                    details={"error": str(exc)},
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


class InventoryItemAdjusted(DomainEvent):
    """
    Event: InventoryItem was adjusted.

    Usage:
        result = InventoryItemAdjusted.create(
            aggregate_id="sku-123",
            adjustment=5,
        )
        if isinstance(result, Success):
            event = result.value
        else:
            # handle error context
            ...
    """

    aggregate_id: str
    adjustment: int | float  # delta, can be negative or positive
    version: int = 1

    @classmethod
    def create(
        cls,
        aggregate_id: str,
        adjustment: int | float,
        version: int = 1,
    ) -> Success[Self, Exception] | Failure[Self, Exception]:
        try:
            logger_service = get_service_provider().get_service(LoggerService)()
            logger = logger_service.get_logger("uno.domain.inventory.events")
            logger.debug(
                "[InventoryItemAdjusted.create] Creating event - aggregate_id=%s adjustment=%f",
                aggregate_id,
                adjustment,
            )

            if not aggregate_id:
                logger.error(
                    "[InventoryItemAdjusted.create] Invalid aggregate_id: %s",
                    aggregate_id,
                )
                return Failure(
                    DomainValidationError(
                        "aggregate_id is required",
                        details={"aggregate_id": aggregate_id},
                    )
                )
            # Accept int, float, or Count
            if isinstance(adjustment, int | float):
                adj_value = float(adjustment)
                event = cls(
                    aggregate_id=aggregate_id,
                    adjustment=adj_value,
                    version=version,
                )
                logger.info(
                    "[InventoryItemAdjusted.create] Event created - aggregate_id=%s adjustment=%f",
                    aggregate_id,
                    adj_value,
                )
                return Success(event)
            else:
                logger.error(
                    "[InventoryItemAdjusted.create] Invalid adjustment type: %s value: %r",
                    type(adjustment).__name__,
                    adjustment,
                )
                return Failure(
                    DomainValidationError(
                        "adjustment must be an int or float",
                        details={"adjustment": adjustment},
                    )
                )
        except Exception as exc:
            logger = (
                get_service_provider()
                .get_service(LoggerService)()
                .get_logger("uno.domain.inventory.events")
            )
            logger.error(
                "[InventoryItemAdjusted.create] Unexpected error: %s", str(exc)
            )
            return Failure(
                DomainValidationError(
                    f"Failed to create InventoryItemAdjusted: {str(exc)}",
                    details={"error": str(exc)},
                )
            )

    def adjust_measurement(self, adjustment: int | float) -> Result[None, Exception]:
        logger_service = get_service_provider().get_service(LoggerService)()
        logger = logger_service.get_logger("uno.domain.inventory.item")
        logger.info(
            "[InventoryItem.adjust_measurement] entry - aggregate_id=%s current_measurement=%f adjustment=%f adjustment_type=%s",
            self.id,
            self.measurement.value.value,
            adjustment,
            type(adjustment).__name__,
        )
        try:
            adj_value = float(adjustment)
            new_value = self.measurement.value.value + adj_value

            if new_value < 0:
                logger.warning(
                    "[InventoryItem.adjust_measurement] negative result - current_measurement=%f adj_value=%f",
                    self.measurement.value.value,
                    adj_value,
                )
                return Failure(
                    DomainValidationError(
                        "resulting measurement cannot be negative",
                        details={
                            "current_measurement": self.measurement.value.value,
                            "adjustment": adj_value,
                        },
                    )
                )

            self.measurement = Measurement.from_value(new_value)
            event = InventoryItemAdjusted.create(self.id, adj_value)
            self._record_event(event)
            logger.info(
                "[InventoryItem.adjust_measurement] success - aggregate_id=%s new_measurement=%f",
                self.id,
                new_value,
            )
            return Success(None)
        except (ValueError, TypeError) as e:
            logger.error(
                "[InventoryItem.adjust_measurement] Failed to adjust measurement - error: %s",
                str(e),
            )
            return Failure(
                DomainValidationError(
                    f"Failed to adjust measurement: {str(e)}",
                    details={"adjustment": adjustment, "error": str(e)},
                )
            )

    def _record_event(self, event: DomainEvent) -> None:
        self._domain_events.append(event)
        self._apply_event(event)

    def _apply_event(self, event: DomainEvent) -> None:
        from examples.app.domain.measurement import Count, Measurement

        if isinstance(event, InventoryItemCreated):
            self.name = event.name
            self.measurement = event.measurement
        elif isinstance(event, InventoryItemRenamed):
            self.name = event.new_name
        elif isinstance(event, InventoryItemAdjusted):
            # event.adjustment is always numeric
            current_value = self.measurement.value.value
            new_value = current_value + event.adjustment
            if new_value < 0:
                raise DomainValidationError(
                    "resulting measurement cannot be negative",
                    details=get_error_context(),
                )
            new_count = Count(value=new_value, unit=self.measurement.value.unit)
            self.measurement = Measurement.from_count(new_count)
        else:
            raise DomainValidationError(
                f"Unhandled event: {event}", details=get_error_context()
            )

    def validate(self) -> Success[None, Exception] | Failure[None, Exception]:
        """
        Validate the aggregate's invariants. Returns Success(None) if valid, Failure(None, Exception) otherwise.
        """
        from uno.core.errors.result import Success, Failure
        from uno.core.errors.definitions import DomainValidationError
        from uno.core.errors.base import get_error_context
        from examples.app.domain.measurement import Measurement

        if not self.name or not isinstance(self.name, str):
            return Failure(
                DomainValidationError(
                    "name must be a non-empty string", details=get_error_context()
                )
            )
        if self.measurement is None or not isinstance(self.measurement, Measurement):
            return Failure(
                DomainValidationError(
                    "measurement must be a Measurement value object",
                    details=get_error_context(),
                )
            )
        if self.measurement.value.value < 0:
            return Failure(
                DomainValidationError(
                    "measurement must be non-negative", details=get_error_context()
                )
            )
        # Add more invariants as needed
        return Success(None)


# --- Events ---


T = TypeVar("T", bound="InventoryLotCreated")

class InventoryLotCreated(DomainEvent):
    """
    Event: InventoryLot was created.


    Usage:
        result = InventoryLotCreated.create(
            lot_id="123",
            aggregate_id="A100",
            measurement=Measurement.from_count(Count.from_each(10)),
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
    version: ClassVar[int] = 1  # Canonical event version field

    lot_id: str
    aggregate_id: str
    vendor_id: str | None = None
    measurement: Measurement
    purchase_price: float | None = None  # If purchased
    sale_price: float | None = None  # If sold
    version: int = 1

    @field_serializer("measurement")
    def serialize_measurement(self, value, _info):
        return value.model_dump(mode="json")

    @field_serializer("purchase_price")
    def serialize_purchase_price(self, value, _info):
        return str(value) if value else None

    @field_serializer("sale_price")
    def serialize_sale_price(self, value, _info):
        return str(value) if value else None

    @classmethod
    def create(
        cls: type[T],
        lot_id: str,
        aggregate_id: str,
        measurement: int | float | Count | Measurement,
        vendor_id: str | None = None,
        purchase_price: float | None = None,
        sale_price: float | None = None,
        version: int = 1,
    ) -> Result[T, DomainValidationError]:
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
            Result containing the event or a validation error
        """
        try:
            if not lot_id:
                return Failure(
                    DomainValidationError(
                        "lot_id is required", details={"lot_id": lot_id}
                    )
                )
            if not aggregate_id:
                return Failure(
                    DomainValidationError(
                        "aggregate_id is required",
                        details={"aggregate_id": aggregate_id},
                    )
                )

            # Handle measurement validation directly
            if isinstance(measurement, Measurement):
                q = measurement
            elif isinstance(measurement, Count | int | float):
                q = Measurement.from_count(measurement)
            else:
                return Failure(
                    DomainValidationError(
                        "measurement must be a Measurement, Count, int, or float",
                        details={"measurement": measurement},
                    )
                )

            # Use model_construct to bypass additional validation that could cause recursion
            event = cls.model_construct(
                lot_id=lot_id,
                aggregate_id=aggregate_id,
                measurement=q,
                vendor_id=vendor_id,
                purchase_price=purchase_price,
                sale_price=sale_price,
                version=version,
            )
            return Success(event)
        except Exception as e:
            return Failure(
                DomainValidationError(
                    f"Failed to create InventoryLotCreated: {str(e)}",
                    details={"error": str(e)},
                )
            )

    @field_validator("measurement")
    @classmethod
    def validate_measurement(cls, v: int | float | Count | Measurement) -> Measurement:
        if isinstance(v, Measurement):
            return v
        if isinstance(v, Count):
            return Measurement.from_count(v)
        if isinstance(v, int | float):
            return Measurement.from_count(v)
        if isinstance(v, dict):
            # Attempt to reconstruct Measurement from dict
            return Measurement.model_validate(v)
        raise ValueError(f"Invalid measurement value: {v!r}")

    @model_validator(mode="before")
    @classmethod
    def model_validate(cls, data: dict | Self) -> Self:
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
                elif isinstance(measurement, Count):
                    data["measurement"] = Measurement.from_count(measurement)
                elif isinstance(measurement, (int, float)):
                    data["measurement"] = Measurement.from_count(measurement)
                elif isinstance(measurement, dict):
                    data["measurement"] = Measurement.model_validate(measurement)
                else:
                    raise ValueError(
                        f"Invalid measurement type: {type(measurement).__name__}"
                    )

            return super().model_validate(data)

        return super().model_validate(data)

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
    reason: Optional[str] = None
    version: int = 1

    @classmethod
    def create(
        cls: type[T],
        lot_id: str,
        adjustment: int,
        reason: Optional[str] = None,
        version: int = 1,
    ) -> Union[Result[T, DomainValidationError], Failure[T, Exception]]:
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
    ) -> Union[Success[T, Exception], Failure[T, Exception]]:
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


T = TypeVar("T", bound="InventoryLotsCombined")


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

    source_lot_ids: List[str]
    source_grades: List[Optional[Grade]]
    source_vendor_ids: List[str]
    new_lot_id: str
    aggregate_id: str
    combined_measurement: Measurement
    blended_grade: Optional[Grade]
    blended_vendor_ids: List[str]
    version: int = 1

    @field_serializer("combined_measurement")
    def serialize_combined_measurement(self, value, _info):
        return value.model_dump(mode="json")

    @field_serializer("blended_grade")
    def serialize_blended_grade(self, value, _info):
        return str(value) if value else None

    @classmethod
    def create(
        cls: type[T],
        source_lot_ids: List[str],
        source_grades: List[Optional[Grade]],
        source_vendor_ids: List[str],
        new_lot_id: str,
        aggregate_id: str,
        combined_measurement: Union[int, float, Count, Measurement],
        blended_grade: Optional[Grade],
        blended_vendor_ids: List[str],
        version: int = 1,
    ) -> Union[Result[T, DomainValidationError], Failure[T, Exception]]:
        try:
            if not source_lot_ids or not new_lot_id or not aggregate_id:
                return Failure(
                    DomainValidationError(
                        "source_lot_ids, new_lot_id, and aggregate_id are required",
                        details={
                            "source_lot_ids": source_lot_ids,
                            "new_lot_id": new_lot_id,
                            "aggregate_id": aggregate_id,
                        },
                    )
                )
            if isinstance(combined_measurement, Measurement):
                q = combined_measurement
            elif isinstance(combined_measurement, Count):
                q = Measurement.from_count(combined_measurement)
            elif isinstance(combined_measurement, (int, float)):
                q = Measurement.from_count(combined_measurement)
            else:
                return Failure(
                    DomainValidationError(
                        "combined_measurement must be a Measurement, Count, int, or float",
                        details={"combined_measurement": combined_measurement},
                    )
                )
            event = cls(
                source_lot_ids=source_lot_ids,
                source_grades=source_grades,
                source_vendor_ids=source_vendor_ids,
                new_lot_id=new_lot_id,
                aggregate_id=aggregate_id,
                combined_measurement=q,
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

    @classmethod
    def model_validate(cls, data):
        if isinstance(data, cls):
            return data
        if isinstance(data, dict):
            q = data.get("combined_measurement")

            if not isinstance(q, Measurement):
                if isinstance(q, dict):
                    data["combined_measurement"] = Measurement.model_validate(q)
                elif isinstance(q, Count):
                    data["combined_measurement"] = Measurement.from_count(q)
                elif isinstance(q, (int, float)):
                    data["combined_measurement"] = Measurement.from_count(q)
            return super().model_validate(data)
        return super().model_validate(data)

    def upcast(
        self, target_version: int
    ) -> Union[Success[T, Exception], Failure[T, Exception]]:
        if target_version == self.version:
            return Success(self)
        return Failure(
            DomainValidationError(
                "Upcasting not implemented",
                details={"from": self.version, "to": target_version},
            )
        )


T = TypeVar("T", bound="InventoryLotSplit")


class InventoryLotSplit(DomainEvent):
    """
    Event: InventoryLot was split into multiple new lots.
    Usage:
        result = InventoryLotSplit.create(
            source_lot_id="lot-1",
            new_lot_ids=["lot-2", "lot-3"],
            aggregate_id="item-xyz",
            split_quantities=[Measurement.from_count(Count.from_each(5)), Measurement.from_count(Count.from_each(5))],
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
    def serialize_split_quantities(self, values, _info):
        return [q.model_dump(mode="json") for q in values]

    source_lot_id: str
    new_lot_ids: List[str]
    aggregate_id: str
    split_quantities: List[Union[int, float, Count, Measurement]]
    reason: Optional[str] = None  # v2: Optional explanation for why the lot was split
    version: int = 1  # default to v1 for backward compatibility with tests
    __version__: ClassVar[int] = 2

    @classmethod
    def create(
        cls: type[T],
        source_lot_id: str,
        new_lot_ids: List[str],
        aggregate_id: str,
        split_quantities: List[Union[int, float, Count, Measurement]],
        reason: Optional[str] = None,
        version: int = 1,
    ) -> Union[Result[T, DomainValidationError], Failure[T, Exception]]:
        try:
            if not source_lot_id or not new_lot_ids or not aggregate_id:
                return Failure(
                    DomainValidationError(
                        "source_lot_id, new_lot_ids, and aggregate_id are required",
                        details={
                            "source_lot_id": source_lot_id,
                            "new_lot_ids": new_lot_ids,
                            "aggregate_id": aggregate_id,
                        },
                    )
                )
            if not isinstance(split_quantities, list):
                return Failure(
                    DomainValidationError(
                        "split_quantities must be a list",
                        details={"split_quantities": split_quantities},
                    )
                )
            qty_objs = []
            for q in split_quantities:
                if isinstance(q, Measurement):
                    qty_objs.append(q)
                elif isinstance(q, Count):
                    qty_objs.append(Measurement.from_count(q))
                elif isinstance(q, int | float):
                    qty_objs.append(Measurement.from_count(q))
                else:
                    return Failure(
                        DomainValidationError(
                            "Each split_measurement must be a Measurement, Count, int, or float",
                            details={"split_measurement": q},
                        )
                    )
            event = cls(
                source_lot_id=source_lot_id,
                new_lot_ids=new_lot_ids,
                aggregate_id=aggregate_id,
                split_quantities=qty_objs,
                reason=reason,
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
        from uno.core.events.base_event import EventUpcasterRegistry

        if target_version == self.version:
            return Success(self)
        if target_version > self.version:
            # Use upcaster registry to migrate
            data = self.to_dict()
            try:
                upcasted = EventUpcasterRegistry.apply(
                    type(self), data, self.version, target_version
                )
                return type(self).from_dict(upcasted)
            except Exception as exc:
                return Failure(
                    DomainValidationError(
                        f"Upcasting failed: {exc}",
                        details={
                            "from": self.version,
                            "to": target_version,
                            "error": str(exc),
                        },
                    )
                )
        return Failure(
            DomainValidationError(
                "Upcasting not implemented",
                details={"from": getattr(self, "version", 1), "to": target_version},
            )
        )


# --- Upcaster registration for InventoryLotSplit (v1 → v2) ---
from uno.core.events.base_event import EventUpcasterRegistry


def _upcast_inventory_lot_split_v1_to_v2(data: dict[str, object]) -> dict[str, object]:
    # v2 adds the 'reason' field (default None)
    data = dict(data)
    if data.get("version", 1) == 1:
        data["reason"] = None
        data["version"] = 2
    return data


EventUpcasterRegistry.register_upcaster(
    event_type=InventoryLotSplit,
    from_version=1,
    upcaster_fn=_upcast_inventory_lot_split_v1_to_v2,
)

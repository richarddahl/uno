"""
Inventory events for the inventory bounded context.
"""

from typing import ClassVar, Self

from pydantic import ConfigDict

from uno.core.domain.event import DomainEvent
from uno.core.errors.base import get_error_context
from uno.core.errors.definitions import DomainValidationError
from uno.core.errors.result import Failure, Success
from examples.app.domain.value_objects import EmailAddress, Grade, Mass, Volume

# Re-export inventory lot events for test and domain imports
from examples.app.domain.inventory.lot import (
    InventoryLotCreated,
    InventoryLotsCombined,
    InventoryLotSplit,
)


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

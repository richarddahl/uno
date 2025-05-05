"""
InventoryItem aggregate and related events for the inventory bounded context.

Implements Uno canonical serialization, DDD, and event sourcing contracts.
"""

from typing import Any, Self

from pydantic import ConfigDict, PrivateAttr, field_validator

from examples.app.domain.inventory.events import (
    InventoryItemAdjusted,
    InventoryItemCreated,
    InventoryItemRenamed,
)
from examples.app.domain.inventory.measurement import Measurement
from examples.app.domain.inventory.value_objects import Count, CountUnit
from uno.core.domain.aggregate import AggregateRoot
from uno.core.errors.base import get_error_context
from uno.core.errors.definitions import DomainValidationError
from uno.core.errors.result import Failure, Result, Success
from uno.core.events import DomainEvent
from uno.infrastructure.di.provider import get_service_provider
from uno.infrastructure.logging.logger import LoggerService


# --- Aggregate ---
class InventoryItem(AggregateRoot[str]):
    name: str
    measurement: Measurement
    _domain_events: list[DomainEvent] = PrivateAttr(default_factory=list)

    @classmethod
    def create(
        cls,
        aggregate_id: str,
        name: str,
        measurement: int | float | Measurement | Count,
    ) -> Result[Self, Exception]:
        try:
            if not aggregate_id:
                return Failure(
                    DomainValidationError(
                        "aggregate_id is required", details=get_error_context()
                    )
                )
            if not name:
                return Failure(
                    DomainValidationError(
                        "name is required", details=get_error_context()
                    )
                )
            # Accept Measurement, Count, int, float
            if isinstance(measurement, Measurement):
                q = measurement
            elif isinstance(measurement, Count):
                # Direct construction to avoid using factory methods that might use logger
                q = Measurement(
                    type="count",
                    value=Count(
                        type="count", value=measurement.value, unit=measurement.unit
                    ),
                )
            elif isinstance(measurement, int | float):
                if measurement < 0:
                    return Failure(
                        DomainValidationError(
                            "measurement must be non-negative",
                            details=get_error_context(),
                        )
                    )
                # Direct construction of Count and Measurement to avoid logger service
                count = Count(
                    type="count", value=float(measurement), unit=CountUnit.EACH
                )
                q = Measurement(type="count", value=count)
            else:
                return Failure(
                    DomainValidationError(
                        "measurement must be a Measurement, Count, int, or float",
                        details=get_error_context(),
                    )
                )
            # Create the aggregate instance directly - modern Python idiom with less complexity
            try:
                # Avoid any usage of factory methods or DI for test compatibility
                item = cls(id=aggregate_id, name=name, measurement=q)

                # Create a dict representing the event data (DDD core pattern)
                event_data = {
                    "aggregate_id": aggregate_id,
                    "name": name,
                    "measurement": q,
                    "version": 1,
                }

                # Use pydantic's direct constructor which has no DI dependencies
                event = InventoryItemCreated(**event_data)

                # Record the event and return success
                item._record_event(event)
                return Success(item)
            except Exception as e:
                return Failure(
                    DomainValidationError(
                        f"Failed to create inventory item: {str(e)}",
                        details=get_error_context(),
                    )
                )
        except Exception as e:
            from pydantic import ValidationError

            if isinstance(e, ValidationError):
                return Failure(
                    DomainValidationError(
                        f"resulting measurement cannot be negative: {e}",
                        details=get_error_context(),
                    )
                )
            return Failure(DomainValidationError(str(e), details=get_error_context()))

    def rename(self, new_name: str) -> Result[None, Exception]:
        try:
            if not new_name:
                return Failure(
                    DomainValidationError(
                        "new_name is required", details=get_error_context()
                    )
                )
            result = InventoryItemRenamed.create(
                aggregate_id=self.id, new_name=new_name, measurement=self.measurement
            )
            if isinstance(result, Failure):
                return result
            event = result.value
            self._record_event(event)
            return Success(None)
        except Exception as e:
            from pydantic import ValidationError

            if isinstance(e, ValidationError):
                return Failure(
                    DomainValidationError(
                        f"resulting measurement cannot be negative: {e}",
                        details=get_error_context(),
                    )
                )
            return Failure(DomainValidationError(str(e), details=get_error_context()))

    def adjust_measurement(self, adjustment: int | float) -> Result[None, Exception]:
        import logging

        logger = logging.getLogger(__name__)
        logger.info(
            {
                "event": "adjust_measurement_entry",
                "aggregate_id": self.id,
                "current_measurement": self.measurement.value.value,
                "adjustment": adjustment,
                "adjustment_type": type(adjustment).__name__,
            }
        )
        try:
            current_value = self.measurement.value.value
            if not isinstance(current_value, float):
                current_value = float(current_value)
            new_value = round(current_value + adjustment, 10)
            if new_value < 0:
                return Failure(
                    DomainValidationError(
                        "resulting measurement cannot be negative",
                        details=get_error_context(),
                    )
                )
            # Do NOT mutate self.measurement here!
            # Only record the event; state will be updated in _apply_event
            event = InventoryItemAdjusted(aggregate_id=self.id, adjustment=adjustment)
            self._record_event(event)
            logger.info(
                {
                    "event": "adjust_measurement_success",
                    "aggregate_id": self.id,
                    "new_measurement": self.measurement.value.value + adjustment,
                }
            )
            return Success(None)
        except Exception as e:
            return Failure(DomainValidationError(str(e), details=get_error_context()))

    def _record_event(self, event: DomainEvent) -> None:
        self._domain_events.append(event)
        self._apply_event(event)

    def _apply_event(self, event: DomainEvent) -> None:
        from examples.app.domain.inventory.measurement import Measurement

        if isinstance(event, InventoryItemCreated):
            self.name = event.name
            self.measurement = (
                event.measurement
                if isinstance(event.measurement, Measurement)
                else Measurement.from_count(event.measurement)
            )
        elif isinstance(event, InventoryItemRenamed):
            self.name = event.new_name
        elif isinstance(event, InventoryItemAdjusted):
            # Diagnostic: print event internals if adjustment is missing
            if not hasattr(event, "adjustment"):
                print(
                    "DEBUG: InventoryItemAdjusted event missing 'adjustment' attribute!"
                )
                print("DEBUG: event type:", type(event))
                print("DEBUG: event __dict__:", getattr(event, "__dict__", str(event)))
                raise DomainValidationError(
                    "InventoryItemAdjusted event missing 'adjustment' attribute",
                    details={
                        "event_type": str(type(event)),
                        "event_dict": getattr(event, "__dict__", str(event)),
                        **get_error_context(),
                    },
                )
            current_value = self.measurement.value.value
            adjustment = event.adjustment
            if not isinstance(current_value, float):
                current_value = float(current_value)
            if not isinstance(adjustment, float):
                adjustment = float(adjustment)
            new_value = round(current_value + adjustment, 10)
            if new_value < 0:
                raise DomainValidationError(
                    "resulting measurement cannot be negative",
                    details=get_error_context(),
                )
            self.measurement = Measurement.from_count(Count.from_each(new_value))
        else:
            raise DomainValidationError(
                f"Unhandled event: {event}", details=get_error_context()
            )

    from pydantic import model_validator

    @model_validator(mode="after")
    def check_invariants(self) -> Self:
        """
        Validate the aggregate's invariants. Raises ValueError if invalid, returns self if valid.
        """
        from examples.app.domain.inventory.measurement import Measurement

        if not self.name or not isinstance(self.name, str):
            raise ValueError("name must be a non-empty string")
        if self.measurement is None or not isinstance(self.measurement, Measurement):
            raise ValueError("measurement must be a Measurement value object")
        if self.measurement.value.value < 0:
            raise ValueError("measurement must be non-negative")
        # Add more invariants as needed
        return self

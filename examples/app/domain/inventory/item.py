"""
InventoryItem aggregate and related events for the inventory bounded context.

Implements Uno canonical serialization, DDD, and event sourcing contracts.

"""

from typing import Self

from pydantic import PrivateAttr, model_validator

from examples.app.domain.inventory.events import (
    InventoryItemAdjusted,
    InventoryItemCreated,
    InventoryItemRenamed,
)
from examples.app.domain.inventory.measurement import Measurement
from examples.app.domain.inventory.value_objects import Count, CountUnit
from uno.domain.aggregate import AggregateRoot
from uno.errors.base import get_error_context
from uno.domain.errors import DomainValidationError
from uno.event_bus import DomainEvent


# --- Aggregate ---
class InventoryItem(AggregateRoot[str]):
    name: str
    measurement: Measurement
    _domain_events: list[DomainEvent] = PrivateAttr(default_factory=list)

    @classmethod
    async def create(
        cls,
        aggregate_id: str,
        name: str,
        measurement: int | float | Measurement | Count,
    ) -> Self:
        """
        Create a new inventory item with initial measurement.

        Args:
            aggregate_id: Unique identifier for the item
            name: Item name
            measurement: Initial measurement (int/float) or Measurement object

        Returns:
            A new InventoryItem

        Raises:
            DomainValidationError: If validation fails
        """
        try:
            if not aggregate_id:
                raise DomainValidationError(
                    "aggregate_id is required", details=get_error_context()
                )
            if not name:
                raise DomainValidationError(
                    "name is required", details=get_error_context()
                )
            # Accept Measurement, Count, int, float
            if isinstance(measurement, Measurement):
                m = measurement
            elif isinstance(measurement, Count):
                # Direct construction to avoid using factory methods that might use logger
                m = Measurement(
                    type="count",
                    value=Count(
                        type="count", value=measurement.value, unit=measurement.unit
                    ),
                )
            elif isinstance(measurement, int | float):
                if measurement < 0:
                    raise DomainValidationError(
                        "measurement must be non-negative",
                        details=get_error_context(),
                    )
                # Direct construction of Count and Measurement to avoid logger service
                count = Count(
                    type="count", value=float(measurement), unit=CountUnit.EACH
                )
                m = Measurement(type="count", value=count)
            # Create the aggregate instance directly - modern Python idiom with less complexity
            try:
                # Avoid any usage of factory methods or DI for test compatibility
                item = cls(id=aggregate_id, name=name, measurement=m)

                # Create the event with named parameters
                event = InventoryItemCreated(
                    aggregate_id=aggregate_id,
                    name=name,
                    measurement=m,
                    version=1,
                )

                # Record the event
                item._record_event(event)
                return item
            except Exception as e:
                raise DomainValidationError(
                    f"Failed to create inventory item: {e}", details=get_error_context()
                ) from e
        except Exception as e:
            from pydantic import ValidationError

            if isinstance(e, ValidationError):
                raise DomainValidationError(
                    f"resulting measurement cannot be negative: {e}",
                    details=get_error_context(),
                ) from e
            if isinstance(e, DomainValidationError):
                raise
            raise DomainValidationError(str(e), details=get_error_context()) from e

    def rename(self, new_name: str) -> None:
        """
        Rename the inventory item.

        Args:
            new_name: The new name for the item

        Raises:
            DomainValidationError: If validation fails
        """
        try:
            if not new_name:
                raise DomainValidationError(
                    "new_name is required", details=get_error_context()
                )
            event = InventoryItemRenamed(
                aggregate_id=self.id,
                new_name=new_name,
                measurement=self.measurement,
            )
            self._record_event(event)
        except Exception as e:
            from pydantic import ValidationError

            if isinstance(e, ValidationError):
                raise DomainValidationError(
                    f"resulting measurement cannot be negative: {e}",
                    details=get_error_context(),
                ) from e
            if isinstance(e, DomainValidationError):
                raise
            raise DomainValidationError(str(e), details=get_error_context()) from e

    def adjust_measurement(self, adjustment: int | float) -> None:
        """
        Adjust the measurement of the inventory item.

        Args:
            adjustment: The amount to adjust by (positive or negative)

        Raises:
            DomainValidationError: If validation fails
        """
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
            new_value = round(current_value + adjustment, 10)
            if new_value < 0:
                raise DomainValidationError(
                    "resulting measurement cannot be negative",
                    details=get_error_context(),
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
        except Exception as e:
            if isinstance(e, DomainValidationError):
                raise
            raise DomainValidationError(str(e), details=get_error_context()) from e

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

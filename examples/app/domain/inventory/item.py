"""
InventoryItem aggregate and related events for the inventory bounded context.

Implements Uno canonical serialization, DDD, and event sourcing contracts.
"""

from pydantic import PrivateAttr
from typing import Self
from uno.core.domain.aggregate import AggregateRoot
from uno.core.domain.event import DomainEvent
from uno.core.errors.result import Result, Success, Failure
from uno.core.errors.base import get_error_context
from uno.core.errors.definitions import DomainValidationError
from examples.app.domain.value_objects import Quantity, Count

# --- Events ---
class InventoryItemCreated(DomainEvent):
    """
    Event: InventoryItem was created.
    model_config = ConfigDict(
        frozen=True,
        json_encoders={
            # Use same logic as value_objects.py
            "Quantity": lambda q: q.model_dump() if hasattr(q, 'model_dump') else str(q),
            "Count": lambda c: c.model_dump() if hasattr(c, 'model_dump') else c.value if hasattr(c, 'value') else c,
            "Mass": lambda m: m.model_dump() if hasattr(m, 'model_dump') else m.value if hasattr(m, 'value') else m,
            "Volume": lambda v: v.model_dump() if hasattr(v, 'model_dump') else v.value if hasattr(v, 'value') else v,
            "Dimension": lambda d: d.model_dump() if hasattr(d, 'model_dump') else d.value if hasattr(d, 'value') else d,
        },
    )

    Usage:
        result = InventoryItemCreated.create(
            item_id="A100",
            name="Widget",
            quantity=Quantity.from_count(100),
        )
        if isinstance(result, Success):
            event = result.value
        else:
            # handle error context
            ...
    """
    item_id: str
    name: str
    quantity: Quantity
    version: int = 1

    @classmethod
    def create(
        cls,
        item_id: str,
        name: str,
        quantity: int | float | Quantity | Count,
        version: int = 1,
    ) -> Success[Self, Exception] | Failure[Self, Exception]:
        from examples.app.domain.value_objects import Quantity, Count
        try:
            if not item_id:
                return Failure(DomainValidationError("item_id is required", details={"item_id": item_id}))
            if not name:
                return Failure(DomainValidationError("name is required", details={"name": name}))
            # Accept Quantity, Count, int, float
            if isinstance(quantity, Quantity):
                q = quantity
            elif isinstance(quantity, Count):
                q = Quantity.from_count(quantity)
            elif isinstance(quantity, (int, float)):
                if quantity < 0:
                    return Failure(DomainValidationError("quantity must be non-negative", details={"quantity": quantity}))
                q = Quantity.from_count(quantity)
            else:
                return Failure(DomainValidationError("quantity must be a Quantity, Count, int, or float", details={"quantity": quantity}))
            event = cls(
                item_id=item_id,
                name=name,
                quantity=q,
                version=version,
            )
            return Success(event)
        except Exception as exc:
            return Failure(DomainValidationError("Failed to create InventoryItemCreated", details={"error": str(exc)}))

    def upcast(self, target_version: int) -> Success[Self, Exception] | Failure[Self, Exception]:
        """
        Upcast event to target version. Stub for future event versioning.
        """
        if target_version == self.version:
            return Success(self)
        return Failure(DomainValidationError("Upcasting not implemented", details={"from": self.version, "to": target_version}))


class InventoryItemRenamed(DomainEvent):
    """
    Event: InventoryItem was renamed.

    Usage:
        result = InventoryItemRenamed.create(
            item_id="sku-123",
            new_name="Gadget",
        )
        if isinstance(result, Success):
            event = result.value
        else:
            # handle error context
            ...
    """
    item_id: str
    new_name: str
    version: int = 1

    @classmethod
    def create(
        cls,
        item_id: str,
        new_name: str,
        version: int = 1,
    ) -> Success[Self, Exception] | Failure[Self, Exception]:
        try:
            if not item_id:
                return Failure(DomainValidationError("item_id is required", details={"item_id": item_id}))
            if not new_name:
                return Failure(DomainValidationError("new_name is required", details={"new_name": new_name}))
            event = cls(
                item_id=item_id,
                new_name=new_name,
                version=version,
            )
            return Success(event)
        except Exception as exc:
            return Failure(DomainValidationError("Failed to create InventoryItemRenamed", details={"error": str(exc)}))

    def upcast(self, target_version: int) -> Success[Self, Exception] | Failure[Self, Exception]:
        """
        Upcast event to target version. Stub for future event versioning.
        """
        if target_version == self.version:
            return Success(self)
        return Failure(DomainValidationError("Upcasting not implemented", details={"from": self.version, "to": target_version}))


class InventoryItemAdjusted(DomainEvent):
    """
    Event: InventoryItem was adjusted.

    Usage:
        result = InventoryItemAdjusted.create(
            item_id="sku-123",
            adjustment=5,
        )
        if isinstance(result, Success):
            event = result.value
        else:
            # handle error context
            ...
    """
    item_id: str
    adjustment: Count  # always a value object
    version: int = 1

    @classmethod
    def create(
        cls,
        item_id: str,
        adjustment: int | float | Count,
        version: int = 1,
    ) -> Success[Self, Exception] | Failure[Self, Exception]:
        from examples.app.domain.value_objects import Count
        try:
            if not item_id:
                return Failure(DomainValidationError("item_id is required", details={"item_id": item_id}))
            # Accept int, float, or Count
            if isinstance(adjustment, Count):
                adj = adjustment
            elif isinstance(adjustment, (int, float)):
                adj = Count.from_each(adjustment)
            else:
                return Failure(DomainValidationError("adjustment must be an int, float, or Count", details={"adjustment": adjustment}))
            event = cls(
                item_id=item_id,
                adjustment=adj,
                version=version,
            )
            return Success(event)
        except Exception as exc:
            return Failure(DomainValidationError("Failed to create InventoryItemAdjusted", details={"error": str(exc)}))

    def upcast(self, target_version: int) -> Success[Self, Exception] | Failure[Self, Exception]:
        """
        Upcast event to target version. Stub for future event versioning.
        """
        if target_version == self.version:
            return Success(self)
        return Failure(DomainValidationError("Upcasting not implemented", details={"from": self.version, "to": target_version}))


# --- Aggregate ---
class InventoryItem(AggregateRoot[str]):
    name: str
    quantity: Quantity
    _domain_events: list[DomainEvent] = PrivateAttr(default_factory=list)

    @classmethod
    def create(cls, item_id: str, name: str, quantity: int | float | Quantity | Count) -> Result[Self, Exception]:
        from examples.app.domain.value_objects import Quantity, Count
        try:
            if not item_id:
                return Failure(DomainValidationError("item_id is required", details=get_error_context()))
            if not name:
                return Failure(DomainValidationError("name is required", details=get_error_context()))
            # Accept Quantity, Count, int, float
            if isinstance(quantity, Quantity):
                q = quantity
            elif isinstance(quantity, Count):
                q = Quantity.from_count(quantity)
            elif isinstance(quantity, (int, float)):
                if quantity < 0:
                    return Failure(DomainValidationError("quantity must be non-negative", details=get_error_context()))
                q = Quantity.from_count(quantity)
            else:
                return Failure(DomainValidationError("quantity must be a Quantity, Count, int, or float", details=get_error_context()))
            item = cls(id=item_id, name=name, quantity=q)
            event = InventoryItemCreated(item_id=item_id, name=name, quantity=q)
            item._record_event(event)
            return Success(item)
        except Exception as e:
            return Failure(DomainValidationError(str(e), details=get_error_context()))

    def rename(self, new_name: str) -> Result[None, Exception]:
        try:
            if not new_name:
                return Failure(DomainValidationError("new_name is required", details=get_error_context()))
            event = InventoryItemRenamed(item_id=self.id, new_name=new_name)
            self._record_event(event)
            return Success(None)
        except Exception as e:
            return Failure(DomainValidationError(str(e), details=get_error_context()))

    def adjust_quantity(self, adjustment: int | float | Count) -> Result[None, Exception]:
        from examples.app.domain.value_objects import Count
        import logging
        logger = logging.getLogger(__name__)
        logger.info({
            'event': 'adjust_quantity_entry',
            'item_id': self.id,
            'current_quantity': self.quantity.value.value,
            'adjustment': adjustment,
            'adjustment_type': type(adjustment).__name__
        })
        try:
            # Always convert adjustment to Count before any arithmetic
            if isinstance(adjustment, Count):
                adj_count = adjustment
                adj_value = adjustment.value
            elif isinstance(adjustment, (int, float)):
                adj_value = float(adjustment)
            else:
                logger.error({'event': 'adjust_quantity_type_error', 'adjustment': adjustment, 'adjustment_type': type(adjustment).__name__})
                return Failure(DomainValidationError("adjustment must be int, float, or Count", details=get_error_context()))
            logger.info({'event': 'adjust_quantity_normalized', 'adj_value': adj_value})
            # Check for negative before constructing the new Count (to control error message)
            if self.quantity.value.value + adj_value < 0:
                logger.warning({'event': 'adjust_quantity_negative_result', 'current_quantity': self.quantity.value.value, 'adj_value': adj_value})
                return Failure(DomainValidationError("resulting quantity cannot be negative", details=get_error_context()))
            # Now it is safe to construct Count
            if not isinstance(adjustment, Count):
                if adj_value < 0:
                    logger.info({'event': 'adjust_quantity_count_from_each', 'passed_value': abs(adj_value)})
                    adj_count = Count.from_each(abs(adj_value))
                    adj_count = Count(value=-adj_count.value, unit=adj_count.unit)
                else:
                    logger.info({'event': 'adjust_quantity_count_from_each', 'passed_value': adj_value})
                    adj_count = Count.from_each(adj_value)
            logger.info({'event': 'adjust_quantity_adj_count_constructed', 'adj_count_value': adj_count.value, 'adj_count_unit': adj_count.unit})
            try:
                _ = self.quantity.value + adj_count  # still check for arithmetic errors
            except Exception as e:
                logger.error({'event': 'adjust_quantity_arithmetic_error', 'error': str(e)})
                return Failure(DomainValidationError(str(e), details=get_error_context()))
            event = InventoryItemAdjusted(item_id=self.id, adjustment=adj_count)
            self._record_event(event)
            logger.info({'event': 'adjust_quantity_success', 'item_id': self.id, 'new_quantity': self.quantity.value.value + adj_count.value})
            return Success(None)
        except Exception as e:
            return Failure(DomainValidationError(str(e), details=get_error_context()))

    def _record_event(self, event: DomainEvent) -> None:
        self._domain_events.append(event)
        self._apply_event(event)

    def _apply_event(self, event: DomainEvent) -> None:
        from examples.app.domain.value_objects import Quantity
        if isinstance(event, InventoryItemCreated):
            self.name = event.name
            self.quantity = event.quantity if isinstance(event.quantity, Quantity) else Quantity.from_count(event.quantity)
        elif isinstance(event, InventoryItemRenamed):
            self.name = event.new_name
        elif isinstance(event, InventoryItemAdjusted):
            if not hasattr(self.quantity, "value"):
                raise DomainValidationError("InventoryItem.quantity is not a value object", details=get_error_context())
            # event.adjustment is always a Count
            self.quantity = Quantity.from_count(self.quantity.value + event.adjustment)
        else:
            raise DomainValidationError(f"Unhandled event: {event}", details=get_error_context())

    # Canonical serialization already handled by AggregateRoot/Entity base

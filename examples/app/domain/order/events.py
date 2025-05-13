# filepath: /Users/richarddahl/Code/uno/examples/app/domain/order/events.py
"""
Order context domain events.
"""

from typing import ClassVar, Literal, Self

from pydantic import ConfigDict

from examples.app.domain.inventory.measurement import Measurement
from examples.app.domain.inventory.value_objects import Count, Money
from examples.app.domain.vendor.value_objects import EmailAddress
from uno.domain.errors import DomainValidationError
from uno.errors.base import get_error_context
from uno.events import DomainEvent


class PaymentReceived(DomainEvent):
    # Inherits FrameworkBaseModel via DomainEvent
    """
    Event: a payment is received for an order.

    Usage:
        try:
            event = PaymentReceived.create(
                order_id="O100",
                amount=Money(amount=100.0, currency="USD"),
                received_from=EmailAddress(value="user@example.com"),
            )
            # use event
        except DomainValidationError as e:
            # handle error
            ...
    """

    order_id: str
    amount: Money
    received_from: EmailAddress
    version: int = 1
    model_config = ConfigDict(frozen=True)

    @classmethod
    def create(
        cls,
        order_id: str,
        amount: Money,
        received_from: EmailAddress,
        version: int = 1,
    ) -> Self:
        """
        Create a new PaymentReceived event with validation.

        Args:
            order_id: The ID of the order
            amount: The payment amount (Money value object)
            received_from: The email address of the payer
            version: The event version

        Returns:
            A new PaymentReceived event

        Raises:
            DomainValidationError: If validation fails
        """
        try:
            if not order_id:
                raise DomainValidationError(
                    "order_id is required", details=get_error_context()
                )
            if not isinstance(amount, Money):
                raise DomainValidationError(
                    "amount must be a Money instance", details=get_error_context()
                )
            if not isinstance(received_from, EmailAddress):
                raise DomainValidationError(
                    "received_from must be an EmailAddress", details=get_error_context()
                )
            event = cls(
                order_id=order_id,
                amount=amount,
                received_from=received_from,
                version=version,
            )
            return event
        except Exception as exc:
            if isinstance(exc, DomainValidationError):
                raise
            raise DomainValidationError(
                "Failed to create PaymentReceived", details={"error": str(exc)}
            ) from exc

    def upcast(self, target_version: int) -> Self:
        """
        Upcast event to target version. Stub for future event versioning.

        Args:
            target_version: The version to upcast to

        Returns:
            The upcasted event

        Raises:
            DomainValidationError: If upcasting is not implemented for the target version
        """
        if target_version == self.version:
            return self
        raise DomainValidationError(
            "Upcasting not implemented",
            details={"from": self.version, "to": target_version},
        )


# --- Events ---
class OrderCreated(DomainEvent):
    """
    Event: Order was created.

    Usage:
        try:
            event = OrderCreated.create(
                order_id="O100",
                aggregate_id="A100",
                lot_id="L100",
                vendor_id="V100",
                measurement=Measurement(10),
                price=Money(25.0),
                order_type="purchase",
            )
            # use event
        except DomainValidationError as e:
            # handle error context
            ...
    """

    order_id: str
    aggregate_id: str
    lot_id: str
    vendor_id: str
    measurement: Measurement
    price: Money
    order_type: Literal["purchase", "sale"]
    version: int = 1
    model_config = ConfigDict(frozen=True)

    @classmethod
    def create(
        cls,
        order_id: str,
        aggregate_id: str,
        lot_id: str,
        vendor_id: str,
        measurement: int | float | Count | Measurement,
        price: Money,
        order_type: Literal["purchase", "sale"],
        version: int = 1,
    ) -> Self:
        """
        Create a new OrderCreated event with validation.

        Args:
            order_id: The ID of the order
            aggregate_id: The aggregate ID
            lot_id: The ID of the inventory lot
            vendor_id: The ID of the vendor
            measurement: The measurement (quantity)
            price: The price
            order_type: Type of order (purchase or sale)
            version: The event version

        Returns:
            A new OrderCreated event

        Raises:
            DomainValidationError: If validation fails
        """
        try:
            if not order_id:
                raise DomainValidationError(
                    "order_id is required", details=get_error_context()
                )
            if not aggregate_id:
                raise DomainValidationError(
                    "aggregate_id is required", details=get_error_context()
                )
            if not lot_id:
                raise DomainValidationError(
                    "lot_id is required", details=get_error_context()
                )
            if not vendor_id:
                raise DomainValidationError(
                    "vendor_id is required", details=get_error_context()
                )
            if isinstance(measurement, Measurement):
                m = measurement
            elif isinstance(measurement, Count):
                m = Measurement.from_count(measurement)
            elif isinstance(measurement, int | float):
                m = Measurement.from_each(measurement)
            else:
                raise DomainValidationError(
                    "measurement must be a Measurement, Count, int, or float",
                    details={"measurement": measurement},
                )
            if order_type not in ("purchase", "sale"):
                raise DomainValidationError(
                    "order_type must be 'purchase' or 'sale'",
                    details=get_error_context(),
                )
            event = cls(
                order_id=order_id,
                aggregate_id=aggregate_id,
                lot_id=lot_id,
                vendor_id=vendor_id,
                measurement=m,
                price=price,
                order_type=order_type,
                version=version,
            )
            return event
        except Exception as exc:
            if isinstance(exc, DomainValidationError):
                raise
            raise DomainValidationError(
                "Failed to create OrderCreated", details={"error": str(exc)}
            ) from exc

    def upcast(self, target_version: int) -> Self:
        """
        Upcast event to target version. Stub for future event versioning.

        Args:
            target_version: The version to upcast to

        Returns:
            The upcasted event

        Raises:
            DomainValidationError: If upcasting is not implemented for the target version
        """
        if target_version == self.version:
            return self
        raise DomainValidationError(
            "Upcasting not implemented",
            details={"from": self.version, "to": target_version},
        )


class OrderFulfilled(DomainEvent):
    """
    Event: Order was fulfilled.

    Usage:
        try:
            event = OrderFulfilled.create(
                order_id="O100",
                fulfilled_measurement=10,
            )
            # use event
        except DomainValidationError as e:
            # handle error context
            ...
    """

    order_id: str
    fulfilled_measurement: int
    version: int = 1
    model_config = ConfigDict(frozen=True)

    @classmethod
    def create(
        cls,
        order_id: str,
        fulfilled_measurement: int,
        version: int = 1,
    ) -> Self:
        """
        Create a new OrderFulfilled event with validation.

        Args:
            order_id: The ID of the order
            fulfilled_measurement: The measurement that was fulfilled
            version: The event version

        Returns:
            A new OrderFulfilled event

        Raises:
            DomainValidationError: If validation fails
        """
        try:
            if not order_id:
                raise DomainValidationError(
                    "order_id is required", details=get_error_context()
                )
            if fulfilled_measurement < 0:
                raise DomainValidationError(
                    "fulfilled_measurement must be non-negative",
                    details=get_error_context(),
                )
            event = cls(
                order_id=order_id,
                fulfilled_measurement=fulfilled_measurement,
                version=version,
            )
            return event
        except Exception as exc:
            if isinstance(exc, DomainValidationError):
                raise
            raise DomainValidationError(
                "Failed to create OrderFulfilled", details={"error": str(exc)}
            ) from exc

    def upcast(self, target_version: int) -> Self:
        """
        Upcast event to target version. Stub for future event versioning.

        Args:
            target_version: The version to upcast to

        Returns:
            The upcasted event

        Raises:
            DomainValidationError: If upcasting is not implemented for the target version
        """
        if target_version == self.version:
            return self
        raise DomainValidationError(
            "Upcasting not implemented",
            details={"from": self.version, "to": target_version},
        )


class OrderCancelled(DomainEvent):
    """Event: Order was cancelled.

    Usage:
        try:
            event = OrderCancelled.create(
                order_id="O100",
                aggregate_id="A100",
                reason="Customer request",
            )
            # use event
        except DomainValidationError as e:
            # handle error context
            ...
    """

    order_id: str
    aggregate_id: str  # Required by DomainEvent
    reason: str | None = None
    version: ClassVar[int] = 1
    model_config = ConfigDict(frozen=True)

    @classmethod
    def create(
        cls,
        order_id: str,
        aggregate_id: str | None = None,
        reason: str | None = None,
        version: int = 1,
    ) -> Self:
        """
        Create a new OrderCancelled event with validation.

        Args:
            order_id: The ID of the order
            aggregate_id: The aggregate ID (defaults to order_id if not provided)
            reason: The reason for cancellation (optional)
            version: The event version

        Returns:
            A new OrderCancelled event
        """
        try:
            if not order_id:
                raise DomainValidationError(
                    "order_id is required", details=get_error_context()
                )
            
            # Use order_id as aggregate_id if not provided
            resolved_aggregate_id = aggregate_id if aggregate_id is not None else order_id

            return cls(
                order_id=order_id,
                aggregate_id=resolved_aggregate_id,
                reason=reason,
                version=version,
            )
        except Exception as exc:
            if isinstance(exc, DomainValidationError):
                raise
            raise DomainValidationError(
                "Failed to create OrderCancelled", details={"error": str(exc)}
            ) from exc

    def upcast(self, target_version: int) -> Self:
        """
        Upcast event to target version. Stub for future event versioning.

        Args:
            target_version: The version to upcast to

        Returns:
            The upcasted event

        Raises:
            DomainValidationError: If upcasting is not implemented for the target version
        """
        if target_version == self.version:
            return self
        raise DomainValidationError(
            "Upcasting not implemented",
            details={"from": self.version, "to": target_version},
        )

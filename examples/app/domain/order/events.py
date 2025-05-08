"""
Order context domain events.
"""

from typing import ClassVar, Literal, Self

from pydantic import ConfigDict

from examples.app.domain.inventory.value_objects import Count, Money
from examples.app.domain.inventory.measurement import Measurement
from examples.app.domain.vendor.value_objects import EmailAddress
from uno.errors.base import get_error_context
from uno.errors.errors import DomainValidationError
from uno.errors.result import Failure, Success
from uno.events import DomainEvent


class PaymentReceived(DomainEvent):
    # Inherits FrameworkBaseModel via DomainEvent
    """
    Event: a payment is received for an order.

    Usage:
        result = PaymentReceived.create(
            order_id="O100",
            amount=Money(amount=100.0, currency="USD"),
            received_from=EmailAddress(value="user@example.com"),
        )
        if isinstance(result, Success):
            event = result.value
        else:
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
    ) -> Success[Self, Exception] | Failure[Self, Exception]:
        try:
            if not order_id:
                return Failure(
                    DomainValidationError(
                        "order_id is required", details=get_error_context()
                    )
                )
            if not isinstance(amount, Money):
                return Failure(
                    DomainValidationError(
                        "amount must be a Money instance", details=get_error_context()
                    )
                )
            if not isinstance(received_from, EmailAddress):
                return Failure(
                    DomainValidationError(
                        "received_from must be an EmailAddress",
                        details=get_error_context(),
                    )
                )
            event = cls(
                order_id=order_id,
                amount=amount,
                received_from=received_from,
                version=version,
            )
            return Success(event)
        except Exception as exc:
            return Failure(
                DomainValidationError(
                    "Failed to create PaymentReceived", details={"error": str(exc)}
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
class OrderCreated(DomainEvent):
    """
    Event: Order was created.

    Usage:
        result = OrderCreated.create(
            order_id="O100",
            aggregate_id="A100",
            lot_id="L100",
            vendor_id="V100",
            measurement=Measurement(10),
            price=Money(25.0),
            order_type="purchase",
        )
        if isinstance(result, Success):
            event = result.value
        else:
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
    ) -> Success[Self, Exception] | Failure[Self, Exception]:
        from examples.app.domain.measurement import Count, Measurement

        try:
            if not order_id:
                return Failure(
                    DomainValidationError(
                        "order_id is required", details=get_error_context()
                    )
                )
            if not aggregate_id:
                return Failure(
                    DomainValidationError(
                        "aggregate_id is required", details=get_error_context()
                    )
                )
            if not lot_id:
                return Failure(
                    DomainValidationError(
                        "lot_id is required", details=get_error_context()
                    )
                )
            if not vendor_id:
                return Failure(
                    DomainValidationError(
                        "vendor_id is required", details=get_error_context()
                    )
                )
            if isinstance(measurement, Measurement):
                m = measurement
            elif isinstance(measurement, Count):
                m = Measurement.from_count(measurement)
            elif isinstance(measurement, int | float):
                m = Measurement.from_each(measurement)
            else:
                return Failure(
                    DomainValidationError(
                        "measurement must be a Measurement, Count, int, or float",
                        details={"measurement": measurement},
                    )
                )
            if order_type not in ("purchase", "sale"):
                return Failure(
                    DomainValidationError(
                        "order_type must be 'purchase' or 'sale'",
                        details=get_error_context(),
                    )
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
            return Success(event)
        except Exception as exc:
            return Failure(
                DomainValidationError(
                    "Failed to create OrderCreated", details={"error": str(exc)}
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


class OrderFulfilled(DomainEvent):
    """
    Event: Order was fulfilled.

    Usage:
        result = OrderFulfilled.create(
            order_id="O100",
            fulfilled_measurement=10,
        )
        if isinstance(result, Success):
            event = result.value
        else:
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
    ) -> Success[Self, Exception] | Failure[Self, Exception]:
        try:
            if not order_id:
                return Failure(
                    DomainValidationError(
                        "order_id is required", details=get_error_context()
                    )
                )
            if fulfilled_measurement < 0:
                return Failure(
                    DomainValidationError(
                        "fulfilled_measurement must be non-negative",
                        details=get_error_context(),
                    )
                )
            event = cls(
                order_id=order_id,
                fulfilled_measurement=fulfilled_measurement,
                version=version,
            )
            return Success(event)
        except Exception as exc:
            return Failure(
                DomainValidationError(
                    "Failed to create OrderFulfilled", details={"error": str(exc)}
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


class OrderCancelled(DomainEvent):
    """
    Event: Order was cancelled.

    Usage:
        result = OrderCancelled.create(
            order_id="O100",
            reason="Customer request",
        )
        if isinstance(result, Success):
            event = result.value
        else:
            # handle error context
            ...
    """

    order_id: str
    reason: str | None = None
    version: int = 1
    model_config = ConfigDict(frozen=True)

    @classmethod
    def create(
        cls,
        order_id: str,
        reason: str | None = None,
        version: int = 1,
    ) -> Success[Self, Exception] | Failure[Self, Exception]:
        try:
            if not order_id:
                return Failure(
                    DomainValidationError(
                        "order_id is required", details=get_error_context()
                    )
                )
            event = cls(order_id=order_id, reason=reason, version=version)
            return Success(event)
        except Exception as exc:
            return Failure(
                DomainValidationError(
                    "Failed to create OrderCancelled", details={"error": str(exc)}
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

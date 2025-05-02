"""
Order context domain events.
"""

from typing import ClassVar, Literal, Self

from uno.core.base_model import FrameworkBaseModel

from examples.app.domain.value_objects import Count, EmailAddress, Money, Quantity
from uno.core.domain.event import DomainEvent
from uno.core.errors.base import get_error_context
from uno.core.errors.definitions import DomainValidationError
from uno.core.errors.result import Failure, Success
from pydantic import ConfigDict

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
    version: ClassVar[int] = 1
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
            item_id="A100",
            lot_id="L100",
            vendor_id="V100",
            quantity=Quantity(10),
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
    item_id: str
    lot_id: str
    vendor_id: str
    quantity: Quantity
    price: Money
    order_type: Literal["purchase", "sale"]
    version: int = 1
    model_config = ConfigDict(frozen=True)

    @classmethod
    def create(
        cls,
        order_id: str,
        item_id: str,
        lot_id: str,
        vendor_id: str,
        quantity: Quantity | Count | float | int,
        price: Money,
        order_type: Literal["purchase", "sale"],
        version: int = 1,
    ) -> Success[Self, Exception] | Failure[Self, Exception]:
        from examples.app.domain.value_objects import Quantity, Count

        try:
            if not order_id:
                return Failure(
                    DomainValidationError(
                        "order_id is required", details=get_error_context()
                    )
                )
            if not item_id:
                return Failure(
                    DomainValidationError(
                        "item_id is required", details=get_error_context()
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
            # Accept Quantity, Count, int, float for quantity
            if isinstance(quantity, Quantity):
                q = quantity
            elif isinstance(quantity, Count):
                q = Quantity.from_count(quantity)
            elif isinstance(quantity, (int, float)):
                if quantity < 0:
                    return Failure(
                        DomainValidationError(
                            "quantity must be non-negative",
                            details=get_error_context(),
                        )
                    )
                q = Quantity.from_count(quantity)
            else:
                return Failure(
                    DomainValidationError(
                        "quantity must be a Quantity, Count, int, or float",
                        details=get_error_context(),
                    )
                )
            if not isinstance(price, Money):
                return Failure(
                    DomainValidationError(
                        "price must be a Money value object",
                        details=get_error_context(),
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
                item_id=item_id,
                lot_id=lot_id,
                vendor_id=vendor_id,
                quantity=q,
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
            fulfilled_quantity=10,
        )
        if isinstance(result, Success):
            event = result.value
        else:
            # handle error context
            ...
    """

    order_id: str
    fulfilled_quantity: int
    version: int = 1
    model_config = ConfigDict(frozen=True)

    @classmethod
    def create(
        cls,
        order_id: str,
        fulfilled_quantity: int,
        version: int = 1,
    ) -> Success[Self, Exception] | Failure[Self, Exception]:
        try:
            if not order_id:
                return Failure(
                    DomainValidationError(
                        "order_id is required", details=get_error_context()
                    )
                )
            if fulfilled_quantity < 0:
                return Failure(
                    DomainValidationError(
                        "fulfilled_quantity must be non-negative",
                        details=get_error_context(),
                    )
                )
            event = cls(
                order_id=order_id,
                fulfilled_quantity=fulfilled_quantity,
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

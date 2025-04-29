"""
Example domain events using Uno value objects.
"""

from uno.core.domain.event import DomainEvent

from .value_objects import EmailAddress, Grade, Mass, Money, Volume


class GradeAssignedToLot(DomainEvent):
    """Event: a Grade is assigned to an inventory lot."""

    lot_id: str
    grade: Grade
    assigned_by: EmailAddress


class MassMeasured(DomainEvent):
    """Event: a mass measurement is recorded for an item."""

    item_id: str
    mass: Mass
    measured_by: EmailAddress


class VolumeMeasured(DomainEvent):
    """Event: a volume measurement is recorded for a vessel."""

    vessel_id: str
    volume: Volume
    measured_by: EmailAddress


class PaymentReceived(DomainEvent):
    """Event: a payment is received for an order."""

    order_id: str
    amount: Money
    received_from: EmailAddress


class VendorEmailUpdated(DomainEvent):
    """Event: a vendor's email address is updated."""

    vendor_id: str
    old_email: EmailAddress
    new_email: EmailAddress

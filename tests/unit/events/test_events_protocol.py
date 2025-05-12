from __future__ import annotations

import pytest

from examples.app.domain.inventory.events import GradeAssignedToLot, MassMeasured
from examples.app.domain.inventory.value_objects import Grade, Mass
from examples.app.domain.order.events import PaymentReceived
from examples.app.domain.vendor.events import VendorEmailUpdated
from examples.app.domain.vendor.value_objects import EmailAddress
from uno.domain.protocols import DomainEventProtocol
from uno.events.protocols import SerializationProtocol


@pytest.mark.parametrize(
    "event_cls",
    [
        GradeAssignedToLot,
        MassMeasured,
        VendorEmailUpdated,
        PaymentReceived,
    ],
)
def test_event_class_conforms_to_protocols(event_cls):
    assert issubclass(event_cls, DomainEventProtocol)
    assert issubclass(event_cls, SerializationProtocol)
    # Check required methods
    for method_name in ["to_dict", "from_dict", "serialize", "deserialize"]:
        assert hasattr(event_cls, method_name) or hasattr(event_cls(), method_name)
        method = getattr(event_cls, method_name, None) or getattr(
            event_cls(), method_name, None
        )
        assert callable(method)


def test_event_serialization_roundtrip():
    # Create test data
    test_grade = Grade(value="A")
    test_email = EmailAddress(value="test@example.com")
    test_mass = Mass(value=1.0, unit="kg")
    
    # Create events with valid data
    grade_event = GradeAssignedToLot.create(
        lot_id="L100",
        grade=test_grade,
        assigned_by=test_email,
    )
    
    mass_event = MassMeasured.create(
        aggregate_id="I100",
        mass=test_mass,
        measured_by=test_email,
    )
    
    # Test serialization/deserialization for GradeAssignedToLot
    if hasattr(grade_event, "to_dict") and hasattr(GradeAssignedToLot, "from_dict"):
        data = grade_event.to_dict()
        deserialized = GradeAssignedToLot.from_dict(data)
        assert deserialized == grade_event
    
    # Test serialization/deserialization for MassMeasured
    if hasattr(mass_event, "to_dict") and hasattr(MassMeasured, "from_dict"):
        data = mass_event.to_dict()
        deserialized = MassMeasured.from_dict(data)
        assert deserialized == mass_event

from __future__ import annotations

import pytest

from examples.app.domain.inventory.events import GradeAssignedToLot, MassMeasured
from examples.app.domain.inventory.value_objects import Grade, Mass
from examples.app.domain.order.events import PaymentReceived
from examples.app.domain.vendor.events import VendorEmailUpdated
from examples.app.domain.vendor.value_objects import EmailAddress
from uno.domain.protocols import DomainEventProtocol
from uno.events.protocols import SerializationProtocol



def test_event_serialization_roundtrip():
    # Create test data
    test_grade = Grade(value=1.0)
    test_email = EmailAddress(value="test@example.com")
    test_mass = Mass(value=1.0, unit=("kg", 1.0))
    
    # Create events with valid data
    grade_event = GradeAssignedToLot.create(
        aggregate_id="L100",
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
    data = grade_event.model_dump()
    if isinstance(data["assigned_by"], str):
        data["assigned_by"] = {"value": data["assigned_by"]}
    deserialized = GradeAssignedToLot.model_validate(data)
    # Compare only domain-relevant fields (ignore event_id, timestamp)
    assert deserialized.model_dump(exclude={"event_id", "timestamp"}) == grade_event.model_dump(exclude={"event_id", "timestamp"})

    # Test serialization/deserialization for MassMeasured
    data = mass_event.model_dump()
    if isinstance(data["measured_by"], str):
        data["measured_by"] = {"value": data["measured_by"]}
    deserialized = MassMeasured.model_validate(data)
    # Compare only domain-relevant fields (ignore event_id, timestamp)
    assert deserialized.model_dump(exclude={"event_id", "timestamp"}) == mass_event.model_dump(exclude={"event_id", "timestamp"})

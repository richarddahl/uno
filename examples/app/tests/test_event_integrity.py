"""
Tests for event stream integrity and tamper detection in Uno event-sourced example domain.
"""
import pytest
from examples.app.persistence.repository import InMemoryInventoryItemRepository
from examples.app.domain.inventory_item import InventoryItem
from uno.core.events.base_event import verify_event_stream_integrity


def test_event_stream_integrity_and_tamper_detection():
    repo = InMemoryInventoryItemRepository()
    # Create and persist events
    item = InventoryItem.create("item-1", "Corn", 100)
    repo.save(item)
    events = repo._events[item.id]
    # Verify initial hash chain is valid
    assert verify_event_stream_integrity(events)

    # Tamper with the hash chain by modifying previous_hash of the second event
    if len(events) > 1:
        tampered_events = list(events)
        tampered_event_dict = tampered_events[1].to_dict()
        tampered_event_dict["previous_hash"] = "fake_hash"  # Malicious tampering
        tampered_events[1] = type(events[1]).from_dict(tampered_event_dict)
        try:
            verify_event_stream_integrity(tampered_events)
            assert False, "Tampering should break the hash chain"
        except ValueError:
            pass  # Expected

"""
Test that uno.core.events exposes the correct public API via __all__.
"""
from uno.core import events

def test_events_public_api():
    expected = {
        "DomainEvent",
        "EventPriority",
        "EventBusProtocol",
        "EventPublisherProtocol",
        "EventBus",
        "EventPublisher",
        "EventStore",
        "InMemoryEventStore",
        "get_event_bus",
        "get_event_store",
        "get_event_publisher",
        "subscribe",
        "register_event_handler",
        "EventHandler",
    }
    actual = set(events.__all__)
    assert expected == actual
    # Also check that all names are importable
    for name in expected:
        assert hasattr(events, name), f"events module missing: {name}"

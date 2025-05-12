import inspect
from uno.events.protocols import (
    EventHandlerProtocol,
    EventRegistryProtocol,
    EventProcessorProtocol,
    SerializationProtocol,
)
from uno.events.registry import EventHandlerRegistry
from uno.events.processor import EventProcessor
from uno.events.serialization import SerializableEvent


def test_event_handler_registry_conforms_to_protocol():
    assert issubclass(EventHandlerRegistry, EventRegistryProtocol)
    required_methods = [
        method_name
        for method_name, method in inspect.getmembers(EventRegistryProtocol)
        if inspect.isfunction(method) and not method_name.startswith("_")
    ]
    for method_name in required_methods:
        assert hasattr(EventHandlerRegistry, method_name)
        assert callable(getattr(EventHandlerRegistry, method_name))


def test_event_processor_conforms_to_protocol():
    assert issubclass(EventProcessor, EventProcessorProtocol)
    required_methods = [
        method_name
        for method_name, method in inspect.getmembers(EventProcessorProtocol)
        if inspect.isfunction(method) and not method_name.startswith("_")
    ]
    for method_name in required_methods:
        assert hasattr(EventProcessor, method_name)
        assert callable(getattr(EventProcessor, method_name))


def test_serializable_event_conforms_to_protocol():
    # Define a minimal concrete subclass for protocol conformance check
    class DummyEvent(SerializableEvent):
        event_type = "dummy"
        version: int = 1

    dummy = DummyEvent()

    assert hasattr(dummy, "event_type")
    assert isinstance(dummy.event_type, str)
    assert hasattr(dummy, "version")
    assert isinstance(dummy.version, int)
    assert hasattr(dummy, "serialize")
    assert callable(dummy.serialize)
    assert hasattr(DummyEvent, "deserialize")
    assert callable(getattr(DummyEvent, "deserialize"))


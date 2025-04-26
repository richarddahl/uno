"""
DI/configurable factories for Uno event sourcing infrastructure.
Provides injectable, testable, and configurable access to event bus, publisher, and store.
"""
from typing import Any, Callable, cast
from uno.core.events.bus import EventBus, EventBusProtocol
from uno.core.events.publisher import EventPublisher, EventPublisherProtocol
from uno.core.events.event_store import EventStore, InMemoryEventStore
from uno.core.logging.logger import LoggerService, LoggingConfig

# Module-level singletons (can be replaced/configured via DI)
_event_bus: EventBusProtocol | None = None
_event_publisher: EventPublisherProtocol | None = None
_event_store: EventStore | None = None
_logger: LoggerService = LoggerService(LoggingConfig())

def get_event_bus() -> EventBusProtocol:
    """Get the current event bus instance (configurable, DI-friendly)."""
    global _event_bus
    if _event_bus is not None:
        return _event_bus
    # Default to in-memory event bus
    _event_bus = EventBus()
    _logger.debug("Using default in-memory EventBus")
    return _event_bus

def set_event_bus(bus: EventBusProtocol) -> None:
    """Override the event bus instance (for DI/testing)."""
    global _event_bus
    _event_bus = bus
    _logger.info(f"EventBus overridden: {bus}")

def get_event_publisher() -> EventPublisherProtocol:
    """Get the current event publisher instance (configurable, DI-friendly)."""
    global _event_publisher
    if _event_publisher is not None:
        return _event_publisher
    # Default: publisher wraps current event bus
    _event_publisher = EventPublisher(get_event_bus(), logger=_logger)
    _logger.debug("Using default EventPublisher")
    return _event_publisher

def set_event_publisher(publisher: EventPublisherProtocol) -> None:
    """Override the event publisher instance (for DI/testing)."""
    global _event_publisher
    _event_publisher = publisher
    _logger.info(f"EventPublisher overridden: {publisher}")

def get_event_store() -> EventStore:
    """Get the current event store instance (configurable, DI-friendly)."""
    global _event_store
    if _event_store is not None:
        return _event_store
    # Default: in-memory event store
    _event_store = InMemoryEventStore(logger_factory=lambda _: _logger)
    _logger.debug("Using default InMemoryEventStore")
    return _event_store

def set_event_store(store: EventStore) -> None:
    """Override the event store instance (for DI/testing)."""
    global _event_store
    _event_store = store
    _logger.info(f"EventStore overridden: {store}")

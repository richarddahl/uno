"""
DI/configurable factories for Uno event sourcing infrastructure.
Provides injectable, testable, and configurable access to event bus, publisher, and store.
"""

from uno.events.bus import EventBus, EventBusProtocol
from uno.events.event_store import EventStore, InMemoryEventStore
from uno.events.publisher import EventPublisher, EventPublisherProtocol
from uno.infrastructure.logging.logger import LoggerService, LoggingConfig

# Module-level singletons (can be replaced/configured via DI)
# Module-level singletons for event infrastructure (set via DI/testing setters)
_event_bus: EventBusProtocol | None = None
_event_publisher: EventPublisherProtocol | None = None
_event_store: EventStore[object] | None = (
    None  # Use object for generality; specialize if needed
)
_logger: LoggerService = LoggerService(LoggingConfig())


def get_event_bus() -> EventBusProtocol:
    """
    Retrieve the current event bus instance for Uno's event sourcing infrastructure.

    Returns:
        EventBusProtocol: The configured event bus instance. Defaults to an in-memory EventBus if not set.

    Notes:
        - This function is DI-friendly and supports test overrides.
        - Uses a module-level singleton pattern.
    """
    if _event_bus is not None:
        return _event_bus
    # Default to in-memory event bus
    # Note: This assignment is safe as module-level singleton
    _set_event_bus(EventBus[object](logger=_logger))
    _logger.debug("Using default in-memory EventBus")
    return _event_bus


def set_event_bus(bus: EventBusProtocol) -> None:
    """
    Override the event bus instance for Uno's event sourcing infrastructure.

    Args:
        bus (EventBusProtocol): The event bus instance to use (for DI/testing).
    """
    _set_event_bus(bus)
    _logger.info(f"EventBus overridden: {bus}")


def _set_event_bus(bus: EventBusProtocol) -> None:
    # Internal setter for module-level singleton (for DI/testing)
    global _event_bus
    _event_bus = bus


def get_event_publisher() -> EventPublisherProtocol:
    """
    Retrieve the current event publisher instance for Uno's event sourcing infrastructure.

    Returns:
        EventPublisherProtocol: The configured event publisher instance. Defaults to an EventPublisher wrapping the current event bus if not set.

    Notes:
        - This function is DI-friendly and supports test overrides.
        - Uses a module-level singleton pattern.
    """
    if _event_publisher is not None:
        return _event_publisher
    # Default: publisher wraps current event bus
    # Note: This assignment is safe as module-level singleton
    _set_event_publisher(EventPublisher(get_event_bus(), logger=_logger))
    _logger.debug("Using default EventPublisher")
    return _event_publisher


def set_event_publisher(publisher: EventPublisherProtocol) -> None:
    """
    Override the event publisher instance for Uno's event sourcing infrastructure.

    Args:
        publisher (EventPublisherProtocol): The event publisher instance to use (for DI/testing).
    """
    _set_event_publisher(publisher)
    _logger.info(f"EventPublisher overridden: {publisher}")


def _set_event_publisher(publisher: EventPublisherProtocol) -> None:
    # Internal setter for module-level singleton (for DI/testing)
    global _event_publisher
    _event_publisher = publisher


def get_event_store() -> EventStore[object]:
    """
    Retrieve the current event store instance for Uno's event sourcing infrastructure.

    Returns:
        EventStore[object]: The configured event store instance. Defaults to an in-memory event store if not set.

    Notes:
        - This function is DI-friendly and supports test overrides.
        - Uses a module-level singleton pattern.
    """
    if _event_store is not None:
        return _event_store
    # Default: in-memory event store
    _set_event_store(InMemoryEventStore[object](logger=_logger))
    _logger.debug("Using default InMemoryEventStore")
    return _event_store


def set_event_store(store: EventStore[object]) -> None:
    """
    Override the event store instance for Uno's event sourcing infrastructure.

    Args:
        store (EventStore[object]): The event store instance to use (for DI/testing).
    """
    _set_event_store(store)
    _logger.info(f"EventStore overridden: {store}")


def _set_event_store(store: EventStore[object]) -> None:
    # Internal setter for module-level singleton (for DI/testing)
    global _event_store
    _event_store = store

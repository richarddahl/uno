# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
DI/configurable factories for Uno event sourcing infrastructure.
Provides injectable, testable, and configurable access to event bus, publisher, and store.
"""

from uno.events.protocols import (
    EventBusProtocol,
    EventPublisherProtocol,
)
from uno.persistence.event_sourcing.protocols import EventStoreProtocol
from uno.events.implementations.bus import InMemoryEventBus
from uno.events.implementations.store import InMemoryEventStore
from uno.logging.logger import LoggerProtocol

# Module-level singletons (can be replaced/configured via DI)
# Module-level singletons for event infrastructure (set via DI/testing setters)
_event_bus: EventBusProtocol | None = None
_event_publisher: EventPublisherProtocol | None = None
_event_store: EventStoreProtocol | None = None
_logger: LoggerProtocol | None = None  # Inject via DI or set externally


def get_event_bus() -> EventBusProtocol:
    """
    Retrieve the current event bus instance for Uno's event sourcing infrastructure.

    Returns:
        EventBusProtocol: The configured event bus instance. Defaults to an in-memory
                         implementation if not set.

    Notes:
        - This function is DI-friendly and supports test overrides.
        - Uses a module-level singleton pattern.
    """
    global _event_bus
    if _event_bus is not None:
        return _event_bus
    # Default to in-memory event bus
    _event_bus = InMemoryEventBus()
    _logger.debug("Using default InMemoryEventBus")
    return _event_bus


def set_event_bus(bus: EventBusProtocol) -> None:
    """
    Override the event bus instance for Uno's event sourcing infrastructure.

    Args:
        bus (EventBusProtocol): The event bus instance to use (for DI/testing).
    """
    global _event_bus
    _event_bus = bus
    _logger.info(f"EventBus overridden: {bus}")


def get_event_publisher() -> EventPublisherProtocol:
    """
    Retrieve the current event publisher instance for Uno's event sourcing infrastructure.

    Returns:
        EventPublisherProtocol: The configured event publisher instance. Defaults to
                               a publisher using the default event bus if not set.

    Notes:
        - This function is DI-friendly and supports test overrides.
        - Uses a module-level singleton pattern.
    """
    global _event_publisher
    if _event_publisher is not None:
        return _event_publisher

    # Use or create an event bus
    event_bus = get_event_bus()

    # For now, we'll just use the event bus as the publisher
    # A dedicated publisher will be added in a future PR
    _event_publisher = event_bus
    _logger.debug("Using default event publisher implementation")
    return _event_publisher


def set_event_publisher(publisher: EventPublisherProtocol) -> None:
    """
    Override the event publisher instance for Uno's event sourcing infrastructure.

    Args:
        publisher (EventPublisherProtocol): The event publisher instance to use (for DI/testing).
    """
    global _event_publisher
    _event_publisher = publisher
    _logger.info(f"EventPublisher overridden: {publisher}")


def get_event_store() -> EventStoreProtocol:
    """
    Retrieve the current event store instance for Uno's event sourcing infrastructure.

    Returns:
        EventStoreProtocol: The configured event store instance. Defaults to an in-memory
                           event store if not set.

    Notes:
        - This function is DI-friendly and supports test overrides.
        - Uses a module-level singleton pattern.
    """
    global _event_store
    if _event_store is not None:
        return _event_store
    # Default: in-memory event store
    _event_store = InMemoryEventStore()
    _logger.debug("Using default InMemoryEventStore")
    return _event_store


def set_event_store(store: EventStoreProtocol) -> None:
    """
    Override the event store instance for Uno's event sourcing infrastructure.

    Args:
        store (EventStoreProtocol): The event store instance to use (for DI/testing).
    """
    global _event_store
    _event_store = store
    _logger.info(f"EventStore overridden: {store}")

# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
DI/configurable factories for Uno event sourcing infrastructure.
Provides injectable, testable, and configurable access to event bus, publisher, and store.
"""

from typing import Any

from uno.injection.container import Container
from uno.injection.provider import Provider, AsyncProvider
from uno.events.protocols import (
    EventBusProtocol,
    EventPublisherProtocol,
)
from uno.logging.protocols import LoggerProtocol
from uno.persistance.event_sourcing.protocols import EventStoreProtocol
from uno.persistance.event_sourcing.implementations.memory.bus import InMemoryEventBus
from uno.persistance.event_sourcing.implementations.memory.event_store import (
    InMemoryEventStore,
)

# Global DI container reference
_di_container: Container | None = None


def set_container(container: Container) -> None:
    """
    Set the DI container used for resolving dependencies.

    Args:
        container: The DI container to use
    """
    global _di_container
    _di_container = container


def get_container() -> Container:
    """
    Get the current DI container, creating a default one if none exists.

    Returns:
        The current DI container
    """
    global _di_container
    if _di_container is None:
        from uno.injection.container import Container

        _di_container = Container()
        # Register default providers
        register_default_providers(_di_container)
    return _di_container


def register_default_providers(container: Container) -> None:
    """
    Register default providers for event infrastructure components.

    Args:
        container: The DI container to register providers with
    """
    # Register logger provider
    container.register(
        LoggerProtocol, AsyncProvider(async_factory=async_create_default_logger)
    )

    # Register event bus provider
    container.register(
        EventBusProtocol,
        AsyncProvider(async_factory=async_create_default_event_bus, singleton=True),
    )

    # Register event publisher provider
    container.register(
        EventPublisherProtocol,
        AsyncProvider(
            async_factory=async_create_default_event_publisher, singleton=True
        ),
    )

    # Register event store provider
    container.register(
        EventStoreProtocol,
        AsyncProvider(async_factory=async_create_default_event_store, singleton=True),
    )


async def async_create_default_logger() -> LoggerProtocol:
    """
    Create a default logger instance.

    Returns:
        A default logger implementation
    """
    from uno.logging.factory import create_logger

    return create_logger("uno.events")


async def async_create_default_event_bus(container: Container) -> EventBusProtocol:
    """
    Create a default event bus instance.

    Args:
        container: The DI container for resolving dependencies

    Returns:
        A default event bus implementation
    """
    logger = await container.resolve(LoggerProtocol)
    await logger.debug("Creating default InMemoryEventBus")
    return InMemoryEventBus()


async def async_create_default_event_publisher(
    container: Container,
) -> EventPublisherProtocol:
    """
    Create a default event publisher instance.

    Args:
        container: The DI container for resolving dependencies

    Returns:
        A default event publisher implementation
    """
    logger = await container.resolve(LoggerProtocol)
    # For now, we'll just use the event bus as the publisher
    event_bus = await container.resolve(EventBusProtocol)
    await logger.debug("Using EventBus as default event publisher")
    return event_bus


async def async_create_default_event_store(container: Container) -> EventStoreProtocol:
    """
    Create a default event store instance.

    Args:
        container: The DI container for resolving dependencies

    Returns:
        A default event store implementation
    """
    logger = await container.resolve(LoggerProtocol)
    await logger.debug("Creating default InMemoryEventStore")
    return InMemoryEventStore()


async def get_event_bus() -> EventBusProtocol:
    """
    Retrieve the current event bus instance for Uno's event sourcing infrastructure.

    Returns:
        The configured event bus instance from the DI container

    Notes:
        - This function uses the DI container to resolve dependencies
        - The container will create and cache a singleton instance as needed
    """
    container = get_container()
    return await container.resolve(EventBusProtocol)


async def get_event_publisher() -> EventPublisherProtocol:
    """
    Retrieve the current event publisher instance for Uno's event sourcing infrastructure.

    Returns:
        The configured event publisher instance from the DI container

    Notes:
        - This function uses the DI container to resolve dependencies
        - The container will create and cache a singleton instance as needed
    """
    container = get_container()
    return await container.resolve(EventPublisherProtocol)


async def get_event_store() -> EventStoreProtocol:
    """
    Retrieve the current event store instance for Uno's event sourcing infrastructure.

    Returns:
        The configured event store instance from the DI container

    Notes:
        - This function uses the DI container to resolve dependencies
        - The container will create and cache a singleton instance as needed
    """
    container = get_container()
    return await container.resolve(EventStoreProtocol)


def register_event_bus(
    container: Container, provider: Provider[EventBusProtocol]
) -> None:
    """
    Register a custom event bus provider with the DI container.

    Args:
        container: The DI container to register with
        provider: The provider that creates event bus instances
    """
    container.register(EventBusProtocol, provider)


def register_event_publisher(
    container: Container, provider: Provider[EventPublisherProtocol]
) -> None:
    """
    Register a custom event publisher provider with the DI container.

    Args:
        container: The DI container to register with
        provider: The provider that creates event publisher instances
    """
    container.register(EventPublisherProtocol, provider)


def register_event_store(
    container: Container, provider: Provider[EventStoreProtocol]
) -> None:
    """
    Register a custom event store provider with the DI container.

    Args:
        container: The DI container to register with
        provider: The provider that creates event store instances
    """
    container.register(EventStoreProtocol, provider)

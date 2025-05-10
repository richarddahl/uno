"""
Dependency injection registration extensions for the events module.

This module provides extension methods to register event system services
with the DI container.
"""

from typing import cast

from uno.di.container import Container
from uno.events.implementations.bus import InMemoryEventBus
from uno.events.config import EventsConfig
from uno.events.protocols import EventBusProtocol, EventStoreProtocol
from uno.persistence.event_sourcing.implementations.postgres.event_store import (
    PostgresEventStore,
)
from uno.logging.protocols import LoggerProtocol


async def register_event_services(container: Container) -> None:
    """
    Register all event module services with the DI container.

    Args:
        container: The DI container to register services with
    """
    # Register configuration
    config = EventsConfig.from_env()
    await container.register_singleton(EventsConfig, lambda _: config)

    # Register event bus based on configuration
    await _register_event_bus(container, config)

    # Register event store based on configuration
    await _register_event_store(container, config)

    # Additional event system service registrations would go here


async def _register_event_bus(container: Container, config: EventsConfig) -> None:
    """
    Register the appropriate event bus implementation based on configuration.

    Args:
        container: The DI container to register services with
        config: The events configuration
    """
    event_bus_type = config.event_bus_type.lower()

    if event_bus_type == "memory":
        await container.register_singleton(
            EventBusProtocol,
            lambda c: InMemoryEventBus(
                logger=cast(LoggerProtocol, c.resolve(LoggerProtocol))
            ),
        )
    elif event_bus_type == "postgres":
        # This would use postgres implementation when available
        # For now, fall back to in-memory
        await container.register_singleton(
            EventBusProtocol,
            lambda c: InMemoryEventBus(
                logger=cast(LoggerProtocol, c.resolve(LoggerProtocol))
            ),
        )
    else:
        # Default to in-memory
        await container.register_singleton(
            EventBusProtocol,
            lambda c: InMemoryEventBus(
                logger=cast(LoggerProtocol, c.resolve(LoggerProtocol))
            ),
        )


async def _register_event_store(container: Container, config: EventsConfig) -> None:
    """
    Register the appropriate event store implementation based on configuration.

    Args:
        container: The DI container to register services with
        config: The events configuration
    """
    event_store_type = config.event_store_type.lower()

    if event_store_type == "postgres":
        # Ensure we have a connection string
        if not config.db_connection_string:
            raise ValueError(
                "Database connection string is required for PostgreSQL event store"
            )

        await container.register_singleton(
            EventStoreProtocol,
            lambda c: PostgresEventStore(
                connection_string=config.db_connection_string.get_secret_value(),
                logger=cast(LoggerProtocol, c.resolve(LoggerProtocol)),
            ),
        )
    else:
        # For now, just log a warning and default to the PostgresEventStore
        # A proper in-memory implementation would be registered here
        logger = await container.resolve(LoggerProtocol)
        logger.warning(
            f"Unsupported event store type: {event_store_type}, defaulting to PostgreSQL",
            event_store_type=event_store_type,
        )

        await container.register_singleton(
            EventStoreProtocol,
            lambda c: PostgresEventStore(
                connection_string=config.db_connection_string.get_secret_value(),
                logger=cast(LoggerProtocol, c.resolve(LoggerProtocol)),
            ),
        )

"""
Dependency injection registration extensions for the events module.

This module provides extension methods to register event system services
with the DI container.
"""

from typing import cast

from uno.injection.container import Container
from uno.events.config import EventsConfig
from uno.persistance.event_sourcing.implementations.memory.bus import InMemoryEventBus
from uno.events.implementations.handlers.middleware import (
    LoggingMiddleware,
    TimingMiddleware,
)
from uno.events.registry import EventHandlerRegistry
from uno.events.protocols import EventBusProtocol
from uno.events.publisher import EventPublisher
from uno.logging.protocols import LoggerProtocol
from uno.persistance.event_sourcing.implementations.postgres.bus import PostgresEventBus
from uno.persistance.event_sourcing.implementations.postgres.event_store import (
    PostgresEventStore,
)
from uno.persistance.event_sourcing.protocols import EventStoreProtocol
from uno.persistance.sql.config import SQLConfig
from uno.persistance.sql.connection import ConnectionManager


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

    # Register event handler registry
    await container.register_singleton(
        EventHandlerRegistry,
        lambda c: EventHandlerRegistry(logger=c.resolve("LoggerProtocol")),
    )

    # Register middleware as singletons
    await container.register_singleton(
        LoggingMiddleware,
        lambda c: LoggingMiddleware(logger=c.resolve("LoggerProtocol")),
    )
    await container.register_singleton(
        TimingMiddleware,
        lambda c: TimingMiddleware(logger=c.resolve("LoggerProtocol")),
    )

    # Register event publisher
    await container.register_singleton(
        EventPublisher,
        lambda c: EventPublisher(
            event_bus=c.resolve(EventBusProtocol),
            logger=c.resolve("LoggerProtocol"),
        ),
    )

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
                logger=cast("LoggerProtocol", c.resolve(LoggerProtocol)), config=config
            ),
        )
    elif event_bus_type == "postgres":
        # Use the PostgresEventBus implementation
        await container.register_singleton(
            EventBusProtocol,
            lambda c: PostgresEventBus(
                dsn=config.db_connection_string,
                channel="uno_events",
                table="event_outbox",
                logger=cast("LoggerProtocol", c.resolve(LoggerProtocol)),
            ),
        )
    else:
        # Default to in-memory
        await container.register_singleton(
            EventBusProtocol,
            lambda c: InMemoryEventBus(
                logger=cast("LoggerProtocol", c.resolve(LoggerProtocol)), config=config
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
                config=c.resolve(SQLConfig),
                connection_manager=c.resolve(ConnectionManager),
                logger=cast("LoggerProtocol", c.resolve(LoggerProtocol)),
            ),
        )
    elif event_store_type == "memory":
        from uno.events.implementations.store import InMemoryEventStore

        await container.register_singleton(
            EventStoreProtocol,
            lambda c: InMemoryEventStore(
                logger=cast("LoggerProtocol", c.resolve(LoggerProtocol)),
            ),
        )
    else:
        # For now, just log a warning and default to the PostgresEventStore
        # A proper in-memory implementation would be registered here
        logger = await container.resolve(LoggerProtocol)
        logger.warning(
            f"Unsupported event store type: {event_store_type}, falling back to InMemoryEventStore",
            event_store_type=event_store_type,
        )

        from uno.events.implementations.store import InMemoryEventStore

        await container.register_singleton(
            EventStoreProtocol,
            lambda c: InMemoryEventStore(
                logger=cast("LoggerProtocol", c.resolve(LoggerProtocol)),
            ),
        )

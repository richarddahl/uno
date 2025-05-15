"""
Container configuration for Uno framework dependency injection.

This module provides the standard container setup for Uno applications,
configuring all framework components with their default implementations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from uno.commands.protocols import CommandHandlerRegistryProtocol
from uno.commands.registry import CommandHandlerRegistry
from uno.config import UnoConfig
from uno.events.protocols import EventHandlerRegistryProtocol, EventPublisherProtocol
from uno.events.registry import EventHandlerRegistry
from uno.events.publisher import EventPublisher
from uno.logging.protocols import LoggerProtocol
from uno.logging.logger import UnoLogger
from uno.persistance.event_sourcing.protocols import EventStoreProtocol
from uno.persistance.event_sourcing.implementations.memory import InMemoryEventStore
from uno.persistance.event_sourcing.implementations.postgres import PostgresEventStore
from uno.snapshots.implementations.memory import (
    EventCountSnapshotStrategy,
    InMemorySnapshotStore,
)
from uno.snapshots.implementations.postgres import PostgresSnapshotStore
from uno.snapshots.protocols import SnapshotStoreProtocol, SnapshotStrategyProtocol

if TYPE_CHECKING:
    from uno.injection.protocols import ContainerProtocol


async def configure_container(container: ContainerProtocol, config: UnoConfig) -> None:
    """
    Configure the dependency injection container with standard bindings.

    This function sets up all the standard Uno framework components with
    their default implementations, which can be overridden by application code.

    Args:
        container: The DI container to configure
        config: The application configuration
    """
    # Snapshot system bindings
    container.bind(SnapshotStoreProtocol, InMemorySnapshotStore)
    container.bind(SnapshotStrategyProtocol, EventCountSnapshotStrategy)

    # Event system bindings
    container.bind(EventHandlerRegistryProtocol, EventHandlerRegistry)
    container.bind(EventPublisherProtocol, EventPublisher)
    container.bind(EventStoreProtocol, InMemoryEventStore)

    # Command system bindings
    container.bind(CommandHandlerRegistryProtocol, CommandHandlerRegistry)

    # Logger binding
    container.bind(LoggerProtocol, UnoLogger)

    # Use PostgreSQL implementations in production mode
    if config.use_postgres:
        container.bind(SnapshotStoreProtocol, PostgresSnapshotStore)
        container.bind(EventStoreProtocol, PostgresEventStore)

    # Additional environment-specific configurations
    if config.environment == "development":
        # Configure development-specific overrides
        pass
    elif config.environment == "testing":
        # Configure testing-specific overrides
        pass
    elif config.environment == "production":
        # Configure production-specific overrides
        pass

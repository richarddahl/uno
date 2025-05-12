"""
Container configuration for Uno framework dependency injection.

This module provides the standard container setup for Uno applications,
configuring all framework components with their default implementations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

from uno.commands.protocols import CommandHandlerRegistryProtocol
from uno.core.config import UnoConfig
from uno.events.protocols import EventHandlerRegistryProtocol, EventPublisherProtocol
from uno.logging.protocols import LoggerProtocol
from uno.persistence.event_sourcing.protocols import EventStoreProtocol
from uno.snapshots.implementations.memory import (
    EventCountSnapshotStrategy,
    InMemorySnapshotStore,
)
from uno.snapshots.implementations.postgres import PostgresSnapshotStore
from uno.snapshots.protocols import SnapshotStoreProtocol, SnapshotStrategyProtocol

if TYPE_CHECKING:
    from uno.core.container import Container


async def configure_container(container: Container, config: UnoConfig) -> None:
    """
    Configure the dependency injection container with standard bindings.

    This function sets up all the standard Uno framework components with
    their default implementations, which can be overridden by application code.

    Args:
        container: The DI container to configure
        config: The application configuration
    """
    # Snapshot system bindings
    container.bind(SnapshotStoreProtocol, to=InMemorySnapshotStore)
    container.bind(SnapshotStrategyProtocol, to=EventCountSnapshotStrategy)

    # Use PostgreSQL implementations in production
    if config.use_postgres:
        container.bind(SnapshotStoreProtocol, to=PostgresSnapshotStore)

    # Configure other framework components
    # ...existing code...

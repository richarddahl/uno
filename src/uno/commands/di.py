# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Dependency injection registration extensions for the commands module.

This module provides extension methods to register command system services
with the DI container.
"""

from typing import cast, TYPE_CHECKING

from uno.di.container import Container
from uno.commands.protocols import CommandBusProtocol
from uno.commands.implementations.structural_bus import StructuralCommandBus
from uno.persistence.event_sourcing.implementations.postgres.bus import (
    PostgresCommandBus,
)

if TYPE_CHECKING:
    from uno.logging.protocols import LoggerProtocol


async def register_command_services(container: Container) -> None:
    """
    Register all command module services with the DI container.

    Args:
        container: The DI container to register services with
    """
    from uno.config.loader import ConfigLoader

    # Get configuration
    config = await container.resolve(ConfigLoader)
    command_bus_type = config.get("COMMAND_BUS_TYPE", "memory").lower()

    # Register command bus based on configuration
    if command_bus_type == "memory":
        await container.register_singleton(
            CommandBusProtocol,
            lambda c: StructuralCommandBus(
                logger=cast("LoggerProtocol", c.resolve("LoggerProtocol")),
            ),
        )
    elif command_bus_type == "postgres":
        db_connection_string = config.get("DB_CONNECTION_STRING")
        if not db_connection_string:
            raise ValueError(
                "Database connection string is required for PostgreSQL command bus"
            )

        await container.register_singleton(
            CommandBusProtocol,
            lambda c: PostgresCommandBus(
                dsn=db_connection_string,
                channel="uno_commands",
                table="command_outbox",
                logger=cast("LoggerProtocol", c.resolve("LoggerProtocol")),
            ),
        )
    else:
        # Default to in-memory implementation
        await container.register_singleton(
            CommandBusProtocol,
            lambda c: StructuralCommandBus(
                logger=cast("LoggerProtocol", c.resolve("LoggerProtocol")),
            ),
        )

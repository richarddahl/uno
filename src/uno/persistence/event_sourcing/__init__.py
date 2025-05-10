# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Event sourcing persistence package for the Uno framework.

This package provides specialized persistence mechanisms for event-sourced systems.
"""

from .implementations.memory import InMemoryEventBus, InMemoryEventStore
from .implementations.postgres import (
    PostgresCommandBus,
    PostgresEventBus,
    PostgresEventStore,
    PostgresSagaStore,
)
from .protocols import EventStoreProtocol

__all__ = [
    # Protocols
    "EventStoreProtocol",
    # In-memory implementations (aliases for backward compatibility)
    "InMemoryEventBus",
    "InMemoryEventStore",
    # Postgres implementations
    "PostgresCommandBus",
    "PostgresEventBus",
    "PostgresEventStore",
    "PostgresSagaStore",
]

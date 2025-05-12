# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Persistence package for the Uno framework.

This package provides mechanisms for data persistence and storage across various
backends, including SQL databases and others.
"""

from uno.persistence.errors import (
    DBConnectionError,
    DBConstraintViolationError,
    DBDeadlockError,
    DBError,
    DBMigrationError,
    DBQueryError,
)
from uno.persistence.event_sourcing import (
    PostgresEventStore,
    PostgresEventBus,
    PostgresCommandBus,
    PostgresSagaStore,
)

__all__ = [
    # Database errors
    "DBError",
    "DBConnectionError",
    "DBQueryError",
    "DBMigrationError",
    "DBConstraintViolationError",
    "DBDeadlockError",
    # Event sourcing implementations
    "PostgresEventStore",
    "PostgresEventBus",
    "PostgresCommandBus",
    "PostgresSagaStore",
]

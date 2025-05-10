# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Public API for the Uno unit of work package.

This module exports the public API for the unit of work pattern in the Uno framework,
providing transactional boundaries for operations.
"""

from uno.uow.errors import (
    UnitOfWorkError,
    UnitOfWorkCommitError,
    UnitOfWorkRollbackError,
    TransactionError,
)
from uno.uow.protocols import UnitOfWork
from uno.uow.implementations.memory import InMemoryUnitOfWork
from uno.uow.implementations.postgres import PostgresUnitOfWork

__all__ = [
    # Core protocols
    "UnitOfWork",
    # Errors
    "UnitOfWorkError",
    "UnitOfWorkCommitError",
    "UnitOfWorkRollbackError",
    "TransactionError",
    # Implementations
    "InMemoryUnitOfWork",
    "PostgresUnitOfWork",
]

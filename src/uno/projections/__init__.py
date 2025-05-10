# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Public API for the Uno projections package.

This module exports the public API for projections in the Uno framework,
providing read model generation and persistence capabilities.
"""

from uno.projections.errors import (
    ProjectionError,
    ProjectionNotFoundError,
    ProjectionStoreError,
)
from uno.projections.protocols import Projection, ProjectionStore
from uno.projections.implementations.memory import InMemoryProjectionStore

__all__ = [
    # Core protocols
    "Projection",
    "ProjectionStore",
    # Errors
    "ProjectionError",
    "ProjectionNotFoundError",
    "ProjectionStoreError",
    # Implementations
    "InMemoryProjectionStore",
]

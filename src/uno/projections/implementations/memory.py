# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
In-memory implementations for the projections package.

This module provides memory-based implementations of projection stores for testing
and simple use cases.
"""

from typing import Any, Dict, Generic, TypeVar
from uno.projections.protocols import ProjectionStore


T = TypeVar("T")


class InMemoryProjectionStore(Generic[T], ProjectionStore[T]):
    """
    In-memory implementation of a projection store.

    This is useful for testing and simple applications where persistence is not required.
    """

    def __init__(self):
        self._store: Dict[str, T] = {}

    async def get(self, id: str) -> T | None:
        """Get a projection by ID."""
        return self._store.get(id)

    async def save(self, id: str, projection: T) -> None:
        """Save a projection."""
        self._store[id] = projection

    async def delete(self, id: str) -> None:
        """Delete a projection."""
        self._store.pop(id, None)

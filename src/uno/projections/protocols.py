# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Protocol definitions for the projections package.

This module contains the core protocols that define the interfaces for projection
and read model components.
"""

from abc import ABC, abstractmethod
from typing import Any, Protocol, TypeVar

T = TypeVar("T")


class Projection(ABC):
    """
    Base class for projections (read models).
    """

    @abstractmethod
    async def project(self, event: Any) -> None:
        """Apply an event to the projection/read model."""
        pass


class ProjectionStore(Protocol[T]):
    """
    Protocol for storing and retrieving projections/read models.
    """

    async def get(self, id: str) -> T | None: ...
    async def save(self, id: str, projection: T) -> None: ...
    async def delete(self, id: str) -> None: ...

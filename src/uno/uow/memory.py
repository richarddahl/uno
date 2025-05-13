# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
In-memory implementations for the unit of work package.

This module provides memory-based implementations of the unit of work pattern for testing
and simple use cases.
"""

from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict

from uno.uow.errors import UnitOfWorkCommitError, UnitOfWorkRollbackError
from uno.uow.protocols import UnitOfWork


class InMemoryUnitOfWork(UnitOfWork):
    """
    In-memory implementation of the Unit of Work pattern.

    This is useful for testing and simple applications where persistence is not required.
    """

    def __init__(self, event_store=None):
        self._changes: Dict[str, Any] = {}
        self._committed = False
        self._rolled_back = False
        self.event_store = event_store

    async def commit(self) -> None:
        """
        Commit all changes made within this unit of work.

        For the in-memory implementation, this simply marks the UoW as committed.
        """
        if self._rolled_back:
            raise UnitOfWorkCommitError("Cannot commit a rolled back unit of work")

        self._committed = True

    async def rollback(self) -> None:
        """
        Roll back all changes made within this unit of work.

        For the in-memory implementation, this simply marks the UoW as rolled back
        and clears any pending changes.
        """
        if self._committed:
            raise UnitOfWorkRollbackError("Cannot roll back a committed unit of work")

        self._rolled_back = True
        self._changes.clear()

    @classmethod
    @asynccontextmanager
    async def begin(cls, **kwargs) -> AsyncGenerator["InMemoryUnitOfWork", None]:
        """
        Start a new in-memory unit of work.

        Returns:
            An asynchronous context manager yielding an InMemoryUnitOfWork instance.

        Example:
            ```python
            async with InMemoryUnitOfWork.begin() as uow:
                # Perform operations
                await uow.commit()
            ```
        """
        uow = cls(**kwargs)
        try:
            yield uow
        except Exception:
            await uow.rollback()
            raise

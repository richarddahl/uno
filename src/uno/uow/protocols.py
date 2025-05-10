# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Protocol definitions for the unit of work package.

This module contains the core protocols that define the interfaces for the unit of work pattern.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from typing import Any, TypeVar


T = TypeVar("T")


class UnitOfWork(ABC):
    """
    Unit of Work abstract base class.

    The Unit of Work pattern provides a way to group operations into a single
    transactional unit, ensuring that they either all succeed or all fail.
    """

    @abstractmethod
    async def commit(self) -> None:
        """
        Commit all changes made within this unit of work.

        Raises:
            UnitOfWorkCommitError: If the commit fails.
        """
        ...

    @abstractmethod
    async def rollback(self) -> None:
        """
        Roll back all changes made within this unit of work.

        Raises:
            UnitOfWorkRollbackError: If the rollback fails.
        """
        ...

    @classmethod
    @abstractmethod
    @asynccontextmanager
    async def begin(cls, **kwargs) -> AsyncGenerator["UnitOfWork", None]:
        """
        Start a new unit of work.

        Returns:
            An asynchronous context manager yielding a UnitOfWork instance.

        Example:
            ```python
            async with UnitOfWork.begin() as uow:
                # Perform operations
                await uow.commit()
            ```
        """
        yield None

"""Unit of Work factory implementations."""

from typing import Any, Callable, Optional, Type, TypeVar
from contextlib import asynccontextmanager

from pydantic import BaseModel

from uno.uow.protocols import (
    UnitOfWorkProtocol,
    UnitOfWorkManagerProtocol,
    RepositoryFactory,
)
from .base import BaseUnitOfWork
from .errors import UnitOfWorkError

T = TypeVar("T", bound=BaseUnitOfWork)


class UnitOfWorkFactory:
    """Factory for creating and managing Unit of Work instances.

    This class provides a convenient way to create and manage UoW instances
    with proper resource cleanup.
    """

    def __init__(
        self,
        uow_class: Type[T],
        repository_factory: RepositoryFactory,
        **uow_kwargs: Any,
    ) -> None:
        """Initialize the factory.

        Args:
            uow_class: The Unit of Work class to instantiate
            repository_factory: Factory function to create repositories
            **uow_kwargs: Additional arguments to pass to the UoW constructor
        """
        self._uow_class = uow_class
        self._repository_factory = repository_factory
        self._uow_kwargs = uow_kwargs

    async def start(self) -> UnitOfWork:
        """Start a new unit of work."""
        return self._uow_class(
            repository_factory=self._repository_factory, **self._uow_kwargs
        )

    async def commit(self, uow: UnitOfWork) -> None:
        """Commit a unit of work."""
        if not isinstance(uow, self._uow_class):
            raise UnitOfWorkError("Incompatible Unit of Work type")
        await uow.commit()

    async def rollback(self, uow: UnitOfWork) -> None:
        """Roll back a unit of work."""
        if not isinstance(uow, self._uow_class):
            raise UnitOfWorkError("Incompatible Unit of Work type")
        await uow.rollback()

    @asynccontextmanager
    async def transaction(self) -> UnitOfWork:
        """Context manager for a unit of work with automatic commit/rollback."""
        uow = await self.start()
        try:
            async with uow:
                yield uow
        except Exception:
            await self.rollback(uow)
            raise


class UnitOfWorkContext:
    """Context manager for working with a Unit of Work."""

    def __init__(
        self, uow_factory: UnitOfWorkManager, auto_commit: bool = True
    ) -> None:
        """Initialize the context manager.

        Args:
            uow_factory: Factory to create Unit of Work instances
            auto_commit: Whether to automatically commit on successful completion
        """
        self._uow_factory = uow_factory
        self._auto_commit = auto_commit
        self._uow: Optional[UnitOfWork] = None

    async def __aenter__(self) -> UnitOfWork:
        """Enter the async context manager."""
        self._uow = await self._uow_factory.start()
        return self._uow

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the async context manager."""
        if self._uow is None:
            return

        try:
            if exc_type is None and self._auto_commit:
                await self._uow_factory.commit(self._uow)
            else:
                await self._uow_factory.rollback(self._uow)
        finally:
            if hasattr(self._uow, "dispose"):
                await self._uow.dispose()
            self._uow = None

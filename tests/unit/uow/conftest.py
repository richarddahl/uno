"""Pytest fixtures for Unit of Work tests."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from typing import Any, AsyncGenerator, Type, TypeVar

from uno.domain.aggregate import AggregateRoot
from uno.domain.repository import BaseRepository
from uno.uow.base import BaseUnitOfWork
from uno.uow.factory import UnitOfWorkFactory, UnitOfWorkManager

T = TypeVar("T", bound=AggregateRoot)


class MockRepository(BaseRepository[T]):
    """Mock repository for testing purposes."""

    def __init__(self, aggregate_type: Type[T]):
        self.aggregate_type = aggregate_type
        self._storage: dict[str, T] = {}
        self._seen: set[T] = set()

    async def get(self, id: str) -> T | None:
        return self._storage.get(id)

    async def add(self, aggregate: T) -> None:
        self._storage[str(aggregate.id)] = aggregate
        self._seen.add(aggregate)

    def seen(self) -> set[T]:
        return self._seen.copy()

    def clear(self) -> None:
        self._seen.clear()

    async def persist_all(self) -> None:
        pass


class MockUnitOfWork(BaseUnitOfWork):
    """Mock Unit of Work for testing."""

    async def _commit(self) -> None:
        pass

    async def _rollback(self) -> None:
        pass


@pytest.fixture
def mock_repository_factory():
    """Fixture that provides a repository factory for testing."""
    repositories = {}

    def factory(aggregate_type: Type[T]) -> BaseRepository[T]:
        if aggregate_type not in repositories:
            repositories[aggregate_type] = MockRepository(aggregate_type)
        return repositories[aggregate_type]

    return factory


@pytest.fixture
def uow_factory(mock_repository_factory) -> UnitOfWorkManager:
    """Fixture that provides a UnitOfWorkFactory for testing."""
    return UnitOfWorkFactory(
        uow_class=MockUnitOfWork, repository_factory=mock_repository_factory
    )


@pytest.fixture
async def uow(uow_factory: UnitOfWorkManager) -> AsyncGenerator[MockUnitOfWork, None]:
    """Fixture that provides a UnitOfWork instance for testing."""
    uow = await uow_factory.start()
    try:
        yield uow
    finally:
        await uow.dispose()

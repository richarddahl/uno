from typing import Any, Protocol, runtime_checkable

import pytest

from uno.infrastructure.di.container import DIContainer
from uno.infrastructure.di.errors import ScopeError


# Define test protocols and implementations
@runtime_checkable
class IRepository(Protocol):
    def add(self, item: Any) -> None: ...
    def get(self, id: str) -> Any: ...


class MemoryRepository:
    def __init__(self) -> None:
        self._store: dict[str, Any] = {}

    def add(self, item: Any) -> None:
        self._store[id(item)] = item

    def get(self, id: str) -> Any:
        return self._store[id]


@pytest.mark.asyncio
async def test_scoped_services_isolated_between_scopes() -> None:
    container = DIContainer()
    await container.register_scoped(IRepository, MemoryRepository)

    # Create two sequential scopes
    async with container.create_scope() as scope1:
        repo1 = await scope1.resolve(IRepository)

    async with container.create_scope() as scope2:
        repo2 = await scope2.resolve(IRepository)

    # Verify different instances across scopes
    assert repo1 is not repo2


@pytest.mark.asyncio
async def test_scope_disposal() -> None:
    container = DIContainer()

    # Create a disposable service
    class DisposableService:
        def __init__(self) -> None:
            self.disposed = False

        async def dispose(self) -> None:
            self.disposed = True

    await container.register_scoped(DisposableService, DisposableService)

    # Create a scope and resolve the service
    async with container.create_scope() as scope:
        service = await scope.resolve(DisposableService)
        assert not service.disposed

    # Verify the service was disposed
    assert service.disposed


@pytest.mark.asyncio
async def test_cannot_use_disposed_scope() -> None:
    container = DIContainer()
    await container.register_scoped(IRepository, MemoryRepository)

    # Create and dispose a scope
    async with container.create_scope() as scope:
        pass  # Scope is automatically disposed at the end of the block

    # Verify we can't use the disposed scope
    with pytest.raises(ScopeError):
        await scope.resolve(IRepository)

from typing import Protocol, runtime_checkable

import pytest

from uno.infrastructure.di.container import DIContainer
from uno.infrastructure.di.errors import ScopeError


# Define test protocols and implementations
@runtime_checkable
class ILogger(Protocol):
    def log(self, message: str) -> None: ...


class ConsoleLogger:
    def log(self, message: str) -> None:
        pass  # Mock implementation


@runtime_checkable
class IRepository(Protocol):
    def get_by_id(self, id: int) -> dict: ...


class MemoryRepository:
    def get_by_id(self, id: int) -> dict:
        return {"id": id}


@pytest.mark.asyncio
async def test_container_disposal() -> None:
    container = DIContainer()

    # Register a disposable singleton
    class DisposableService:
        def __init__(self):
            self.disposed = False

        def dispose(self):
            self.disposed = True

    await container.register_singleton(DisposableService, DisposableService)
    service = await container.resolve(DisposableService)

    # Dispose the container
    await container.dispose()

    # Verify the service was disposed
    assert service.disposed

    # Verify we can't use the disposed container
    with pytest.raises(ScopeError):
        await container.register_singleton(ILogger, ConsoleLogger)

    with pytest.raises(ScopeError):
        await container.resolve(DisposableService)


@pytest.mark.asyncio
async def test_dispose_with_active_scope() -> None:
    container = DIContainer()
    await container.register_scoped(IRepository, MemoryRepository)

    # Create a scope and resolve a service
    async with container.create_scope() as scope:
        repo = await scope.resolve(IRepository)

        # Dispose the container while a scope is active
        await container.dispose()

        # Verify we can't use the disposed container
        with pytest.raises(ScopeError):
            await container.resolve(IRepository)

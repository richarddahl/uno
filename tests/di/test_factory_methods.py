import asyncio
from typing import Protocol, runtime_checkable

import pytest

from uno.infrastructure.di.container import Container


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
async def test_container_create_factory() -> None:
    # Define a configuration function
    async def configure(container: Container) -> None:
        await container.register_singleton(ILogger, ConsoleLogger)
        await container.register_scoped(IRepository, MemoryRepository)

    # Create a container using the factory
    container = await Container.create(configure)

    # Verify the container is properly configured
    logger = await container.resolve(ILogger)
    assert isinstance(logger, ConsoleLogger)

    async with container.create_scope() as scope:
        repo = await scope.resolve(IRepository)
        assert isinstance(repo, MemoryRepository)

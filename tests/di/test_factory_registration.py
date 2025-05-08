import asyncio
from typing import Protocol, runtime_checkable

import pytest

from uno.infrastructure.di.container import Container


# Define test protocols and implementations


@runtime_checkable
class ILogger(Protocol):
    def log(self, message: str) -> None: ...


@runtime_checkable
class IRepository(Protocol):
    def get_by_id(self, id: int) -> dict: ...


class ConsoleLogger:
    def log(self, message: str) -> None:
        pass  # Mock implementation


class MemoryRepository:
    def get_by_id(self, id: int) -> dict:
        return {"id": id}


@pytest.mark.asyncio
async def test_register_with_sync_factory() -> None:
    """Test registering a service with a synchronous factory function."""
    container = Container()

    def create_logger() -> ILogger:
        return ConsoleLogger()

    await container.register_singleton(ILogger, create_logger)
    logger = await container.resolve(ILogger)

    assert isinstance(logger, ConsoleLogger)


@pytest.mark.asyncio
async def test_register_with_async_factory() -> None:
    """Test registering a service with an asynchronous factory function."""
    container = Container()

    async def create_repository() -> IRepository:
        # Simulate async work
        await asyncio.sleep(0.01)
        return MemoryRepository()

    await container.register_singleton(IRepository, create_repository)
    repo = await container.resolve(IRepository)

    assert isinstance(repo, MemoryRepository)

import asyncio
from typing import Protocol, runtime_checkable

import pytest

from uno.di.container import Container


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
async def test_concurrent_resolution() -> None:
    container = Container()
    await container.register_singleton(ILogger, ConsoleLogger)
    await container.register_transient(IRepository, MemoryRepository)

    # Define a function to resolve services
    async def resolve_services() -> tuple[ILogger, IRepository]:
        logger = await container.resolve(ILogger)
        repo = await container.resolve(IRepository)
        return logger, repo

    # Resolve services concurrently
    tasks = [resolve_services() for _ in range(10)]
    results = await asyncio.gather(*tasks)

    # Verify all resolutions succeeded
    for logger, repo in results:
        assert isinstance(logger, ConsoleLogger)
        assert isinstance(repo, MemoryRepository)

    # Verify singleton behavior
    loggers = [logger for logger, _ in results]
    assert all(logger is loggers[0] for logger in loggers)

    # Verify transient behavior
    repos = [repo for _, repo in results]
    for i in range(len(repos)):
        for j in range(i + 1, len(repos)):
            assert repos[i] is not repos[j]

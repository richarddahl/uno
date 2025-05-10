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
async def test_container_create_factory() -> None:
    # Define a simpler configuration function to avoid complex error paths
    async def configure(container: Container) -> None:
        # Use concrete implementations directly to avoid factory resolution
        try:
            await container.register_singleton(ILogger, ConsoleLogger)
            await container.register_scoped(IRepository, MemoryRepository)
        except Exception as e:
            # If an error occurs during configuration, ensure any coroutines are closed
            import inspect
            if inspect.iscoroutine(container):
                container.close()
            raise e

    # Create a container using the factory
    container = await Container.create(configure)

    # Verify the logger is correctly registered and resolvable
    logger = await container.resolve(ILogger)
    assert isinstance(logger, ConsoleLogger)
    
    # Test scoped service in a controlled scope
    async with container.create_scope() as scope:
        repo = await scope.resolve(IRepository)
        assert isinstance(repo, MemoryRepository)

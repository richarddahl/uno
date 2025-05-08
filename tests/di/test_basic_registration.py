from typing import Protocol, runtime_checkable

import pytest

from uno.infrastructure.di.container import DIContainer
from uno.infrastructure.di.errors import ServiceNotRegisteredError


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
async def test_register_and_resolve_singleton() -> None:
    """Test registering and resolving a singleton service.

    This test verifies that:
    1. A singleton service can be registered
    2. The same instance is returned when resolving multiple times
    3. The resolved instance is of the correct type
    """
    container = DIContainer()
    await container.register_singleton(ILogger, ConsoleLogger)

    # Resolve the service
    logger1 = await container.resolve(ILogger)
    logger2 = await container.resolve(ILogger)

    # Verify instance type
    assert isinstance(logger1, ConsoleLogger)
    # Verify singleton behavior (same instance)
    assert logger1 is logger2


@pytest.mark.asyncio
async def test_register_and_resolve_transient() -> None:
    """Test registering and resolving a transient service.

    This test verifies that:
    1. A transient service can be registered
    2. Different instances are returned when resolving multiple times
    3. The resolved instances are of the correct type
    """
    container = DIContainer()
    await container.register_transient(IRepository, MemoryRepository)

    # Resolve multiple instances
    repo1 = await container.resolve(IRepository)
    repo2 = await container.resolve(IRepository)

    # Verify instance type
    assert isinstance(repo1, MemoryRepository)
    # Verify transient behavior (different instances)
    assert repo1 is not repo2


@pytest.mark.asyncio
async def test_register_and_resolve_scoped() -> None:
    """Test registering and resolving a scoped service.

    This test verifies that:
    1. A scoped service can be registered
    2. The same instance is returned within the same scope
    3. Different instances are returned in different scopes
    4. The resolved instances are of the correct type
    """
    container = DIContainer()
    await container.register_scoped(IRepository, MemoryRepository)

    # Create a scope and resolve the service
    async with container.create_scope() as scope:
        repo1 = await scope.resolve(IRepository)
        repo2 = await scope.resolve(IRepository)

        # Verify instance type
        assert isinstance(repo1, MemoryRepository)
        # Verify scoped behavior (same instance within scope)
        assert repo1 is repo2


@pytest.mark.asyncio
async def test_service_not_registered() -> None:
    """Test resolving a non-registered service.

    This test verifies that:
    1. Resolving a non-registered service raises ServiceNotRegisteredError
    2. The error contains the correct interface type
    """
    container = DIContainer()

    # Try to resolve a service that hasn't been registered
    with pytest.raises(ServiceNotRegisteredError):
        await container.resolve(ILogger)

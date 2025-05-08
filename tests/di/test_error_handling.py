from typing import Any, Protocol, runtime_checkable

import pytest

from uno.infrastructure.di.container import DIContainer
from uno.infrastructure.di.errors import (
    DuplicateRegistrationError,
    ScopeError,
    ServiceCreationError,
    ServiceNotRegisteredError,
    TypeMismatchError,
)


# Define test protocols and implementations
@runtime_checkable
class ILogger(Protocol):
    def log(self, message: str) -> None: ...


@runtime_checkable
class IRepository(Protocol):
    def get_by_id(self, id: int) -> dict[str, Any]: ...


class ConsoleLogger:
    def log(self, message: str) -> None:
        pass  # Mock implementation


class NotALogger:
    pass


class MemoryRepository:
    def get_by_id(self, id: int) -> dict[str, Any]:
        return {"id": id}


@pytest.mark.asyncio
async def test_duplicate_registration() -> None:
    """Test that registering the same service twice raises DuplicateRegistrationError."""
    container = DIContainer()
    await container.register_singleton(ILogger, ConsoleLogger)

    with pytest.raises(DuplicateRegistrationError):
        await container.register_singleton(ILogger, ConsoleLogger)


@pytest.mark.asyncio
async def test_service_not_registered() -> None:
    """Test that resolving an unregistered service raises ServiceNotRegisteredError."""
    container = DIContainer()
    with pytest.raises(ServiceNotRegisteredError):
        await container.resolve(ILogger)


@pytest.mark.asyncio
async def test_type_mismatch() -> None:
    """Test that registering a service that doesn't implement the interface raises TypeMismatchError."""
    container = DIContainer()

    class BadLogger:
        # Missing the 'log' method that ILogger requires
        pass

    with pytest.raises(ServiceCreationError) as excinfo:
        await container.register_singleton(ILogger, BadLogger)
        
    # Verify the underlying cause is a TypeMismatchError
    assert isinstance(excinfo.value.__cause__, TypeMismatchError)


@pytest.mark.asyncio
async def test_resolve_scoped_outside_scope() -> None:
    """Test that resolving a scoped service outside of a scope raises ScopeError."""
    container = DIContainer()
    await container.register_scoped(IRepository, MemoryRepository)

    with pytest.raises(ScopeError):
        await container.resolve(IRepository)

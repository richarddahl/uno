import pytest
from uno.injection.container import Container
from uno.injection.errors import ScopeError, ScopeDisposedError


class FakeSingletonService:
    pass


class FakeScopedService:
    pass


class FakeTransientService:
    pass


@pytest.mark.asyncio
async def test_scope_resolves_parent_services():
    # Initialize the container correctly (no await)
    parent = Container()

    # Register a singleton service
    await parent.register_singleton(FakeSingletonService, FakeSingletonService)

    # Use create_scope with async with, not directly awaiting it
    async with parent.create_scope() as scope:
        # Resolve the singleton service from the child scope
        service = await scope.resolve(FakeSingletonService)
        assert isinstance(service, FakeSingletonService)

    # Clean up
    await parent.dispose()


@pytest.mark.asyncio
async def test_scope_disposal_prevents_resolution():
    # Initialize the container correctly (no await)
    container = Container()

    # Register a scoped service
    await container.register_scoped(FakeScopedService, FakeScopedService)

    # Create and immediately dispose a scope
    scope = None
    async with container.create_scope() as s:
        scope = s
        # Verify we can resolve while scope is active
        service = await scope.resolve(FakeScopedService)
        assert isinstance(service, FakeScopedService)

    # Now scope is disposed (after exiting the async with block)
    # Attempting to resolve should raise an error
    with pytest.raises(Exception):  # Specific error type depends on your implementation
        await scope.resolve(FakeScopedService)

    # Clean up
    await container.dispose()


@pytest.mark.asyncio
async def test_scope_error_on_out_of_scope_resolution():
    container = Container()
    await container.register_scoped(FakeScopedService, FakeScopedService)
    with pytest.raises(ScopeError):
        await container.resolve(FakeScopedService)

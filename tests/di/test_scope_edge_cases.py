"""
Test edge cases for scope management in the DI container.
"""

from typing import Any, Protocol, runtime_checkable

import pytest

from uno.infrastructure.di.container import Container
from uno.infrastructure.di.errors import ScopeError


@runtime_checkable
class IService(Protocol):
    def do_something(self) -> None: ...


class Service:
    def do_something(self) -> None:
        pass


@pytest.mark.asyncio
async def test_nested_scopes_with_different_lifetimes() -> None:
    """Test that nested scopes with different service lifetimes work correctly."""
    container = Container()

    # Register a test service with transient lifetime
    await container.register_transient(IService, Service)

    async with container.create_scope() as scope1:
        # Resolve the transient service twice from the same scope
        transient1 = await scope1.resolve(IService)
        transient2 = await scope1.resolve(IService)
        # Transient services should be different instances even in the same scope
        assert transient1 is not transient2

        # Now test scoped
        # Re-register with scoped lifetime
        await container.register_scoped(IService, Service, replace=True)

        # Scoped services should be same instance within a scope
        scoped1 = await scope1.resolve(IService)
        scoped2 = await scope1.resolve(IService)
        assert scoped1 is scoped2

        # But different across scopes
        async with container.create_scope() as scope2:
            scoped3 = await scope2.resolve(IService)
            assert scoped1 is not scoped3

        # Finally test singleton
        # Re-register with singleton lifetime
        await container.register_singleton(IService, Service, replace=True)

        # Singleton services should be same instance across all scopes
        singleton1 = await scope1.resolve(IService)
        async with container.create_scope() as scope3:
            singleton2 = await scope3.resolve(IService)
            assert singleton1 is singleton2

            # Re-register as scoped to test scoped behavior
            await container.register_scoped(IService, Service, replace=True)

            # Create a new scope to test scoped services
            async with container.create_scope() as scope4:
                # Scoped services should be different across different scopes
                scoped1 = await scope1.resolve(IService)
                scoped4 = await scope4.resolve(IService)
                assert scoped1 is not scoped4

                # Re-register as transient to test transient behavior
                await container.register_transient(IService, Service, replace=True)

                # Transient services should be different instances even in the same scope
                # Use container directly to ensure we're not getting cached instances
                transient1 = await container.resolve(IService)
                transient2 = await container.resolve(IService)
                assert transient1 is not transient2


@pytest.mark.asyncio
async def test_scope_disposal_with_active_dependencies() -> None:
    """Test that scope disposal properly cleans up active dependencies."""
    container = Container()
    await container.register_scoped(IService, Service)

    async with container.create_scope() as scope:
        service = await scope.resolve(IService)
        assert service is not None

    # After scope disposal, resolving should fail
    with pytest.raises(ScopeError):
        await scope.resolve(IService)


@pytest.mark.asyncio
async def test_scope_reentry() -> None:
    """Test that scopes cannot be re-entered after disposal."""
    container = Container()
    await container.register_scoped(IService, Service)

    async with container.create_scope() as scope:
        # First resolution works
        await scope.resolve(IService)

    # After scope disposal, re-entering should fail
    with pytest.raises(ScopeError):
        async with scope:
            await scope.resolve(IService)

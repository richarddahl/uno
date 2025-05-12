import pytest
from uno.di.container import Container
from uno.di.protocols import Lifetime
import asyncio

class FakeAsyncResource:
    disposed: bool = False

    async def do_work(self) -> str:
        await asyncio.sleep(0.01)
        return "done"

    async def dispose(self) -> None:
        self.disposed = True

@pytest.mark.asyncio
async def test_scoped_service_lifetime_and_disposal():
    container = Container()

    # Register FakeAsyncResource as a scoped service
    await container.register_scoped(FakeAsyncResource, FakeAsyncResource)

    async with container.create_scope() as scope:
        resource = await scope.resolve(FakeAsyncResource)
        assert isinstance(resource, FakeAsyncResource)
        assert not resource.disposed
        result = await resource.do_work()
        assert result == "done"

    # After the scope, the resource should be disposed by the container
    assert resource.disposed

@pytest.mark.asyncio
async def test_scoped_service_not_shared_between_scopes():
    container = Container()
    await container.register_scoped(FakeAsyncResource, FakeAsyncResource)

    async with container.create_scope() as scope1:
        res1 = await scope1.resolve(FakeAsyncResource)
        async with container.create_scope() as scope2:
            res2 = await scope2.resolve(FakeAsyncResource)
            assert res1 is not res2

@pytest.mark.asyncio
async def test_scoped_service_not_accessible_outside_scope():
    container = Container()
    await container.register_scoped(FakeAsyncResource, FakeAsyncResource)

    async with container.create_scope() as scope:
        resource = await scope.resolve(FakeAsyncResource)
        assert isinstance(resource, FakeAsyncResource)
    # Outside the scope, resolving should fail (in a new scope)
    from uno.di.errors import ScopeError, ServiceNotRegisteredError
    async with container.create_scope() as new_scope:
        with pytest.raises((ScopeError, ServiceNotRegisteredError)):
            await new_scope.resolve(FakeAsyncResource)

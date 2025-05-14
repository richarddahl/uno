import pytest
from uno.di.container import Container
from uno.di.errors import ScopeError, DIScopeDisposedError

class FakeScopedService:
    def __init__(self):
        self.value = 123

@pytest.mark.asyncio
async def test_scope_resolves_parent_services():
    container = Container()
    await container.register_singleton(FakeScopedService, FakeScopedService)
    async with container.create_scope() as scope:
        inst = await scope.resolve(FakeScopedService)
        assert isinstance(inst, FakeScopedService)
        assert inst.value == 123

@pytest.mark.asyncio
async def test_scope_disposal_prevents_resolution():
    container = Container()
    await container.register_scoped(FakeScopedService, FakeScopedService)
    async with container.create_scope() as scope:
        inst = await scope.resolve(FakeScopedService)
    with pytest.raises(DIScopeDisposedError):
        await scope.resolve(FakeScopedService)

@pytest.mark.asyncio
async def test_scope_error_on_out_of_scope_resolution():
    container = Container()
    await container.register_scoped(FakeScopedService, FakeScopedService)
    with pytest.raises(ScopeError):
        await container.resolve(FakeScopedService)

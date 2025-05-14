import pytest
from uno.di.container import Container
from uno.di.errors import DICircularDependencyError

@pytest.mark.asyncio
async def test_circular_dependency_error_details():
    class ServiceA:
        def __init__(self, b: 'ServiceB'):
            self.b = b
    class ServiceB:
        def __init__(self, a: ServiceA):
            self.a = a
    container = Container()
    async def factory_a(_):
        b = await container.resolve(ServiceB)
        return ServiceA(b)
    async def factory_b(_):
        a = await container.resolve(ServiceA)
        return ServiceB(a)
    await container.register_singleton(ServiceA, factory_a)
    await container.register_singleton(ServiceB, factory_b)
    with pytest.raises(DICircularDependencyError) as exc:
        await container.resolve(ServiceA)
    err = exc.value
    assert hasattr(err, "context")
    assert "dependency_chain" in err.context
    assert "circular_dependency" in err.context

import pytest
from uno.injection.container import Container
from uno.injection.errors import CircularDependencyError


@pytest.mark.asyncio
async def test_circular_dependency_error_details():
    class ServiceA:
        def __init__(self, b: "ServiceB" = None):
            self.b = b

    class ServiceB:
        def __init__(self, a: ServiceA = None):
            self.a = a

    container = Container()

    # Define factories that create circular dependency
    async def factory_a(c):
        b = await c.resolve(ServiceB)
        return ServiceA(b)

    async def factory_b(c):
        a = await c.resolve(ServiceA)
        return ServiceB(a)

    # Register both services with factories - DO NOT pre-register with placeholders
    await container.register_transient(ServiceB, factory_b)
    await container.register_transient(ServiceA, factory_a)

    # Now resolving should trigger the circular dependency
    with pytest.raises(CircularDependencyError) as exc:
        await container.resolve(ServiceA)

    err = exc.value
    assert hasattr(err, "context")
    assert "dependency_chain" in err.context
    assert "circular_dependency" in err.context

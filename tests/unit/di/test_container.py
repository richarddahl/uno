import pytest
import asyncio
from uno.di.container import Container
from uno.di.registration import ServiceRegistration
from uno.di.errors import (
    DuplicateRegistrationError,
    ScopeError,
    ServiceCreationError,
    ServiceNotRegisteredError,
    TypeMismatchError,
    DICircularDependencyError,
    DIServiceCreationError,
    DIServiceNotFoundError,
    ContainerDisposedError,
    DIScopeDisposedError,
)
from uno.di.protocols import ContainerProtocol, ScopeProtocol

class FakeService:
    def __init__(self):
        self.value = 42

class FakeScopedService:
    def __init__(self):
        self.value = 99

@pytest.mark.asyncio
async def test_singleton_registration_and_resolution():
    container = Container()
    await container.register_singleton(FakeService, FakeService)
    instance1 = await container.resolve(FakeService)
    instance2 = await container.resolve(FakeService)
    assert instance1 is instance2
    assert instance1.value == 42

@pytest.mark.asyncio
async def test_scoped_registration_and_resolution():
    container = Container()
    await container.register_scoped(FakeScopedService, FakeScopedService)
    async with container.create_scope() as scope1:
        inst1 = await scope1.resolve(FakeScopedService)
        inst2 = await scope1.resolve(FakeScopedService)
        assert inst1 is inst2
        assert inst1.value == 99
    async with container.create_scope() as scope2:
        inst3 = await scope2.resolve(FakeScopedService)
        assert inst3 is not inst1

@pytest.mark.asyncio
async def test_transient_registration_and_resolution():
    container = Container()
    await container.register_transient(FakeService, FakeService)
    inst1 = await container.resolve(FakeService)
    inst2 = await container.resolve(FakeService)
    assert inst1 is not inst2

@pytest.mark.asyncio
async def test_dispose_container_and_scope():
    container = Container()
    await container.register_singleton(FakeService, FakeService)
    instance = await container.resolve(FakeService)
    await container.dispose()
    with pytest.raises(ContainerDisposedError):
        await container.resolve(FakeService)

@pytest.mark.asyncio
async def test_service_not_registered_error():
    container = Container()
    with pytest.raises(ServiceNotRegisteredError):
        await container.resolve(FakeScopedService)

@pytest.mark.asyncio
async def test_duplicate_registration_error():
    container = Container()
    await container.register_singleton(FakeService, FakeService)
    with pytest.raises(DuplicateRegistrationError):
        await container.register_singleton(FakeService, FakeService)

@pytest.mark.asyncio
async def test_scope_disposed_error():
    container = Container()
    await container.register_scoped(FakeScopedService, FakeScopedService)
    async with container.create_scope() as scope:
        inst = await scope.resolve(FakeScopedService)
    with pytest.raises(DIScopeDisposedError):
        await scope.resolve(FakeScopedService)

@pytest.mark.asyncio
async def test_circular_dependency_detection():
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
    with pytest.raises(DICircularDependencyError):
        await container.resolve(ServiceA)

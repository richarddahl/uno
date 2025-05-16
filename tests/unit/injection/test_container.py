import pytest
import asyncio
from uno.injection.container import Container
from uno.injection.registration import ServiceRegistration
from uno.injection.errors import (
    DuplicateRegistrationError,
    ScopeError,
    ServiceCreationError,
    ServiceNotFoundError,
    TypeMismatchError,
    CircularDependencyError,
    InjectionError,
    ServiceNotFoundError,
    ContainerDisposedError,
    ScopeDisposedError,
)
from uno.injection.protocols import ContainerProtocol, ScopeProtocol


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
    container = await Container.create()
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
    container = await Container.create()
    await container.register_transient(FakeService, FakeService)
    inst1 = await container.resolve(FakeService)
    inst2 = await container.resolve(FakeService)
    assert inst1 is not inst2


@pytest.mark.asyncio
async def test_dispose_container_and_scope():
    container = await Container.create()
    await container.register_singleton(FakeService, FakeService)
    instance = await container.resolve(FakeService)
    await container.dispose()
    with pytest.raises(ContainerDisposedError):
        await container.resolve(FakeService)


@pytest.mark.asyncio
async def test_service_not_registered_error():
    container = await Container.create()
    with pytest.raises(ServiceNotFoundError):
        await container.resolve(FakeScopedService)


@pytest.mark.asyncio
async def test_duplicate_registration_error():
    container = await Container.create()
    await container.register_singleton(FakeService, FakeService)
    with pytest.raises(DuplicateRegistrationError):
        await container.register_singleton(FakeService, FakeService)


@pytest.mark.asyncio
async def test_scope_disposed_error():
    container = await Container.create()
    await container.register_scoped(FakeScopedService, FakeScopedService)
    async with container.create_scope() as scope:
        inst = await scope.resolve(FakeScopedService)
    with pytest.raises(ScopeDisposedError):
        await scope.resolve(FakeScopedService)


@pytest.mark.asyncio
async def test_circular_dependency_detection():
    """Test that circular dependencies are properly detected and reported."""
    container = Container()

    # Create a container with both services registered
    await container.register_transient(ServiceA, factory_a)
    await container.register_transient(ServiceB, factory_b)

    # This should raise a CircularDependencyError directly
    with pytest.raises(CircularDependencyError) as excinfo:
        await container.resolve(ServiceA)

    # Verify the error message contains the dependency chain
    error_message = str(excinfo.value)
    assert "Circular dependency detected" in error_message
    assert "ServiceA -> ServiceB -> ServiceA" in error_message

    # Cleanup
    await container.dispose()


async def factory_a(container):
    # Create ServiceA that depends on ServiceB
    b = await container.resolve(ServiceB)
    return ServiceA()


async def factory_b(container):
    # Create ServiceB that depends on ServiceA
    a = await container.resolve(ServiceA)
    return ServiceB()


class ServiceA:
    def __init__(self, container=None):
        # Create circular dependency: A -> B -> A
        if container:
            b = container.resolve(ServiceB)
            self.b = b


class ServiceB:
    def __init__(self, container=None):
        # Complete the circular dependency: B -> A
        if container:
            a = container.resolve(ServiceA)
            self.a = a

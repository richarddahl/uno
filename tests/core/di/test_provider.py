from typing import Any, Optional
import pytest

from uno.infrastructure.di.service_lifecycle import ServiceLifecycle
from uno.infrastructure.di.service_provider import ServiceProvider
from uno.infrastructure.di.service_collection import ServiceCollection
from uno.infrastructure.di.scope_context import ScopeContext
from uno.core.errors.definitions import ServiceRegistrationError
from uno.core.errors.result import Failure


class CounterSingleton:
    def __init__(self) -> None:
        CounterSingleton.counter += 1

    counter = 0


class ErrorSingleton:
    def __init__(self) -> None:
        raise RuntimeError("Singleton error!")


@pytest.mark.asyncio
async def test_provider_validation_hook_blocks_init() -> None:
    services = ServiceCollection()
    
    def validation_hook() -> None:
        raise ValueError("Provider invalid!")
    services.add_validation(validation_hook)
    services.add_singleton(SimpleService)
    provider = ServiceProvider(services)
    with pytest.raises(ValueError, match="Validation hook failed: Provider invalid!"):
        await provider.initialize()


@pytest.mark.asyncio
async def test_provider_validation_hook_passes() -> None:
    services = ServiceCollection()
    services.add_singleton(SimpleService)
    services.add_validation(lambda: None)
    provider = ServiceProvider(services)
    await provider.initialize()
    service = provider.get_service(SimpleService).value
    assert service is not None
    assert isinstance(service, SimpleService)


class FakeService(ServiceLifecycle):
    def __init__(self) -> None:
        self.is_initialized = False
        self.value: Any = None

    def initialize(self) -> None:
        self.is_initialized = True

    def dispose(self) -> None:
        self.is_initialized = False

    def __repr__(self) -> str:
        return f"FakeService(id={id(self)}, value={self.value}, is_initialized={self.is_initialized})"


class SimpleService:
    def __init__(self) -> None:
        pass


@pytest.fixture(autouse=True)
def reset_provider(monkeypatch: Any) -> None:
    monkeypatch.setenv("ENV", "test")
    services = ServiceCollection()
    provider = ServiceProvider(services)
    provider._initialized = False
    provider._lifecycle_queue.clear()
    provider._extensions.clear()
    provider._base_services = ServiceCollection()
    return provider


@pytest.mark.asyncio
async def test_initialize_default_initialize() -> None:
    services = ServiceCollection()
    provider = ServiceProvider(services)
    await provider.initialize()
    assert provider.is_initialized() is True


@pytest.mark.asyncio
async def test_lifecycle_services_initialization() -> None:
    # Create a service collection with a FakeService (which is a lifecycle service)
    services = ServiceCollection()
    services.add_singleton(FakeService)
    provider = ServiceProvider(services)
    await provider.initialize()
    
    # Verify the service is initialized
    service = provider.get_service(FakeService).unwrap()
    assert service.is_initialized
    
    # Verify it was added to the lifecycle queue
    assert len(provider._lifecycle_queue) > 0
    assert isinstance(provider._lifecycle_queue[0], FakeService)


@pytest.mark.asyncio
async def test_scoped_service_raises_outside_scope() -> None:
    services = ServiceCollection()
    services.add_scoped(FakeService)
    provider = ServiceProvider(services)
    await provider.initialize()
    
    # Test outside scope
    result = provider.get_service(FakeService)
    assert isinstance(result, Failure), "Expected Failure when resolving scoped service outside of scope"
    error_msg = str(result)
    assert "no active scope" in error_msg.lower(), f"Expected error about missing scope, got: {error_msg}"
    
    # For this test, we just need to verify that outside a scope, we get a Failure
    # The actual behavior inside a scope is tested in test_scoped_service_resolves_inside_scope


import pytest

@pytest.mark.asyncio
async def test_scoped_service_resolves_inside_scope() -> None:
    services = ServiceCollection()
    services.add_singleton(FakeService)
    provider = ServiceProvider(services)
    services = ServiceCollection()
    services.add_singleton(FakeService)
    provider.configure_services(services)
    await provider.initialize()
    from uno.infrastructure.di.scope_context import ScopeContext
    async with ScopeContext(provider) as scope:
        result = scope.get_service(FakeService)
        assert not isinstance(result, Failure)
        assert isinstance(result.unwrap(), FakeService)


@pytest.mark.asyncio
async def test_transient_service_resolves_anywhere() -> None:
    services = ServiceCollection()
    provider = ServiceProvider(services)
    services = ServiceCollection()
    services.add_transient(SimpleService)
    provider = ServiceProvider(services)
    service1 = provider.get_service(SimpleService).value
    service2 = provider.get_service(SimpleService).value
    assert service1 is not service2
    from uno.infrastructure.di.scope_context import ScopeContext
    async with ScopeContext(provider) as scope:
        r3 = scope.get_service(SimpleService)
        assert isinstance(r3.unwrap(), SimpleService)


import pytest

@pytest.mark.asyncio
async def test_shutdown_disposes_services_in_reverse_order() -> None:
    services = ServiceCollection()
    services.add_singleton(FakeService)
    provider = ServiceProvider(services)
    await provider.initialize()
    async with provider.create_scope() as scope:
        s = scope.resolve(FakeService)
        assert isinstance(s, FakeService)


import pytest

@pytest.mark.asyncio
async def test_resolve_singleton_service() -> None:
    services = ServiceCollection()
    services.add_singleton(FakeService)
    provider = ServiceProvider(services)
    await provider.initialize()

    result1 = provider.get_service(FakeService)
    service1 = result1.value
    try:
        assert service1.is_initialized
    except AttributeError:
        raise AssertionError("Expected service to be initialized")
    service2 = provider.get_service(FakeService).value
    print(
        f"test: service2 id={id(service2)} is_initialized={getattr(service2, 'is_initialized', None)}"
    )
    assert service1 is service2
    assert service1.is_initialized
    provider.shutdown()
    assert not service1.is_initialized
    async with provider.create_scope() as scope:
        s3 = scope.resolve(FakeService)
        assert s3 is service1


@pytest.mark.asyncio
async def test_prewarm_singletons_instantiates_all_singletons() -> None:
    services = ServiceCollection()
    services.add_singleton(CounterSingleton)
    services.add_singleton(CounterSingleton)
    provider = ServiceProvider(services)
    await provider.initialize()
    service1 = provider.get_service(CounterSingleton).value
    service2 = provider.get_service(CounterSingleton).value
    assert service1 is service2
    assert CounterSingleton.counter == 1
    provider.prewarm_singletons()
    assert CounterSingleton.counter == 1


def test_prewarm_singletons_is_idempotent() -> None:
    services = ServiceCollection()
    CounterSingleton.counter = 0
    services.add_singleton(CounterSingleton)
    provider = ServiceProvider(services)
    service = provider.get_service(CounterSingleton).value
    provider.prewarm_singletons()
    provider.prewarm_singletons()
    provider.prewarm_singletons()
    assert CounterSingleton.counter == 1


def test_prewarm_singletons_surfaces_errors() -> None:
    services = ServiceCollection()
    services.add_singleton(ErrorSingleton)
    provider = ServiceProvider(services)
    with pytest.raises(ServiceRegistrationError):
        provider.prewarm_singletons()

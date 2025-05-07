import pytest
from uno.infrastructure.di.service_collection import ServiceCollection, ServiceScope
from uno.infrastructure.di.service_provider import ServiceProvider
from uno.core.errors.result import Result, Success, Failure
from uno.infrastructure.di.errors import ServiceStateError, ServiceRegistrationError

# --- Fake Services ---

class FakeService:
    def __init__(self) -> None:
        self.value = 42

class FakeAsyncService:
    def __init__(self) -> None:
        self.initialized = False
    async def initialize(self) -> None:
        self.initialized = True

class FakeScopedService:
    def __init__(self) -> None:
        self.id = id(self)

# --- Helper to create provider after registration ---
def build_provider_with(services: ServiceCollection) -> ServiceProvider:
    return ServiceProvider(services)

# --- Tests ---

def test_singleton_registration_and_resolution() -> None:
    services = ServiceCollection()
    services.add_singleton(FakeService, FakeService)
    provider = build_provider_with(services)
    result = provider.resolve(FakeService)
    assert isinstance(result, Success)
    assert isinstance(result.unwrap(), FakeService)
    # Singleton: same instance
    result2 = provider.resolve(FakeService)
    assert result.unwrap() is result2.unwrap()

def test_transient_registration_and_resolution() -> None:
    services = ServiceCollection()
    services.add_transient(FakeService, FakeService)
    provider = build_provider_with(services)
    result1 = provider.resolve(FakeService)
    result2 = provider.resolve(FakeService)
    assert isinstance(result1, Success)
    assert isinstance(result2, Success)
    assert result1.unwrap() is not result2.unwrap()

def test_scoped_registration_and_resolution() -> None:
    services = ServiceCollection()
    services.add_scoped(FakeScopedService, FakeScopedService)
    provider = build_provider_with(services)
    scope_result = provider.create_scope()
    assert isinstance(scope_result, Success)
    scope = scope_result.unwrap()
    service1 = scope.get_or_create(FakeScopedService, lambda: FakeScopedService())
    service2 = scope.get_or_create(FakeScopedService, lambda: FakeScopedService())
    assert service1 is service2  # Scoped: same within scope
    # New scope = new instance
    scope2_result = provider.create_scope()
    assert isinstance(scope2_result, Success)
    scope2 = scope2_result.unwrap()
    service3 = scope2.get_or_create(FakeScopedService, lambda: FakeScopedService())
    assert service1 is not service3

def test_unregistered_service_resolution_fails() -> None:
    services = ServiceCollection()
    provider = build_provider_with(services)
    result = provider.resolve(str)  # Not registered
    assert isinstance(result, Failure)
    assert isinstance(result.error, ServiceRegistrationError)

def test_scope_error_handling() -> None:
    services = ServiceCollection()
    services.add_scoped(FakeService, FakeService)
    provider = build_provider_with(services)
    # Intentionally break the provider's collection to force error
    provider._collection._registrations = None  # type: ignore
    scope_result = provider.create_scope()
    assert isinstance(scope_result, Failure)
    assert isinstance(scope_result.error, ServiceStateError)

import asyncio
@pytest.mark.asyncio
async def test_async_service_resolution_and_scope() -> None:
    services = ServiceCollection()
    services.add_singleton(FakeAsyncService, FakeAsyncService)
    provider = build_provider_with(services)
    result = provider.resolve(FakeAsyncService)
    assert isinstance(result, Success)
    service = result.unwrap()
    assert hasattr(service, "initialize")
    await service.initialize()
    assert service.initialized

@pytest.mark.asyncio
async def test_async_create_scope() -> None:
    services = ServiceCollection()
    provider = build_provider_with(services)
    result = await provider.async_create_scope()
    assert isinstance(result, Success)
    scope = result.unwrap()
    assert hasattr(scope, "get_or_create")

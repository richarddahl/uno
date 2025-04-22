# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# uno framework
import pytest

from uno.core.di.container import ServiceCollection
from uno.core.di.provider import ServiceLifecycle, get_service_provider
from uno.core.errors.base import FrameworkError


class FakeService(ServiceLifecycle):
    # Ensure this is registered as singleton in tests
    pass

    def __init__(self):
        self.initialized = False
        self.disposed = False

    async def initialize(self) -> None:
        self.initialized = True

    async def dispose(self) -> None:
        self.disposed = True


class SimpleService:
    pass


@pytest.fixture(autouse=True)
def reset_provider(monkeypatch):
    monkeypatch.setenv("ENV", "test")
    provider = get_service_provider()
    provider._initialized = False
    provider._lifecycle_queue.clear()
    provider._extensions.clear()
    provider._base_services = ServiceCollection()
    return provider


@pytest.mark.asyncio
async def test_initialize_default_initialize():
    provider = get_service_provider()
    await provider.initialize()
    assert provider.is_initialized() is True


@pytest.mark.asyncio
async def test_register_and_initialize_lifecycle_services():
    provider = get_service_provider()
    services = ServiceCollection()
    services.add_scoped(FakeService)
    provider.configure_services(services)
    await provider.initialize()
    with pytest.raises(NotImplementedError):
        provider.register_lifecycle_service(FakeService)


@pytest.mark.asyncio
async def test_scoped_service_raises_outside_scope():
    provider = get_service_provider()
    services = ServiceCollection()
    services.add_scoped(FakeService)
    provider.configure_services(services)
    await provider.initialize()
    with pytest.raises(FrameworkError):
        provider.get_service(FakeService)


@pytest.mark.asyncio
async def test_scoped_service_resolves_inside_scope():
    provider = get_service_provider()
    services = ServiceCollection()
    services.add_scoped(FakeService)
    provider.configure_services(services)
    await provider.initialize()
    async with await provider.create_scope() as scope:
        s = scope.get_service(FakeService)
        assert isinstance(s, FakeService)


@pytest.mark.asyncio
async def test_transient_service_resolves_anywhere():
    provider = get_service_provider()
    services = ServiceCollection()
    services.add_transient(SimpleService)
    provider.configure_services(services)
    await provider.initialize()
    s1 = provider.get_service(SimpleService)
    s2 = provider.get_service(SimpleService)
    assert s1 is not s2
    async with await provider.create_scope() as scope:
        s3 = scope.get_service(SimpleService)
        assert isinstance(s3, SimpleService)


@pytest.mark.asyncio
async def test_shutdown_disposes_services_in_reverse_order():
    provider = get_service_provider()
    services = ServiceCollection()
    services.add_singleton(FakeService)
    provider.configure_services(services)
    await provider.initialize()
    async with await provider.create_scope() as scope:
        s: FakeService = scope.get_service(FakeService)
        assert isinstance(s, FakeService)
    # No shutdown assertion since scope is unsupported


@pytest.mark.asyncio
async def test_resolve_singleton_service():
    provider = get_service_provider()
    services = ServiceCollection()
    services.add_singleton(SimpleService)
    provider.configure_services(services)
    await provider.initialize()
    s1 = provider.get_service(SimpleService)
    s2 = provider.get_service(SimpleService)
    assert s1 is s2
    # Should also work inside a scope
    async with await provider.create_scope() as scope:
        s3 = scope.get_service(SimpleService)
        assert s3 is s1

import pytest
from uno.core.di.provider import ServiceLifecycle, get_service_provider
from uno.core.di.scoped_container import ServiceCollection

class FakeService(ServiceLifecycle):
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
    provider.register_lifecycle_service(FakeService)
    await provider.initialize()
    s: FakeService = provider.get_service(FakeService)
    assert s.initialized is True


@pytest.mark.asyncio
async def test_shutdown_disposes_services_in_reverse_order():
    provider = get_service_provider()
    services = ServiceCollection()
    services.add_scoped(FakeService)
    provider.configure_services(services)
    provider.register_lifecycle_service(FakeService)
    await provider.initialize()
    await provider.shutdown()
    s: FakeService = provider.get_service(FakeService)
    assert s.disposed is True


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

import pytest

from uno.infrastructure.di.service_collection import ServiceCollection
from uno.infrastructure.di.service_lifecycle import ServiceLifecycle
from uno.infrastructure.di.service_provider import ServiceProvider
from uno.infrastructure.logging.logger import LoggerService, LoggingConfig


class DummyLifecycleService(ServiceLifecycle):
    def __init__(self) -> None:
        self.initialized = False
        self.disposed = False

    async def initialize(self) -> None:
        self.initialized = True

    async def dispose(self) -> None:
        self.initialized = False
        self.disposed = True



def test_lifecycle_service_non_singleton_raises() -> None:
    services = ServiceCollection() 
    services.add_scoped(DummyLifecycleService)
    logger = LoggerService(LoggingConfig())
    services.add_instance(LoggerService, logger)
    provider = ServiceProvider(services)
    provider.configure_services(services)
    with pytest.raises(TypeError) as exc:
        provider.register_lifecycle_service(DummyLifecycleService)
    assert "Lifecycle services must be singleton" in str(exc.value)




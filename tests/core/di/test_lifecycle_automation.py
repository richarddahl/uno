import pytest

from uno.infrastructure.di.container import ServiceCollection
from uno.infrastructure.di.provider import ServiceLifecycle, ServiceProvider
from uno.infrastructure.logging.logger import LoggerService, LoggingConfig


class DummyLifecycleService(ServiceLifecycle):
    def __init__(self):
        self.initialized = False
        self.disposed = False

    async def initialize(self):
        self.initialized = True

    async def dispose(self):
        self.disposed = True


def test_lifecycle_service_auto_queued_and_singleton():
    services = ServiceCollection()
    services.add_singleton(DummyLifecycleService)
    logger = LoggerService(LoggingConfig())
    provider = ServiceProvider(logger)
    provider.configure_services(services)
    # Should not raise
    provider._auto_register_lifecycle_services()
    assert DummyLifecycleService in provider._lifecycle_queue


def test_lifecycle_service_non_singleton_raises():
    services = ServiceCollection()
    services.add_scoped(DummyLifecycleService)
    logger = LoggerService(LoggingConfig())
    provider = ServiceProvider(logger)
    provider.configure_services(services)
    with pytest.raises(TypeError) as exc:
        provider._auto_register_lifecycle_services()
    assert "must be registered as singleton" in str(exc.value)


def test_lifecycle_queue_removes_stale_entries():
    services = ServiceCollection()
    services.add_singleton(DummyLifecycleService)
    logger = LoggerService(LoggingConfig())
    provider = ServiceProvider(logger)
    provider.configure_services(services)
    provider._lifecycle_queue.append(DummyLifecycleService)
    # Remove service registration
    services._registrations.pop(DummyLifecycleService)
    provider._auto_register_lifecycle_services()
    assert DummyLifecycleService not in provider._lifecycle_queue

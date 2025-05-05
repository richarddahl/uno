import pytest

from uno.infrastructure.di.service_collection import ServiceCollection
from uno.infrastructure.di.provider import ServiceProvider
from uno.infrastructure.logging.logger import LoggerService, LoggingConfig


class MyDep:
    def __init__(self) -> None:
        pass


class MyService:
    def __init__(self, dep: MyDep):
        self.dep = dep


@pytest.mark.asyncio
async def test_resolution_cache_and_lazy_loading():
    services = ServiceCollection()
    services.add_singleton(MyDep)
    services.add_singleton(MyService, lambda: MyService(MyDep()))
    services.add_singleton(MyService)
    logger = LoggerService(LoggingConfig())
    provider = ServiceProvider(logger)
    provider.configure_services(services)
    await provider.initialize()
    # First resolution (should populate cache)
    s1 = provider.get_service(MyService)
    assert s1.is_success
    instance1 = s1.value
    assert isinstance(instance1, MyService)
    assert isinstance(instance1.dep, MyDep)
    # Second resolution (should use cache, same singleton instance)
    s2 = provider.get_service(MyService)
    assert s2.is_success
    instance2 = s2.value
    assert instance1 is instance2
    # Underlying dependency is also singleton
    assert instance1.dep is provider.get_service(MyDep).value

    # Check that the singleton cache is used (ServiceResolver._singletons)
    resolver = provider._resolver
    assert MyService in resolver._singletons
    assert resolver._singletons[MyService] is instance1
    assert MyDep in resolver._singletons
    assert resolver._singletons[MyDep] is instance1.dep

    # Test that re-registering invalidates the cache
    class MyService2(MyService):
        pass

    services.add_singleton(MyService, MyService2)
    logger2 = LoggerService(LoggingConfig())
    provider2 = ServiceProvider(logger2)
    provider2.configure_services(services)
    await provider2.initialize()
    s3 = provider2.get_service(MyService)
    assert s3.is_success
    assert isinstance(s3.value, MyService2)


@pytest.mark.asyncio
async def test_lazy_loading():
    """
    Uno DI eagerly instantiates singleton services at provider initialization.
    This test asserts that the singleton is created immediately after initialization,
    not lazily on first access.
    """
    services = ServiceCollection()
    instantiation_counter = {"count": 0}

    class LazyDep:
        def __init__(self) -> None:
            instantiation_counter["count"] += 1

    services.add_singleton(LazyDep)
    logger = LoggerService(LoggingConfig())
    provider = ServiceProvider(logger)
    provider.configure_services(services)
    await provider.initialize()
    # Eager instantiation: singleton is created at initialization
    assert instantiation_counter["count"] == 1
    s = provider.get_service(LazyDep)
    assert s.is_success
    assert isinstance(s.value, LazyDep)
    assert instantiation_counter["count"] == 1
    # Subsequent gets do not re-instantiate
    s2 = provider.get_service(LazyDep)
    assert s2.is_success
    assert s2.value is s.value
    assert instantiation_counter["count"] == 1

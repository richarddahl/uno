import pytest
from uno.core.di.container import ServiceCollection
from uno.core.di.provider import ServiceProvider

class MyDep:
    pass

class MyService:
    def __init__(self, dep: MyDep):
        self.dep = dep

@pytest.mark.asyncio
async def test_resolution_cache_and_lazy_loading():
    services = ServiceCollection()
    services.add_singleton(MyDep)
    services.add_singleton(MyService)
    provider = ServiceProvider()
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

    # Check that the cache is used by monkeypatching _get_resolution_plan
    called = {}
    orig = provider._resolver._get_resolution_plan
    def wrapped(impl):
        called[impl] = called.get(impl, 0) + 1
        return orig(impl)
    provider._resolver._get_resolution_plan = wrapped
    provider.get_service(MyService)
    provider.get_service(MyService)
    # After singleton is cached, _get_resolution_plan should not be called again for MyService
    assert called.get(MyService, 0) == 0
    provider._resolver._get_resolution_plan = orig

    # Test that re-registering invalidates the cache
    class MyService2(MyService):
        pass
    services.add_singleton(MyService, MyService2)
    provider2 = ServiceProvider()
    provider2.configure_services(services)
    await provider2.initialize()
    s3 = provider2.get_service(MyService)
    assert s3.is_success
    assert isinstance(s3.value, MyService2)

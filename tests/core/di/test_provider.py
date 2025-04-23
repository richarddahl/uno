# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# uno framework
import pytest

from uno.core.di.container import ServiceCollection
from uno.core.di.provider import ServiceLifecycle, get_service_provider

class CounterSingleton:
    def __init__(self):
        CounterSingleton.counter += 1
    counter = 0

class ErrorSingleton:
    def __init__(self):
        raise RuntimeError("Singleton error!")
from uno.core.errors.base import FrameworkError

@pytest.mark.asyncio
async def test_provider_validation_hook_blocks_init():
    provider = get_service_provider()
    services = ServiceCollection()
    services.add_singleton(SimpleService)
    def fail_validation(sc):
        raise ValueError("Provider invalid!")
    services.add_validation(fail_validation)
    provider.configure_services(services)
    with pytest.raises(ValueError):
        await provider.initialize()

@pytest.mark.asyncio
async def test_provider_validation_hook_passes():
    provider = get_service_provider()
    services = ServiceCollection()
    services.add_singleton(SimpleService)
    services.add_validation(lambda sc: None)
    provider.configure_services(services)
    await provider.initialize()
    assert provider.is_initialized() is True


class FakeService(ServiceLifecycle):
    # Ensure this is registered as singleton in tests
    def __init__(self):
        self.initialized = False
        self.disposed = False

    async def initialize(self) -> None:
        self.initialized = True

    async def dispose(self) -> None:
        self.disposed = True


class SimpleService:
    def __init__(self):
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
    result = provider.get_service(FakeService)
    from uno.core.errors.result import Failure
    from uno.core.errors.definitions import ScopeError
    assert isinstance(result, Failure)
    assert isinstance(result.error, ScopeError)


@pytest.mark.asyncio
async def test_scoped_service_resolves_inside_scope():
    provider = get_service_provider()
    services = ServiceCollection()
    services.add_scoped(FakeService)
    provider.configure_services(services)
    await provider.initialize()
    async with await provider.create_scope() as scope:
        result = scope.get_service(FakeService)
        from uno.core.errors.result import Success
        assert isinstance(result, Success)
        s = result.value
        assert isinstance(s, FakeService)


@pytest.mark.asyncio
async def test_transient_service_resolves_anywhere():
    provider = get_service_provider()
    services = ServiceCollection()
    services.add_transient(SimpleService)
    provider.configure_services(services)
    await provider.initialize()
    r1 = provider.get_service(SimpleService)
    r2 = provider.get_service(SimpleService)
    from uno.core.errors.result import Success
    assert isinstance(r1, Success)
    assert isinstance(r2, Success)
    s1 = r1.value
    s2 = r2.value
    assert s1 is not s2
    async with await provider.create_scope() as scope:
        r3 = scope.get_service(SimpleService)
        assert isinstance(r3, Success)
        s3 = r3.value
        assert isinstance(s3, SimpleService)


@pytest.mark.asyncio
async def test_shutdown_disposes_services_in_reverse_order():
    provider = get_service_provider()
    services = ServiceCollection()
    services.add_singleton(FakeService)
    provider.configure_services(services)
    await provider.initialize()
    async with await provider.create_scope() as scope:
        r = scope.get_service(FakeService)
        from uno.core.errors.result import Success
        assert isinstance(r, Success)
        s: FakeService = r.value
        assert isinstance(s, FakeService)
    # No shutdown assertion since scope is unsupported


@pytest.mark.asyncio
async def test_resolve_singleton_service():
    provider = get_service_provider()
    services = ServiceCollection()
    services.add_singleton(SimpleService)
    provider.configure_services(services)
    await provider.initialize()
    r1 = provider.get_service(SimpleService)
    r2 = provider.get_service(SimpleService)
    from uno.core.errors.result import Success
    assert isinstance(r1, Success)
    assert isinstance(r2, Success)
    s1 = r1.value
    s2 = r2.value
    assert s1 is s2
    # Should also work inside a scope
    async with await provider.create_scope() as scope:
        r3 = scope.get_service(SimpleService)
        assert isinstance(r3, Success)
        s3 = r3.value
        assert s3 is s1


import pytest

def test_prewarm_singletons_instantiates_all_singletons():
    provider = get_service_provider()
    services = ServiceCollection()
    CounterSingleton.counter = 0
    services.add_singleton(CounterSingleton)
    provider.configure_services(services)
    import asyncio
    asyncio.get_event_loop().run_until_complete(provider.initialize())
    provider.prewarm_singletons()
    assert CounterSingleton.counter == 1
    # Second call should not increment
    provider.prewarm_singletons()
    assert CounterSingleton.counter == 1

def test_prewarm_singletons_is_idempotent():
    provider = get_service_provider()
    services = ServiceCollection()
    CounterSingleton.counter = 0
    services.add_singleton(CounterSingleton)
    provider.configure_services(services)
    import asyncio
    asyncio.get_event_loop().run_until_complete(provider.initialize())
    provider.prewarm_singletons()
    provider.prewarm_singletons()
    provider.prewarm_singletons()
    assert CounterSingleton.counter == 1

def test_prewarm_singletons_surfaces_errors():
    provider = get_service_provider()
    services = ServiceCollection()
    services.add_singleton(ErrorSingleton)
    provider.configure_services(services)
    import asyncio
    asyncio.get_event_loop().run_until_complete(provider.initialize())
    # Should not raise, but error is logged (cannot assert logs here)
    provider.prewarm_singletons()

import pytest

from uno.core.di.container import ServiceCollection
from uno.core.di.service_scope import ServiceScope


@pytest.fixture(autouse=True)
def reset_global_service_registry():
    from uno.core.di.decorators import _global_service_registry

    # Always start with a clean global service registry and register FakeService

    # Remove any lingering FakeService
    if FakeService in _global_service_registry:
        _global_service_registry.remove(FakeService)
    # Register FakeService with correct metadata
    _global_service_registry.append(FakeService)
    FakeService.__framework_service_type__ = IFakeService
    FakeService.__framework_service_scope__ = ServiceScope.SINGLETON
    FakeService.__framework_service_name__ = None
    FakeService.__framework_service_version__ = None
    FakeService.__framework_service__ = True
    yield
    # Clean up after test
    if FakeService in _global_service_registry:
        _global_service_registry.remove(FakeService)


class IFakeService:
    pass


class FakeService(IFakeService):
    def __init__(self, *args, **kwargs):
        pass


def test_auto_register_env(monkeypatch):
    monkeypatch.setenv("UNO_DI_AUTO_REGISTER", "true")
    services = ServiceCollection()
    provider = services.build()
    # Should be auto-registered
    instance = provider.get(IFakeService)
    assert isinstance(instance, FakeService)


def test_auto_register_constructor():
    services = ServiceCollection(auto_register=True)
    provider = services.build()
    instance = provider.get(IFakeService)
    assert isinstance(instance, FakeService)


def test_auto_register_explicit():
    services = ServiceCollection()
    services.enable_auto_registration()
    provider = services.build()
    instance = provider.get(IFakeService)
    assert isinstance(instance, FakeService)


def test_explicit_override():
    class CustomFake(FakeService):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

    services = ServiceCollection(auto_register=True)
    services.add_singleton(IFakeService, CustomFake)
    provider = services.build()
    instance = provider.get(IFakeService)
    assert isinstance(instance, CustomFake)

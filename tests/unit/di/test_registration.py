import pytest
from uno.di.registration import ServiceRegistration
from uno.di.protocols import ContainerProtocol
from uno.di.container import Container

class FakeService:
    pass

@pytest.mark.asyncio
async def test_service_registration_properties():
    reg = ServiceRegistration(FakeService, FakeService, "singleton")
    assert reg.interface is FakeService
    assert reg.implementation is FakeService
    assert reg.lifetime == "singleton"

@pytest.mark.asyncio
async def test_register_logging_services_type_safety():
    # This test will pass once type safety is enforced for logger registration
    container = Container()
    from uno.di.registration import register_logging_services
    register_logging_services(container)
    # Should be able to resolve LoggerScopeProtocol and LoggerFactoryProtocol after registration
    from uno.logging.scope import LoggerScopeProtocol
    from uno.logging.factory import LoggerFactoryProtocol
    assert hasattr(container, "_registrations")
    assert LoggerScopeProtocol in container._registrations
    assert LoggerFactoryProtocol in container._registrations

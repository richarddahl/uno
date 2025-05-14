import pytest
from uno.di.container import Container
from uno.di.registration import ServiceRegistration


class FakeService:
    pass


@pytest.mark.asyncio
async def test_service_registration_properties():
    # Use ServiceRegistration instead of DIServiceNotFoundError
    reg = ServiceRegistration(FakeService, FakeService, "singleton")
    assert reg.interface is FakeService
    assert reg.implementation is FakeService
    assert reg.lifetime == "singleton"


@pytest.mark.asyncio
async def test_register_services():
    # Properly instantiate a container (not awaitable)
    container = Container()

    # Register a test service
    await container.register_singleton(FakeService, FakeService)

    # Verify the registration
    assert hasattr(container, "_registrations")
    assert FakeService in container._registrations

    # Test accessing registrations through API
    reg_keys = await container.get_registration_keys()
    assert "FakeService" in reg_keys

    # Clean up
    await container.dispose()

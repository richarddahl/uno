import asyncio
import pytest
from uno.infrastructure.di.service_lifecycle import ServiceLifecycle, T
from uno.infrastructure.di.service_collection import ServiceCollection
from uno.infrastructure.di.service_provider import ServiceProvider
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .test_forgotten_service import ForgottenService


class ForgottenService(ServiceLifecycle["ForgottenService"]):
    def __init__(self) -> None:
        self._initialized = False
        self._disposed = False

    @property
    def initialized(self) -> bool:
        return self._initialized

    @property
    def disposed(self) -> bool:
        return self._disposed

    async def initialize(self) -> None:
        await asyncio.sleep(0.01)
        self._initialized = True

    async def dispose(self) -> None:
        self._disposed = True


@pytest.mark.asyncio
async def test_forgotten_service() -> None:
    services = ServiceCollection()
    services.add_singleton(ForgottenService)
    provider = ServiceProvider(services)
    provider.register_lifecycle_service(ForgottenService)
    await provider.initialize()

    result = provider.get_service(ForgottenService)
    from uno.core.errors.result import Success
    assert isinstance(result, Success)
    instance = result.value
    assert hasattr(instance, "initialized") and instance.initialized
    assert hasattr(instance, "disposed") and not instance.disposed

    await provider.shutdown_async()
    assert hasattr(instance, "disposed") and instance.disposed

"""
Tests for Uno DI: async lifecycle and initialization
"""

import asyncio
import pytest
from uno.infrastructure.di.service_collection import ServiceCollection
from uno.infrastructure.di.service_provider import ServiceProvider
from uno.infrastructure.di.service_lifecycle import ServiceLifecycle, T
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .test_di_async_lifecycle import AsyncService


class AsyncService(ServiceLifecycle["AsyncService"]):
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
async def test_async_lifecycle() -> None:
    services = ServiceCollection()
    services.add_singleton(AsyncService)
    provider = ServiceProvider(services)
    provider.register_lifecycle_service(AsyncService)
    await provider.initialize()

    result = provider.get_service(AsyncService)

    from uno.core.errors.result import Success

    assert isinstance(result, Success)
    instance = result.value
    assert hasattr(instance, "initialized") and instance.initialized
    assert hasattr(instance, "disposed") and not instance.disposed

    await provider.shutdown_async()
    assert hasattr(instance, "disposed") and instance.disposed

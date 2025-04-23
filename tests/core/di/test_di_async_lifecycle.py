"""
Tests for Uno DI: async lifecycle and initialization
"""
import asyncio
import pytest
from uno.core.di.container import ServiceCollection
from uno.core.di.test_helpers import TestDI

class AsyncService:
    def __init__(self):
        self.initialized = False

    async def initialize(self):
        await asyncio.sleep(0.01)
        self.initialized = True

@pytest.mark.asyncio
async def test_async_lifecycle():
    provider = TestDI.create_test_provider()
    services = ServiceCollection()
    services.add_singleton(AsyncService)
    provider.configure_services(services)
    await provider.initialize()
    result = provider.get_service(AsyncService)
    from uno.core.errors.result import Success
    assert isinstance(result, Success)
    instance = result.value
    await instance.initialize()
    assert hasattr(instance, 'initialized') and instance.initialized

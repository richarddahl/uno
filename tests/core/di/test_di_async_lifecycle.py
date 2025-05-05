"""
Tests for Uno DI: async lifecycle and initialization
"""

import asyncio
import pytest
from uno.infrastructure.di.service_collection import ServiceCollection
from uno.infrastructure.di.provider import ServiceProvider, ServiceLifecycle


class AsyncService(ServiceLifecycle):
    def __init__(self):
        self.initialized = False
        self.disposed = False

    async def initialize(self):
        await asyncio.sleep(0.01)
        self.initialized = True

    async def dispose(self):
        self.disposed = True


@pytest.mark.asyncio
async def test_async_lifecycle():
    from uno.infrastructure.logging.logger import LoggerService, LoggingConfig

    logger = LoggerService(LoggingConfig())
    provider = ServiceProvider(logger)
    provider._base_services.add_singleton(AsyncService)
    provider.register_lifecycle_service(AsyncService)
    await provider.initialize()

    result = provider.get_service(AsyncService)

    from uno.core.errors.result import Success

    assert isinstance(result, Success)
    instance = result.value
    assert hasattr(instance, "initialized") and instance.initialized
    assert hasattr(instance, "disposed") and not instance.disposed

    await provider.shutdown()
    assert hasattr(instance, "disposed") and instance.disposed

    # SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
    # SPDX-License-Identifier: MIT
    # uno framework
    # See docs/di_testing.md for DI test patterns and best practices

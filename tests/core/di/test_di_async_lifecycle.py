"""
Tests for Uno DI: async lifecycle and initialization
"""
import asyncio

import pytest

from uno.core.di.container import ServiceCollection


class AsyncService:
    def __init__(self):
        self.initialized = False

    async def initialize(self):
        await asyncio.sleep(0.01)
        self.initialized = True

@pytest.mark.asyncio
async def test_async_lifecycle(di_provider):
   # SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# uno framework
# See docs/di_testing.md for DI test patterns and best practices

    services = ServiceCollection()
    services.add_singleton(AsyncService)
    di_provider.configure_services(services)
    await di_provider.initialize()
    result = di_provider.get_service(AsyncService)
    from uno.core.errors.result import Success
    assert isinstance(result, Success)
    instance = result.value
    await instance.initialize()
    assert hasattr(instance, 'initialized') and instance.initialized

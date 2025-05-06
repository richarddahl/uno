# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# uno framework
# See docs/di_testing.md for DI test patterns and best practices

import pytest
from uno.infrastructure.di.service_provider import ServiceProvider
from uno.infrastructure.di.service_collection import ServiceCollection
from tests.core.di.di_helper import DIHelper

from uno.infrastructure.logging.logger import LoggerService, LoggingConfig
from uno.infrastructure.di.service_lifecycle import ServiceLifecycle


@pytest.fixture
def di_provider() -> ServiceProvider:
    services = ServiceCollection()
    services.add_instance(LoggerService, LoggerService(LoggingConfig()))
    provider = ServiceProvider(services)
    return provider


# Example: Isolated provider per test
def test_example_isolated(di_provider: ServiceProvider) -> None:
    # di_provider is a fresh ServiceProvider for this test
    ...


# Example: Temporary override (sync)
def test_example_override(di_provider: ServiceProvider) -> None:
    mock = object()
    with DIHelper.override_service(di_provider, str, mock):
        # str resolves to mock within this block
        ...


# Example: Batch override
def test_example_batch_override(di_provider: ServiceProvider) -> None:
    overrides = {str: object(), int: 123}
    with DIHelper.batch_override_services(di_provider, overrides):
        ...


# Example: Register mock
def test_example_register_mock(di_provider: ServiceProvider) -> None:
    DIHelper.register_mock(di_provider, str, "mocked string")
    ...


# Example: Async override
@pytest.mark.asyncio
async def test_example_async_override(di_provider: ServiceProvider) -> None:
    mock = object()
    async with DIHelper.async_override_service(di_provider, str, mock):
        ...


# Example: Teardown (manual)
@pytest.mark.asyncio
async def test_example_teardown(di_provider: ServiceProvider) -> None:
    await di_provider.shutdown()
    ...


# Example: Reset DI state (if using globals)
def test_example_reset_state() -> None:
    DIHelper.reset_di_state()
    ...

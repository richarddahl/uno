# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# uno framework
import pytest
from uno.core.di.provider import ServiceProvider
from uno.core.di.test_helpers import TestDI

class Dummy:
    def __init__(self):
        self.value = 1

class Dummy2:
    def __init__(self):
        self.value = 2

def test_create_test_provider_isolated():
    p1 = TestDI.create_test_provider()
    p2 = TestDI.create_test_provider()
    assert isinstance(p1, ServiceProvider)
    assert p1 is not p2
    assert not p1._initialized

def test_initialize_test_provider_sets_env(monkeypatch):
    monkeypatch.delenv("ENV", raising=False)
    provider = TestDI.initialize_test_provider(env="custom-env")
    assert isinstance(provider, ServiceProvider)
    assert provider._base_services is not None
    assert provider._initialized is False
    assert provider._base_services._instances
    assert provider._base_services._instances.get is not None
    assert provider._base_services._registrations is not None
    assert provider._base_services._registrations.get is not None
    assert provider._base_services._instances
    assert provider._base_services._instances.get is not None
    assert provider._base_services._registrations is not None
    assert provider._base_services._registrations.get is not None
    assert provider._base_services._instances
    assert provider._base_services._instances.get is not None
    assert provider._base_services._registrations is not None
    assert provider._base_services._registrations.get is not None
    assert provider._base_services._instances
    assert provider._base_services._instances.get is not None
    assert provider._base_services._registrations is not None
    assert provider._base_services._registrations.get is not None
    assert provider._base_services._instances
    assert provider._base_services._instances.get is not None
    assert provider._base_services._registrations is not None
    assert provider._base_services._registrations.get is not None

@pytest.mark.asyncio
async def test_setup_test_services_and_override_service():
    provider = await TestDI.setup_test_services()
    dummy = Dummy()
    # Register mock
    TestDI.register_mock(provider, Dummy, dummy)
    assert provider._base_services._instances[Dummy] is dummy
    # Test override_service context manager
    dummy2 = Dummy2()
    with TestDI.override_service(provider, Dummy, dummy2):
        assert provider._base_services._instances[Dummy] is dummy2
    # After context, should revert to dummy
    assert provider._base_services._instances[Dummy] is dummy

import pytest
import asyncio

def test_reset_di_state():
    # Should not raise
    TestDI.reset_di_state()

@pytest.mark.asyncio
async def test_async_override_service():
    provider = TestDI.create_test_provider()
    class Dummy:
        def __init__(self):
            self.value = 1
    dummy1 = Dummy()
    dummy2 = Dummy()
    TestDI.register_mock(provider, Dummy, dummy1)
    assert provider._base_services._instances[Dummy] is dummy1
    async with TestDI.async_override_service(provider, Dummy, dummy2):
        assert provider._base_services._instances[Dummy] is dummy2
    assert provider._base_services._instances[Dummy] is dummy1

@pytest.fixture
def di_provider():
    provider = TestDI.create_test_provider()
    yield provider
    TestDI.reset_di_state()

def test_di_provider_fixture(di_provider):
    class Dummy:
        pass
    dummy = Dummy()
    TestDI.register_mock(di_provider, Dummy, dummy)
    assert di_provider._base_services._instances[Dummy] is dummy

# ---
# Best Practices and Usage Examples
#
# 1. Use TestDI.create_test_provider() or the di_provider fixture for isolated DI setup.
# 2. Use TestDI.override_service or async_override_service for temporary overrides.
# 3. Use TestDI.register_mock to inject mocks/doubles.
# 4. Always reset DI state between tests.
#
# Example (sync):
#     with TestDI.override_service(provider, MyService, my_mock):
#         ...
# Example (async):
#     async with TestDI.async_override_service(provider, MyService, my_mock):
#         ...
# Example (pytest fixture):
#     def test_my_di(di_provider):
#         ...

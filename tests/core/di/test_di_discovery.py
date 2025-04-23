# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# uno framework

import types

from uno.core.di.container import ServiceScope
from uno.core.di.decorators import framework_service
from uno.core.di.discovery import discover_services, get_class_metadata


# Dummy service for testing
def make_dummy_service():
    @framework_service(scope=ServiceScope.SINGLETON)
    class DummyService:
        def __init__(self):
            pass
        def hello(self):
            return "world"

    DummyService.__module__ = "fake_module"

    return DummyService


def test_framework_service_decorator_sets_attributes():
    dummy_service = make_dummy_service()
    meta = get_class_metadata(dummy_service)
    assert meta["is_service"] is True
    assert meta["scope"] == ServiceScope.SINGLETON
    assert meta["service_type"] == dummy_service


def test_discover_services_registers_service():
    dummy_service = make_dummy_service()
    # Create a fake module and inject the service
    module = types.ModuleType("fake_module")
    module.DummyService = dummy_service
    # Patch find_modules to return our fake module name
    import uno.core.di.discovery as discovery_mod

    discovery_mod.importlib.import_module = lambda name: module
    discovery_mod.find_modules = lambda name: ["fake_module"]
    # Run discovery
    services = discover_services("fake_module")
    # The service should be registered as singleton
    resolver = services.build()
    result = resolver.resolve(dummy_service)
    from uno.core.errors.result import Success
    assert isinstance(result, Success)
    instance = result.value
    assert isinstance(instance, dummy_service)
    assert instance.hello() == "world"

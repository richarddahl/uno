# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# uno framework
# See docs/di_testing.md for DI test patterns and best practices


def test_di_public_api_surface():
    from uno.infrastructure import di
    # Only these should be public
    assert hasattr(di, "ServiceCollection")
    assert hasattr(di, "ServiceProvider")
    assert hasattr(di, "ServiceLifecycle")
    assert hasattr(di, "ServiceScope")
    assert hasattr(di, "get_service_provider")
    assert hasattr(di, "initialize_services")
    assert hasattr(di, "shutdown_services")
    # Internal/private should not be in __all__
    assert not hasattr(di, "_ServiceResolver")
    # ServiceRegistration is available but not in __all__
    assert hasattr(di, "ServiceRegistration")
    # Only public APIs should be in __all__
    assert set(di.__all__) == {
        "ServiceCollection",
        "ServiceLifecycle",
        "ServiceProvider",
        "ServiceScope",
        "get_service_provider",
        "initialize_services",
        "shutdown_services",
    }

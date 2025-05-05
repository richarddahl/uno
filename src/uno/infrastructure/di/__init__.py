# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# uno framework

from typing import TypeVar

# Public API symbols for uno.infrastructure.di
from uno.infrastructure.di.service_collection import ServiceCollection
from uno.infrastructure.di.resolver import ServiceResolver
from uno.infrastructure.di.service_registration import ServiceRegistration
from uno.infrastructure.di.service_scope import ServiceScope
from uno.infrastructure.di.service_provider import (
    ServiceProvider,
    get_service_provider,
    initialize_services,
    shutdown_services,
)

# Forward reference for ServiceLifecycle
ServiceLifecycle = "ServiceLifecycle[ProviderT]"

ProviderT = TypeVar("ProviderT")

"""
Scoped dependency injection container for Uno framework.

Public API:
- ServiceCollection: Main API for registering services
- ServiceScope: Enum for service lifetimes
- Inject: Marker for use with Annotated to specify named/optional dependencies.
- ServiceProvider: Interface for resolving services.
- ServiceLifecycle: Protocol for services with startup/shutdown hooks.
- get_service_provider: Function to get the root service provider.
- initialize_services: Function to trigger eager initialization.
- shutdown_services: Function to call shutdown hooks on services.

Internal/advanced classes are not exposed here.
"""


__all__ = [
    "ServiceCollection",
    "ServiceLifecycle",
    "ServiceProvider",
    "ServiceRegistration",
    "ServiceResolver",
    "ServiceScope",
    "get_service_provider",
    "initialize_services",
    "shutdown_services",
]


def __getattr__(name: str) -> object:
    # Check if the name exists in the module's explicitly exported symbols
    # or is intended to be public (e.g., not starting with an underscore
    # if __all__ is not rigorously maintained).
    # For simplicity here, we rely on globals() which includes imports.
    if name in globals() and (name in __all__ or not name.startswith("_")):
        return globals()[name]
    else:
        # Raise AttributeError for non-existent attributes to work correctly
        # with hasattr() and other introspection tools.
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

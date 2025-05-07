# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# uno framework

from __future__ import annotations
from typing import TypeVar

# Public API symbols for uno.infrastructure.di
from uno.infrastructure.di.service_collection import ServiceCollection
from uno.infrastructure.di.service_scope import ServiceScope, Scope
from uno.infrastructure.di.service_provider import ServiceProvider, ServiceResolver
from uno.infrastructure.di.service_lifecycle import ServiceLifecycle
from uno.infrastructure.di.decorators import service, singleton, scoped, transient

ProviderT = TypeVar("ProviderT")

"""
Core DI functionality for Uno framework.

This module provides the core dependency injection (DI) functionality for the Uno framework.
It includes service registration, resolution, and lifecycle management.

Note: This module enforces strict DI - no global state or service locators are allowed.
All dependencies must be passed explicitly from the composition root.

Public API:
- ServiceCollection: Main API for registering services
- ServiceScope: Enum for service lifetimes
- ServiceProvider: Interface for resolving services
- ServiceLifecycle: Protocol for services with startup/shutdown hooks
- Scope: Context manager for scoped service resolution
- service, singleton, scoped, transient: Decorators for service registration
"""

__all__ = [
    "ServiceCollection",
    "ServiceScope",
    "ServiceProvider",
    "ServiceResolver",
    "ServiceLifecycle",
    "Scope",
    "service",
    "singleton",
    "scoped",
    "transient",
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

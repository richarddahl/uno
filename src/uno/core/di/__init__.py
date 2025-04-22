# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# uno framework
"""
Dependencies module for Uno framework.

This module provides a modern dependency injection system
to improve testability, maintainability, and decoupling of components.

The module offers a decorator-based approach to dependency management
with proper scope handling and automatic discovery of injectable services.
"""

"""
Modern dependency injection entry point for Uno framework.

Exports only the canonical ServiceProvider-based DI system and related types.
"""
from uno.core.di.container import (
    ServiceCollection,
    ServiceResolver,
    ServiceScope,
    ServiceRegistration,
)
from uno.core.di.provider import (
    ServiceLifecycle,
    ServiceProvider,
    get_service_provider,
    initialize_services,
    shutdown_services,
)

__all__ = [
    "ServiceCollection",
    "ServiceResolver",
    "ServiceScope",
    "ServiceRegistration",
    "ServiceLifecycle",
    "ServiceProvider",
    "get_service_provider",
    "initialize_services",
    "shutdown_services",
]

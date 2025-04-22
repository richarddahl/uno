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

# New modern DI system
from uno.core.di.container import (
    ServiceCollection,
    ServiceResolver,
    ServiceScope,
    create_async_scope,
    create_scope,
    get_service,
)
from uno.core.di.provider import (
    ServiceLifecycle,
    ServiceProvider,
    get_service_provider,
    shutdown_services,
)
from uno.core.di.provider import (
    initialize_services as initialize_modern_services,
)

__all__ = [
    "ServiceCollection",
    "ServiceLifecycle",
    "ServiceProvider",
    "ServiceResolver",
    "ServiceScope",
    "create_async_scope",
    "create_scope",
    "get_service",
    "get_service_provider",
    "initialize_modern_services",
    "shutdown_services",
]

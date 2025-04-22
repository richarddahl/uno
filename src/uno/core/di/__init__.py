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

from uno.core.di.container import (
    ServiceCollection,
    ServiceRegistration,
    ServiceScope,
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
    "ServiceLifecycle",
    "ServiceProvider",
    "ServiceRegistration",
    "ServiceScope",
    "get_service_provider",
    "initialize_services",
    "shutdown_services",
]

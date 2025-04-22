# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# uno framework
"""
Dependencies module for Uno framework.

This module provides a modern dependency injection system
to improve testability, maintainability, and decoupling of components.

The module offers a decorator-based approach to dependency management
with proper scope handling and automatic discovery of injectable services.

API Clarity:
- Only the symbols in __all__ are considered public and stable for end-users.
- Internal helpers/classes (e.g., _ServiceResolver, ServiceRegistration) are for advanced/extensibility use only and are NOT considered public API.
- For performance tuning (such as prewarming singletons), see ServiceProvider.prewarm_singletons().
- For advanced usage and performance notes, see the documentation in provider.py and container.py.
"""

# UNO DI Public API: Only the symbols in __all__ are considered stable/public.
# Internal helpers/classes (e.g., _ServiceResolver, ServiceRegistration) are not for typical end-user code.
# ServiceRegistration is imported for advanced/extensibility use, but not included in __all__.

from uno.core.di.container import (
    ServiceCollection,
    ServiceRegistration,  # advanced/extensibility only; not public API
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
    "ServiceScope",
    "get_service_provider",
    "initialize_services",
    "shutdown_services",
]

"""
Decorators for Uno DI system.

Provides @framework_service and related decorators to mark classes for DI service discovery.
"""

from collections.abc import Callable
from typing import Any

from uno.core.di.container import ServiceScope

_global_service_registry = []


def framework_service(
    service_type: type[Any] | None = None,
    scope: ServiceScope | None = None,
    name: str | None = None,
    tags: list[str] | None = None,
    version: str | None = None,
) -> Callable[[type[Any]], type[Any]]:
    """
    Decorator to mark a class as a DI service with optional metadata.

    Args:
        service_type: Optional explicit service type (interface/base class)
        scope: Optional service scope (e.g., ServiceScope.SINGLETON)
        name: Optional service name for named injection
        tags: Optional list of tags for expressive patterns
        version: Optional version string
    Returns:
        The decorated class, marked for DI service discovery.
    """

    def decorator(cls: type[Any]) -> type[Any]:
        cls.__framework_service__ = True
        if service_type:
            cls.__framework_service_type__ = service_type
        if scope:
            cls.__framework_service_scope__ = scope
        if name:
            cls.__framework_service_name__ = name
        if tags:
            cls.__framework_service_tags__ = tags
        if version:
            cls.__framework_service_version__ = version
        _global_service_registry.append(cls)
        return cls

    return decorator

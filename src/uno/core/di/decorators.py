"""
Decorators for Uno DI system.

Provides @framework_service and related decorators to mark classes for DI service discovery.
"""


from collections.abc import Callable
from typing import Any

from .container import ServiceScope


def framework_service(
    service_type: type[Any] | None = None,
    scope: ServiceScope | None = None
) -> Callable[[type[Any]], type[Any]]:
    """
    Decorator to mark a class as a DI service.

    Args:
        service_type: Optional explicit service type (interface/base class)
        scope: Optional service scope (e.g., ServiceScope.SINGLETON)
    Returns:
        The decorated class, marked for DI service discovery.
    """
    def decorator(cls: type[Any]) -> type[Any]:
        """Marks the class for DI service discovery."""
        cls.__framework_service__ = True
        if service_type:
            cls.__framework_service_type__ = service_type
        if scope:
            cls.__framework_service_scope__ = scope
        return cls
    return decorator

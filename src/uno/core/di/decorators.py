"""
Decorators for Uno DI system.

Provides @framework_service and related decorators to mark classes for DI service discovery.
"""


def framework_service(service_type=None, scope=None):
    """
    Decorator to mark a class as a DI service.

    Args:
        service_type: Optional explicit service type (interface/base class)
        scope: Optional service scope (e.g., ServiceScope.SINGLETON)
    """

    def decorator(cls):
        cls.__framework_service__ = True
        if service_type:
            cls.__framework_service_type__ = service_type
        if scope:
            cls.__framework_service_scope__ = scope
        return cls

    return decorator

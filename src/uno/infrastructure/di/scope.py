"""
Async context manager for DI scopes in Uno.

This module provides the Scope class, which manages the lifecycle of scoped services
using Python contextvars for per-coroutine/task isolation.
"""

import asyncio
import contextvars
from typing import TYPE_CHECKING, Any, Optional, TypeVar

if TYPE_CHECKING:
    from .provider import ServiceProvider

T = TypeVar("T")

# Context variable to track the current active scope per coroutine/task
_current_scope = contextvars.ContextVar("uno_di_current_scope", default=None)

class Scope:
    """
    Async context manager representing a DI scope.
    Tracks scoped service instances and disposes them on exit.
    """
    def __init__(self, provider: 'ServiceProvider', scope_id: str | None = None):
        self._provider = provider
        self._scope_id = scope_id
        self._instances: dict[type, Any] = {}
        self._disposed = False
        self._token = None

    async def __aenter__(self):
        self._token = _current_scope.set(self)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        try:
            # Dispose all disposable services in reverse creation order
            for instance in reversed(list(self._instances.values())):
                dispose = getattr(instance, "dispose", None)
                if asyncio.iscoroutinefunction(dispose):
                    await dispose()
                elif callable(dispose):
                    dispose()
        finally:
            _current_scope.reset(self._token)
            self._disposed = True

    def get_service(self, service_type: type[T]) -> T:
        """
        Get a service from the scope (singleton, transient, or scoped).
        """
        return self._provider.get_service(service_type)

    def set_instance(self, service_type: type, instance: Any):
        self._instances[service_type] = instance

    def get_instance(self, service_type: type) -> Any:
        return self._instances.get(service_type)

    @property
    def id(self):
        return self._scope_id

    @staticmethod
    def get_current_scope() -> Optional['Scope']:
        return _current_scope.get()
